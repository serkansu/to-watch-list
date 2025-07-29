import streamlit as st
import json
import requests
import os
from dotenv import load_dotenv
from firebase_setup import get_database

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
ref = get_database()

st.set_page_config(page_title="Serkan's Watch App", layout="centered")

# --- Refresh butonu stili ---
st.markdown("""
    <style>
    .refresh-button {
        background-color: #f0f0f5;
        color: black;
        padding: 8px 16px;
        border-radius: 10px;
        border: 1px solid #ccc;
        font-weight: bold;
        cursor: pointer;
        transition: background-color 0.3s ease;
        margin-bottom: 10px;
    }
    .refresh-button:hover {
        background-color: #cce6ff;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎬 Serkan's Watch App")

# --- Refresh butonu ---
if st.button("🔄 Refresh page", key="refresh", help="Sayfayı yenile"):
    st.query_params.clear()
    st.rerun()

# --- Arama Tipi ve Girdi ---
search_type = st.radio("Search type:", ["Movie", "TV Show", "Actor/Actress"])
default_query = st.query_params.get("q", "")
query = st.text_input("🔍 Search for a title or actor:", value=default_query, key="search_box")

# --- API Fonksiyonları ---
def tmdb_search(query, search_type):
    type_map = {"Movie": "movie", "TV Show": "tv", "Actor/Actress": "person"}
    url = f"https://api.themoviedb.org/3/search/{type_map[search_type]}"
    params = {"api_key": TMDB_API_KEY, "query": query}
    response = requests.get(url, params=params)
    return response.json().get("results", [])

def fetch_omdb_rating(imdb_id):
    url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={imdb_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        imdb_rating = data.get("imdbRating", "N/A")
        rt_rating = next((r["Value"] for r in data.get("Ratings", []) if r["Source"] == "Rotten Tomatoes"), "N/A")
        return imdb_rating, rt_rating
    return "N/A", "N/A"

def fetch_actor_movies(person_id):
    url = f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={TMDB_API_KEY}"
    response = requests.get(url)
    return response.json().get("cast", [])

# --- Arama Sonuçları ---
if query:
    results = tmdb_search(query, search_type)
    if results:
        st.success(f"🔍 {len(results)} sonuç bulundu.")
        if search_type == "Actor/Actress":
            for actor in results:
                st.subheader(actor.get("name", "Unknown"))
                person_id = actor.get("id")
                movies = fetch_actor_movies(person_id)
                for r in movies:
                    tmdb_id = r.get("id")
                    title = r.get("title") or r.get("name")
                    year = (r.get("release_date") or "")[:4]
                    poster_path = r.get("poster_path")
                    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
                    external_ids_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/external_ids?api_key={TMDB_API_KEY}"
                    imdb_id_resp = requests.get(external_ids_url).json().get("imdb_id")
                    imdb_rating, rt_rating = fetch_omdb_rating(imdb_id_resp) if imdb_id_resp else ("N/A", "N/A")

                    cols = st.columns([1, 3])
                    with cols[0]:
                        if poster_url:
                            st.image(poster_url, width=100)
                    with cols[1]:
                        st.markdown(f"**{title}** ({year})")
                        st.markdown(f"🎯 IMDb: {imdb_rating} | 🍅 RT: {rt_rating}")
                        form_key = f"form_{imdb_id_resp or tmdb_id}_{title.replace(' ', '_')}"
                        with st.form(form_key):
                            priority = st.slider("🎯 İzleme Sırası (1-100)", 1, 100, 50)
                            submitted = st.form_submit_button("➕ Listeye Ekle")
                            if submitted:
                                ref.child(f"to_watch_firebase/movies/{imdb_id_resp}").set({
                                    "title": title,
                                    "year": year,
                                    "poster": poster_url,
                                    "imdbRating": imdb_rating,
                                    "rtRating": rt_rating,
                                    "priority": priority
                                })
                                st.success("✅ Başarıyla eklendi.")
                                st.query_params.clear()
                                st.rerun()
        else:
            for r in results:
                tmdb_id = r.get("id")
                title = r.get("title") or r.get("name")
                year = (r.get("release_date") or r.get("first_air_date") or "")[:4]
                poster_path = r.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
                media_type = "movie" if search_type == "Movie" else "tv"
                external_ids_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/external_ids?api_key={TMDB_API_KEY}"
                imdb_id_resp = requests.get(external_ids_url).json().get("imdb_id")
                imdb_rating, rt_rating = fetch_omdb_rating(imdb_id_resp) if imdb_id_resp else ("N/A", "N/A")

                cols = st.columns([1, 3])
                with cols[0]:
                    if poster_url:
                        st.image(poster_url, width=100)
                with cols[1]:
                    st.markdown(f"**{title}** ({year})")
                    st.markdown(f"🎯 IMDb: {imdb_rating} | 🍅 RT: {rt_rating}")
                    form_key = f"form_{imdb_id_resp or tmdb_id}_{title.replace(' ', '_')}"
                    with st.form(form_key):
                        priority = st.slider("🎯 İzleme Sırası (1-100)", 1, 100, 50)
                        submitted = st.form_submit_button("➕ Listeye Ekle")
                        if submitted:
                            category = "movies" if search_type == "Movie" else "shows"
                            ref.child(f"to_watch_firebase/{category}/{imdb_id_resp}").set({
                                "title": title,
                                "year": year,
                                "poster": poster_url,
                                "imdbRating": imdb_rating,
                                "rtRating": rt_rating,
                                "priority": priority
                            })
                            st.success("✅ Başarıyla eklendi.")
                            st.query_params.clear()
                            st.rerun()
    else:
        st.warning("❗ Hiç sonuç bulunamadı.")

# --- Watchlist ---
st.markdown("---")
category_selected = st.radio("📂 Watchlist kategorisi:", ["Movies", "TV Shows"])
db_key = "movies" if category_selected == "Movies" else "shows"
st.markdown(f"### 📺 Watchlist: {category_selected}")

movies_data = ref.child(f"to_watch_firebase/{db_key}").get()
if movies_data:
    sorted_movies = sorted(movies_data.items(), key=lambda x: x[1].get("priority", 50))
    for i, (imdb_id, movie) in enumerate(sorted_movies, start=1):
        cols = st.columns([1, 3])
        with cols[0]:
            if movie.get("poster"):
                st.image(movie["poster"], width=120)
        with cols[1]:
            st.markdown(f"**{i}) {movie['title']}** ({movie['year']})")
            st.markdown(f"🎯 IMDb: {movie['imdbRating']} | 🍅 RT: {movie['rtRating']}")
            new_priority = st.slider(f"🎛️ Öncelik:", 1, 100, movie["priority"], key=f"edit_{imdb_id}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📎 Güncelle", key=f"save_{imdb_id}"):
                    ref.child(f"to_watch_firebase/{db_key}/{imdb_id}/priority").set(new_priority)
                    st.success("✅ Güncellendi.")
                    st.rerun()
            with col2:
                if st.button("🗑️ Sil", key=f"delete_{imdb_id}"):
                    ref.child(f"to_watch_firebase/{db_key}/{imdb_id}").delete()
                    st.warning("❌ Silindi.")
                    st.rerun()
else:
    st.info("Henüz bu kategoriye öğe eklenmemiş.")
