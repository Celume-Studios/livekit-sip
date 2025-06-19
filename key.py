import secrets

import base64

api_key = secrets.token_hex(16)

api_secret = base64.b64encode(secrets.token_bytes(32)).decode()

print("API Key:", api_key)

print("API Secret:", api_secret)