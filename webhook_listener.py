# import subprocess
# import threading
# from flask import Flask, request, jsonify
# import asyncio
# import logging
# import sys
# from livekit import api
# logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)
# logger = logging.getLogger(__name__)

# app = Flask(__name__)
# def launch_agent():
#     print("=== Launching Agnent ===", flush=True)
#     # Launch the agent using the LiveKit CLI and log output
#     # Example: lk agent run --agent-name restaurant_agent --room <room_name>
#     process = subprocess.Popen(
#         ['python', 'restaurant_agent.py', '--room', 'start'],
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         text=True,
#         bufsize=1
#     )
#     # for line in process.stdout:
#     #     print(f"[LK_AGENT {room_name}] {line.rstrip()}", flush=True)
#     # process.stdout.close()
#     # process.wait()
# async def dispatch_agent_to_room(room_name, agent_name="restaurant_agent"):
#     lkapi = api.LiveKitAPI()
#     dispatch = await lkapi.agent_dispatch.create_dispatch(
#         api.CreateAgentDispatchRequest(
#             agent_name=agent_name, room=room_name, metadata='{"user_id": "12345"}'
#         )
#     )
#     logger.info(f"Created dispatch: {dispatch}")
#     dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
#     logger.info(f"There are {len(dispatches)} dispatches in {room_name}")
#     await lkapi.aclose()

# @app.route('/webhook', methods=['POST'])
# def webhook():
#     print("=== Request Recieved ===", flush=True)
#     launch_agent()
#     # print("=== Webhook received ===", flush=True)
#     # logger.info(f"Headers: {dict(request.headers)}")
#     # logger.info(f"Data: {request.data}")
#     # logger.info(f"JSON: {request.json}")
#     # sys.stdout.flush()
#     # data = request.json
#     # # Check for room creation event
#     # event = data.get('event')
#     # room = data.get('room', {})
#     # room_name = room.get('name', '').strip()  # Trim whitespace

#     # if event == 'room_started' and room_name.startswith('call-'):
       
        
#     #     logger.info(f"Triggered agent for room: {room_name}")
#     #     print(f"Triggered agent for room: {room_name}", flush=True)
#     #     logger.info(f"Dispatching agent to room: {room_name}")
#     #     print(f"Dispatching agent to room: {room_name}", flush=True)
#     #     asyncio.run(dispatch_agent_to_room(room_name))
#     return jsonify({'status': 'ok'})

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5005, debug=True)
import subprocess
import threading
from flask import Flask, request, jsonify
import asyncio
import logging
import sys
import os
from livekit import api

logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Single agent worker process
agent_worker_process = None
agent_worker_thread = None

# Track rooms that have already been dispatched
already_dispatched_rooms = set()

def stream_output(process, name):
    """Stream the agent worker's output to the main terminal"""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[{name}] {line.rstrip()}", flush=True)
        process.stdout.close()
    except Exception as e:
        logger.error(f"Error streaming output for {name}: {e}")

def start_agent_worker():
    """Start a single agent worker that can handle multiple rooms"""
    global agent_worker_process, agent_worker_thread
    
    if agent_worker_process and agent_worker_process.poll() is None:
        print("Agent worker already running", flush=True)
        return True
    
    try:
        print("=== Starting Agent Worker ===", flush=True)
        
        # Start the agent worker without specifying a room
        # It will wait for dispatch requests
        agent_worker_process = subprocess.Popen(
            ['python', 'restaurant_agent.py', 'start'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=os.environ.copy()
        )
        
        # Start a thread to stream the output
        # agent_worker_thread = threading.Thread(
        #     target=stream_output,
        #     args=(agent_worker_process, "WORKER"),
        #     daemon=True
        # )
        # agent_worker_thread.start()
        
        print(f"Agent worker started successfully, PID: {agent_worker_process.pid}", flush=True)
        logger.info(f"Agent worker process started with PID: {agent_worker_process.pid}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to start agent worker: {e}")
        print(f"ERROR starting agent worker: {e}", flush=True)
        return False

async def dispatch_agent_to_room(room_name, agent_name="restaurant_agent"):
    """Dispatch agent to a specific room using LiveKit API"""
    try:
        lkapi = api.LiveKitAPI()
        
        # Create dispatch request
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
                metadata='{"user_id": "webhook_dispatch"}'
            )
        )
        logger.info(f"Created dispatch for room {room_name}: {dispatch}")
        
        # List dispatches to confirm
        dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
        logger.info(f"There are {len(dispatches)} dispatches in {room_name}")
        
        await lkapi.aclose()
        return True
        
    except Exception as e:
        logger.error(f"Failed to dispatch agent to room {room_name}: {e}")
        return False

def run_async_in_thread(coro):
    """Run async function in a separate thread"""
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coro)
            return result
        except Exception as e:
            logger.error(f"Error in async thread: {e}")
            return False
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    return thread

def cleanup_worker():
    """Clean up the agent worker process"""
    global agent_worker_process
    if agent_worker_process and agent_worker_process.poll() is None:
        print("Terminating agent worker...", flush=True)
        agent_worker_process.terminate()
        try:
            agent_worker_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print("Force killing agent worker...", flush=True)
            agent_worker_process.kill()
        agent_worker_process = None

@app.route('/webhook', methods=['POST'])
def webhook():
    print("=== Webhook Request Received ===", flush=True)
    global already_dispatched_rooms
    try:
        # Log request details
        logger.info(f"Headers: {dict(request.headers)}")
        data = request.json if request.json else {}
        logger.info(f"JSON: {data}")
        
        # Extract event and room information
        event = data.get('event')
        room = data.get('room', {})
        room_name = room.get('name', '').strip()
        
        print(f"Event: {event}, Room: {room_name}", flush=True)
        
        if not room_name:
            return jsonify({'status': 'error', 'message': 'No room name provided'}), 400
        
        # Check if this room has already been dispatched
        if room_name in already_dispatched_rooms:
            logger.info(f"Room {room_name} has already been dispatched. Skipping.")
            return jsonify({
                'status': 'ok',
                'message': f'Agent already dispatched to room: {room_name}',
                'room': room_name
            })
        
        # Ensure agent worker is running
        if not start_agent_worker():
            return jsonify({'status': 'error', 'message': 'Failed to start agent worker'}), 500
        
        # Wait a moment for worker to initialize
        import time
        time.sleep(2)
        
        # Dispatch agent to the specific room
        logger.info(f"Dispatching agent to room: {room_name}")
        dispatch_thread = run_async_in_thread(dispatch_agent_to_room(room_name))
        
        # Mark this room as dispatched
        already_dispatched_rooms.add(room_name)
        
        return jsonify({
            'status': 'ok',
            'message': f'Agent dispatched to room: {room_name}',
            'room': room_name
        })
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    """Check status of agent worker"""
    global agent_worker_process
    worker_status = {
        'running': agent_worker_process and agent_worker_process.poll() is None,
        'pid': agent_worker_process.pid if agent_worker_process else None
    }
    return jsonify({'worker_status': worker_status})

@app.route('/start-worker', methods=['POST'])
def start_worker():
    """Manually start the agent worker"""
    success = start_agent_worker()
    return jsonify({
        'status': 'ok' if success else 'error',
        'message': 'Worker started' if success else 'Failed to start worker'
    })

@app.route('/stop-worker', methods=['POST'])
def stop_worker():
    """Manually stop the agent worker"""
    cleanup_worker()
    return jsonify({'status': 'ok', 'message': 'Worker stopped'})

# Cleanup on exit
import atexit
import signal

atexit.register(cleanup_worker)

def signal_handler(signum, frame):
    print(f"Received signal {signum}, cleaning up...", flush=True)
    cleanup_worker()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    print("Starting webhook server...", flush=True)
    print("Available endpoints:", flush=True)
    print("  POST /webhook - Main webhook endpoint", flush=True)
    print("  GET /status - Check worker status", flush=True)
    print("  POST /start-worker - Start agent worker", flush=True)
    print("  POST /stop-worker - Stop agent worker", flush=True)
    
    app.run(host='0.0.0.0', port=5005, debug=True)