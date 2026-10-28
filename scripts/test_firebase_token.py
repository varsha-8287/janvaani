import getpass
import os
import sys

import requests

from app.api.auth import _verify_firebase_token


API_KEY = os.environ.get("FIREBASE_API_KEY")
if not API_KEY:
    sys.exit("FIREBASE_API_KEY environment variable is not set.")

email = input("Test user email: ").strip()
password = getpass.getpass("Test user password: ")

response = requests.post(
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword",
    params={"key": API_KEY},
    json={
        "email": email,
        "password": password,
        "returnSecureToken": True,
    },
    timeout=20,
)

if not response.ok:
    print("Firebase sign-in failed. HTTP status:", response.status_code)
    sys.exit(1)

token = response.json()["idToken"]

try:
    claims = _verify_firebase_token(token)
    print("Firebase ID token verification: PASSED")
    print("Verified UID:", claims.get("uid"))
    print("Verified project:", claims.get("aud"))
except Exception:
    print("Firebase ID token verification: FAILED")
    sys.exit(1)