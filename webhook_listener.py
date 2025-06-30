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

# Store active processes to avoid duplicates
active_processes = {}

def stream_output(process, room_name):
    """Stream the agent's output to the main terminal"""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[AGENT-{room_name}] {line.rstrip()}", flush=True)
        process.stdout.close()
    except Exception as e:
        logger.error(f"Error streaming output for {room_name}: {e}")

def launch_agent(room_name="start"):
    print(f"=== Launching Agent for room: {room_name} ===", flush=True)
    
    # Check if agent is already running for this room
    if room_name in active_processes:
        if active_processes[room_name].poll() is None:  # Process is still running
            print(f"Agent already running for room: {room_name}", flush=True)
            return
        else:
            # Process has ended, remove it from active processes
            del active_processes[room_name]
    
    try:
        # Launch the agent with proper arguments
        process = subprocess.Popen(
            ['python', 'restaurant_agent.py', 'start'],  # Fixed: removed --room flag
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=os.environ.copy()  # Inherit environment variables
        )
        
        # Store the process
        active_processes[room_name] = process
        
        # Start a thread to stream the output
        output_thread = threading.Thread(
            target=stream_output, 
            args=(process, room_name),
            daemon=True
        )
        output_thread.start()
        
        print(f"Agent launched successfully for room: {room_name}, PID: {process.pid}", flush=True)
        logger.info(f"Agent process started with PID: {process.pid}")
        
    except FileNotFoundError:
        logger.error("restaurant_agent.py not found. Make sure the file exists in the current directory.")
        print("ERROR: restaurant_agent.py not found!", flush=True)
    except Exception as e:
        logger.error(f"Failed to launch agent: {e}")
        print(f"ERROR launching agent: {e}", flush=True)

async def dispatch_agent_to_room(room_name, agent_name="restaurant_agent"):
    """Dispatch agent to a specific room using LiveKit API"""
    try:
        lkapi = api.LiveKitAPI()
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=agent_name, 
                room=room_name, 
                metadata='{"user_id": "12345"}'
            )
        )
        logger.info(f"Created dispatch: {dispatch}")
        
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
            loop.run_until_complete(coro)
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    return thread

@app.route('/webhook', methods=['POST'])
def webhook():
    print("=== Webhook Request Received ===", flush=True)
    
    try:
        # Log request details for debugging
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Data: {request.data}")
        
        # Parse JSON data
        data = request.json if request.json else {}
        logger.info(f"JSON: {data}")
        
        # Extract event and room information
        event = data.get('event')
        room = data.get('room', {})
        room_name = room.get('name', 'start').strip()
        
        print(f"Event: {event}, Room: {room_name}", flush=True)
        
        # Launch agent for testing (always launch for now)
        launch_agent(room_name)
        
        # Uncomment below for production use with specific event handling
        # if event == 'room_started' and room_name.startswith('call-'):
            
        #     logger.info(f"Room started event detected for: {room_name}")
        #     launch_agent(room_name)
            
        #     # Also dispatch via API if needed
        #     # run_async_in_thread(dispatch_agent_to_room(room_name))
        
        return jsonify({'status': 'ok', 'message': 'Agent launch initiated'})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    """Check status of active agents"""
    status_info = {}
    for room, process in active_processes.items():
        status_info[room] = {
            'pid': process.pid,
            'running': process.poll() is None
        }
    return jsonify({'active_agents': status_info})

@app.route('/test-launch', methods=['POST'])
def test_launch():
    """Test endpoint to manually launch an agent"""
    room_name = request.json.get('room_name', 'test-room') if request.json else 'test-room'
    launch_agent(room_name)
    return jsonify({'status': 'ok', 'message': f'Test launch initiated for room: {room_name}'})

if __name__ == '__main__':
    print("Starting webhook server...", flush=True)
    print("Available endpoints:", flush=True)
    print("  POST /webhook - Main webhook endpoint", flush=True)
    print("  GET /status - Check agent status", flush=True)
    print("  POST /test-launch - Test agent launch", flush=True)
    
    app.run(host='0.0.0.0', port=5005, debug=True)
