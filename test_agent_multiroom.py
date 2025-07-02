import requests
import subprocess
import threading
import time
import sys
import os
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

WEBHOOK_URL = "http://192.168.0.114:5005/webhook"
LIVEKIT_LOGS_CMD = "docker logs livekit-livekit-server-1"

# Fetch API key and secret from environment variables
API_KEY = os.environ.get("LIVEKIT_API_KEY")
API_SECRET = os.environ.get("LIVEKIT_API_SECRET")
if not API_KEY or not API_SECRET:
    print("Error: LIVEKIT_API_KEY and LIVEKIT_API_SECRET environment variables must be set.")
    sys.exit(1)

# LK_JOIN_CMD now uses the actual room name
LK_JOIN_CMD = (
    f'lk.exe join-room --url ws://192.168.0.114:7880 '
    f'--api-key {API_KEY} '
    f'--api-secret {API_SECRET} '
    '--room {room} --identity alice'
)

def send_webhook(room_name):
    data = {
        "event": "room_started",
        "room": {"name": room_name}
    }
    requests.post(WEBHOOK_URL, json=data)

def join_room(room_name):
    cmd = LK_JOIN_CMD.format(room=room_name)
    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def check_agent_in_logs(room_names):
    try:
        time.sleep(5)
        logs = subprocess.check_output(LIVEKIT_LOGS_CMD, shell=True, text=True)
        found = {room: False for room in room_names}
        for line in logs.splitlines():
            for room in room_names:
                # Look for the actual room name and agent participant in the same line
                if (
                    f'"room": "{room}"' in line and
                    'agent-' in line
                ):
                    found[room] = True
        return all(found.values())
    except KeyboardInterrupt:
        print("\nTest interrupted by user. Exiting gracefully.")
        sys.exit(0)
    return False

def main():
    print("=== Test script started ===")
    room1 = "call-room10000"
    room2 = "call-room20000"

    # 1. Send webhooks for both rooms
    t1 = threading.Thread(target=send_webhook, args=(room1,))
    t2 = threading.Thread(target=send_webhook, args=(room2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # 2. Simulate user joining both rooms
    u1 = threading.Thread(target=join_room, args=(room1,))
    u2 = threading.Thread(target=join_room, args=(room2,))
    u1.start()
    u2.start()
    u1.join()
    u2.join()

    # 3. Check logs for agent in both rooms (with improved logic)
    try:
        if check_agent_in_logs([room1, room2]):
            print("success: Agent joined both rooms!")
        else:
            print("failure: Agent did not join both rooms.")
    except KeyboardInterrupt:
        print("\nTest interrupted by user. Exiting gracefully.")
        sys.exit(0)

    # Print the exact commands used to join the rooms
    print("Commands used to join rooms:")
    print(LK_JOIN_CMD.format(room=room1))
    print(LK_JOIN_CMD.format(room=room2))

if __name__ == "__main__":
    main()
