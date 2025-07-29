import os
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

load_dotenv()

def get_database():
    json_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not json_path or not os.path.exists(json_path):
        raise ValueError("❌ GOOGLE_APPLICATION_CREDENTIALS tanımlı değil veya dosya bulunamadı.")

    cred = credentials.Certificate(json_path)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://serkans-to-watch-list-default-rtdb.europe-west1.firebasedatabase.app"
        })

    return db.reference()
