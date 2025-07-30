
import streamlit as st
import json
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")

from firebase_setup import get_database

ref = get_database()

# --- Yardımcı Fonksiyonlar ---
def tmdb_search(query, search_type):
    type_map = {"Movie": "movie", "TV Show": "tv", "Actor/Actress": "person"}
    media_type = type_map.get(search_type, "movie")
    url = f"https://api.themoviedb.org/3/search/{media_type}"
    params = {"api_key": TMDB_API_KEY, "query": query}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        st.error("🔌 TMDB API'den veri alınamadı!")
        return []
    return response.json().get("results", [])

def fetch_omdb_rating(imdb_id):
    url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={imdb_id}"
    response = requests.get(url)
    try:
        data = response.json()
        imdb_rating = data.get("imdbRating", "N/A")
        rt_rating = next((r["Value"] for r in data.get("Ratings", []) if r["Source"] == "Rotten Tomatoes"), "N/A")
        return imdb_rating, rt_rating
    except:
        return "N/A", "N/A"

def fetch_actor_movies(person_id):
    url = f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={TMDB_API_KEY}"
    response = requests.get(url)
    return response.json().get("cast", [])

# --- UI Başlangıcı ---
st.set_page_config(page_title="Serkan's Watch App", layout="centered")
st.title("🎬 Serkan's Watch App")

col1, col2, col3 = st.columns([1, 2, 2])
with col1:
    if st.button("🔄", help="Refresh"):
        st.query_params.update({"q": ""})
        st.rerun()

with col2:
    if st.button("🆕 Last 4 Weeks – Movies"):
        st.session_state['recent_type'] = "movie"
        st.session_state['trigger'] = True

with col3:
    if st.button("📺 Last 4 Weeks – TV Shows"):
        st.session_state['recent_type'] = "tv"
        st.session_state['trigger'] = True

# --- Son 4 hafta içerikleri ---
if st.session_state.get("trigger", False):
    st.session_state['trigger'] = False
    content_type = st.session_state['recent_type']
    today = datetime.now().date()
    past_date = today - timedelta(days=28)
    endpoint = "movie" if content_type == "movie" else "tv"
    date_field = "primary_release_date" if content_type == "movie" else "first_air_date"
    url = f"https://api.themoviedb.org/3/discover/{endpoint}"
    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": f"{date_field}.desc",
        f"{date_field}.gte": past_date.isoformat(),
        f"{date_field}.lte": today.isoformat(),
        "language": "en-US"
    }
    resp = requests.get(url, params=params)
    items = resp.json().get("results", []) if resp.status_code == 200 else []
    for item in items[:10]:
        title = item.get("title") or item.get("name", "Unknown")
        year = (item.get("release_date") or item.get("first_air_date") or "")[:4]
        poster_path = item.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        tmdb_id = item.get("id")

        external_url = f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}/external_ids?api_key={TMDB_API_KEY}"
        imdb_id = requests.get(external_url).json().get("imdb_id")
        imdb_rating, rt_rating = fetch_omdb_rating(imdb_id) if imdb_id else ("N/A", "N/A")
        vote_avg = item.get("vote_average")
        vote_count = item.get("vote_count")
        fallback_rating = f"⭐ {vote_avg}/10 ({vote_count} oy)" if vote_avg and vote_count else "N/A"

        cols = st.columns([1, 3])
        with cols[0]:
            if poster_url:
                imdb_url = f"https://www.imdb.com/title/{imdb_id}" if imdb_id else ""
                st.markdown(
                    f'<a href="{imdb_url}" target="_blank">'
                    f'<img src="{poster_url}" width="100" style="border-radius:12px; cursor:pointer;"></a>'
                    if imdb_id else
                    f'<img src="{poster_url}" width="100" style="border-radius:12px;">',
                    unsafe_allow_html=True
                )
        with cols[1]:
            st.markdown(f"**{title}** ({year})")
            st.markdown(f"🎯 IMDb: {imdb_rating} | 🍅 RT: {rt_rating} | {fallback_rating}")

# --- Devamı: Arama ve Watchlist bölümleri ---
# Bu kısmı istersen dosyaya devamında ekleyebilirim. 200+ satıra ulaşması için Watchlist dahil edilmeli.



# --- Search and Watchlist Integration (Extended) ---

# --- Arama Kutusu ---
search_type = st.radio("Search type:", ["Movie", "TV Show", "Actor/Actress"], horizontal=True)
default_query = st.query_params.get("q", "")
query = st.text_input("🔍 Search for a title or actor:", value=default_query, key="search_box")

if query:
    results = tmdb_search(query, search_type)

    if results:
        if search_type == "Actor/Actress":
            results_expanded = []
            for actor in results:
                actor_id = actor.get("id")
                actor_movies = fetch_actor_movies(actor_id)
                results_expanded.extend(actor_movies)
            results = results_expanded

        for r in results:
            tmdb_id = r.get("id")
            type_map = {"Movie": "movie", "TV Show": "tv", "Actor/Actress": "person"}
            media_type = type_map.get(search_type, "movie")
            external_ids_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/external_ids?api_key={TMDB_API_KEY}"
            imdb_id_resp = requests.get(external_ids_url).json().get("imdb_id")
            r["imdb_id"] = imdb_id_resp

        st.success(f"🔍 {len(results)} sonuç bulundu.")
        for r in results:
            tmdb_id = r.get("id")
            title = r.get("title") or r.get("name", "N/A")
            year = (r.get("release_date") or r.get("first_air_date") or "")[:4]
            poster_path = r.get("poster_path")
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
            imdb_id_resp = r.get("imdb_id")
            imdb_rating, rt_rating = fetch_omdb_rating(imdb_id_resp) if imdb_id_resp else ("N/A", "N/A")

            cols = st.columns([1, 3])
            with cols[0]:
                if poster_url:
                    imdb_url = f"https://www.imdb.com/title/{imdb_id_resp}" if imdb_id_resp else ""
                    st.markdown(
                        f'<a href="{imdb_url}" target="_blank">'
                        f'<img src="{poster_url}" width="100" style="border-radius:12px; cursor:pointer;"></a>' 
                        if imdb_id_resp else 
                        f'<img src="{poster_url}" width="100" style="border-radius:12px;">',
                        unsafe_allow_html=True
                    )
            with cols[1]:
                st.markdown(f"**{title}** ({year})")
                st.markdown(f"🎯 IMDb: {imdb_rating} | 🍅 RT: {rt_rating}")
                with st.form(f"form_{imdb_id_resp or tmdb_id}_{title.replace(' ', '_')}"):
                    priority = st.slider("🎯 İzleme Sırası (1–100)", 1, 100, 50)
                    submitted = st.form_submit_button("➕ Listeye Ekle")
                    if submitted:
                        category = "movies" if search_type == "Movie" else "shows"
            st.query_params.update({"q": ""})
            ref.child(f"to_watch_firebase/{category}/{imdb_id_resp or tmdb_id}").set({
                            "title": title,
                            "year": year,
                            "poster": poster_url,
                            "imdbRating": imdb_rating,
                            "rtRating": rt_rating,
                            "priority": priority
                        })
                        st.success("✅ Başarıyla eklendi.")
                        st.query_params.update({"q": ""})
                        st.rerun()

# --- Watchlist ---
st.markdown("---")
category_selected = st.radio("📂 Watchlist kategorisi:", ["Movies", "TV Shows"], horizontal=True)
db_key = "movies" if category_selected == "Movies" else "shows"
st.markdown(f"### 📺 Watchlist: {category_selected}")

movies_data = ref.child(f"to_watch_firebase/{db_key}").get()
if movies_data:
    sorted_movies = sorted(movies_data.items(), key=lambda x: x[1].get("priority", 50))
    for i, (imdb_id, movie) in enumerate(sorted_movies, start=1):
        cols = st.columns([1, 3])
        with cols[0]:
            if movie.get("poster"):
                imdb_url = f"https://www.imdb.com/title/{imdb_id}" if imdb_id else ""
                st.markdown(
                    f'<a href="{imdb_url}" target="_blank">'
                    f'<img src="{movie["poster"]}" width="120" style="border-radius:12px; cursor:pointer;"></a>'
                    if imdb_id else 
                    f'<img src="{movie["poster"]}" width="120" style="border-radius:12px;">',
                    unsafe_allow_html=True
                )
        with cols[1]:
            st.markdown(f"**{i}) {movie['title']}** ({movie['year']})")
            st.markdown(f"🎯 IMDb: {movie['imdbRating']} | 🍅 RT: {movie['rtRating']}")
            new_priority = st.slider(f"🎛️ Öncelik:", 1, 100, movie["priority"], key=f"edit_{imdb_id}")
            col1, col2, col3 = st.columns(3)
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
            with col3:
                if st.button("📌 Başa Tuttur", key=f"pin_{imdb_id}"):
                    lowest_priority = min(x[1]["priority"] for x in sorted_movies)
                    new_top_priority = max(1, lowest_priority - 1)
                    ref.child(f"to_watch_firebase/{db_key}/{imdb_id}/priority").set(new_top_priority)
                    st.success("📌 Listenin en başına alındı.")
                    st.rerun()
else:
    st.info("Henüz bu kategoriye öğe eklenmemiş.")
