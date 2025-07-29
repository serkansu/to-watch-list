import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, db

def get_database():
    b64_key = os.getenv("FIREBASE_SERVICE_KEY_B64")

    if not b64_key:
        raise ValueError("❌ Ortam değişkeni 'FIREBASE_SERVICE_KEY_B64' tanımlı değil.")

    try:
        decoded_json = base64.b64decode(b64_key).decode("utf-8")
        service_account_info = json.loads(decoded_json)
    except Exception as e:
        raise ValueError(f"❌ Firebase kimlik bilgileri decode edilemedi: {e}")

    cred = credentials.Certificate(service_account_info)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://serkans-to-watch-list-default-rtdb.europe-west1.firebasedatabase.app"
        })

    return db.reference("/")
