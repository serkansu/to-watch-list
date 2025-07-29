import firebase_admin
from firebase_admin import credentials, db

def get_database():
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase_to_watch.json")
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://serkans-to-watch-list-default-rtdb.europe-west1.firebasedatabase.app"
        })

    return db.reference()
