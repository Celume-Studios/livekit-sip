# server.py
import os
from livekit import api
from flask import Flask
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

@app.route('/getToken')
def getToken():
  token = api.AccessToken(os.getenv('LIVEKIT_API_KEY'), os.getenv('LIVEKIT_API_SECRET')) \
    .with_identity("identity") \
    .with_name("call-my name") \
    .with_grants(api.VideoGrants(
        room_join=True,
        room="room-test-5",
    ))
  return token.to_jwt()

if __name__ == "__main__":
    app.run(debug=True)