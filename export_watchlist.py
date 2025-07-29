
import json
from firebase_setup import get_database

ref = get_database()
data = ref.child("to_watch").get()

# Veriyi 'movies' ve 'series' olarak ayırmayı desteklemek için kontrol ekle
movies = []
series = []

if data:
    for key, item in data.items():
        entry = {
            "imdb": item.get("imdb_id", ""),
            "title": item.get("title", ""),
            "poster": item.get("poster", ""),
            "description": item.get("description", "")
        }
        if item.get("type") == "series":
            series.append(entry)
        else:
            movies.append(entry)

# to_watch.json dosyasına yaz
with open("to_watch.json", "w", encoding="utf-8") as f:
    json.dump({
        "movies": movies,
        "series": series
    }, f, indent=2)

print("✅ to_watch.json başarıyla güncellendi.")
