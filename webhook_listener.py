from flask import Flask, request, jsonify
import subprocess
import threading

app = Flask(__name__)

def launch_agent(room_name):
    # Launch restaurant_agent.py with the room name as an argument
    subprocess.Popen(['python', 'restaurant_agent.py', '--room', room_name])

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # Check for room creation event
    event = data.get('event')
    room = data.get('room', {})
    room_name = room.get('name', '')

    if event == 'room_started' and room_name.startswith('call-'):
        threading.Thread(target=launch_agent, args=(room_name,)).start()
        print(f"Triggered agent for room: {room_name}")
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)
