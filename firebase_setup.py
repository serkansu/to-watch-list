import os
import json
import firebase_admin
from firebase_admin import credentials, db
import base64

def get_database():
    encoded_json = os.environ.get("FIREBASE_CREDENTIALS")

    if not encoded_json:
        raise ValueError("❌ FIREBASE_CREDENTIALS ortam değişkeni eksik.")

    try:
        decoded_json = base64.b64decode(encoded_json).decode("utf-8")
        cred_dict = json.loads(decoded_json)
    except Exception as e:
        raise ValueError(f"❌ Firebase kimlik bilgileri decode edilemedi: {e}")

    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://serkans-to-watch-list-default-rtdb.europe-west1.firebasedatabase.app"
        })

    return db.reference("/")
