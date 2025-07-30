
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

# -------------------- YARDIMCI FONKSİYONLAR --------------------
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
    if response.status_code == 200:
        data = response.json()
        imdb_rating = data.get("imdbRating", "N/A")
        rt_rating = next((r["Value"] for r in data.get("Ratings", []) if r["Source"] == "Rotten Tomatoes"), "N/A")
        return imdb_rating, rt_rating
    return "N/A", "N/A"

def fetch_tmdb_external_id(tmdb_id, media_type):
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/external_ids?api_key={TMDB_API_KEY}"
    response = requests.get(url)
    return response.json().get("imdb_id", None)

def fetch_actor_movies(person_id):
    url = f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={TMDB_API_KEY}"
    response = requests.get(url)
    return response.json().get("cast", [])

def format_rating(imdb, rt, vote_avg, vote_count):
    if imdb != "N/A":
        return f"🎯 IMDb: {imdb} | 🍅 RT: {rt}"
    elif vote_avg:
        return f"⭐ {vote_avg}/10 ({vote_count} oy)"
    else:
        return "🎯 IMDb: N/A | 🍅 RT: N/A"

def list_and_add_recent(content_type, label, db_category, api_endpoint, date_field, key_prefix):
    today = datetime.now().date()
    past_date = today - timedelta(days=28)
    url = f"https://api.themoviedb.org/3/discover/{api_endpoint}"
    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": f"{date_field}.desc",
        f"{date_field}.gte": past_date.isoformat(),
        f"{date_field}.lte": today.isoformat(),
        "language": "en-US"
    }
    resp = requests.get(url, params=params)
    items = resp.json().get("results", []) if resp.status_code == 200 else []
    st.success(f"{label} Found {len(items)} new {content_type}s in the last 4 weeks.")
    for item in items[:10]:
        tmdb_id = item["id"]
        media_type = api_endpoint
        imdb_id = fetch_tmdb_external_id(tmdb_id, media_type)
        imdb_rating, rt_rating = fetch_omdb_rating(imdb_id) if imdb_id else ("N/A", "N/A")
        vote_avg = item.get("vote_average", None)
        vote_count = item.get("vote_count", None)
        rating_display = format_rating(imdb_rating, rt_rating, vote_avg, vote_count)

        title = item.get("title") or item.get("name", "Unknown")
        year = (item.get("release_date") or item.get("first_air_date") or "")[:4]
        poster_path = item.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""

        cols = st.columns([1, 3])
        with cols[0]:
            if poster_url:
                if imdb_id:
                    st.markdown(f'<a href="https://www.imdb.com/title/{imdb_id}" target="_blank"><img src="{poster_url}" width="100"></a>', unsafe_allow_html=True)
                else:
                    st.image(poster_url, width=100)
        with cols[1]:
            st.markdown(f"**{title}** ({year})")
            st.markdown(rating_display)
            with st.form(f"{key_prefix}_form_{tmdb_id}"):
                priority = st.slider("🎯 İzleme Sırası (1–100)", 1, 100, 50, key=f"{key_prefix}_priority_{tmdb_id}")
                submitted = st.form_submit_button("➕ Listeye Ekle")
                if submitted:
                    ref.child(f"to_watch_firebase/{db_category}/{tmdb_id}").set({
                        "title": title,
                        "year": year,
                        "poster": poster_url,
                        "imdbRating": imdb_rating,
                        "rtRating": rt_rating,
                        "priority": priority
                    })
                    st.success("✅ Başarıyla eklendi.")

# -------------------- UI BAŞLANGIÇ --------------------
st.set_page_config(page_title="Serkan's Watch App", layout="centered")
st.title("🎬 Serkan's Watch App")

col_refresh, col_movies, col_shows = st.columns([1, 2, 2])
with col_refresh:
    if st.button("🔄 Refresh page", key="refresh", help="Sayfayı yenile"):
        st.query_params.update({"q": ""})
        st.rerun()

with col_movies:
    if st.button("🆕 Last 4 Weeks – Movies"):
        list_and_add_recent("movie", "🎬", "movies", "movie", "primary_release_date", "recent_movie")

with col_shows:
    if st.button("📺 Last 4 Weeks – TV Shows"):
        list_and_add_recent("tv show", "📺", "shows", "tv", "first_air_date", "recent_show")

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
            imdb_id_resp = fetch_tmdb_external_id(tmdb_id, media_type)
            r["imdb_id"] = imdb_id_resp

        st.success(f"🔍 {len(results)} sonuç bulundu.")
        for r in results:
            tmdb_id = r.get("id")
            title = r.get("title") or r.get("name", "N/A")
            year = (r.get("release_date") or r.get("first_air_date") or "")[:4]
            poster_path = r.get("poster_path")
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
            imdb_id = r.get("imdb_id")
            imdb_rating, rt_rating = fetch_omdb_rating(imdb_id) if imdb_id else ("N/A", "N/A")
            vote_avg = r.get("vote_average", None)
            vote_count = r.get("vote_count", None)
            rating_display = format_rating(imdb_rating, rt_rating, vote_avg, vote_count)

            cols = st.columns([1, 3])
            with cols[0]:
                if poster_url:
                    if imdb_id:
                        st.markdown(f'<a href="https://www.imdb.com/title/{imdb_id}" target="_blank"><img src="{poster_url}" width="100"></a>', unsafe_allow_html=True)
                    else:
                        st.image(poster_url, width=100)
            with cols[1]:
                st.markdown(f"**{title}** ({year})")
                st.markdown(rating_display)
                with st.form(f"form_{imdb_id or tmdb_id}_{title.replace(' ', '_')}"):
                    priority = st.slider("🎯 İzleme Sırası (1–100)", 1, 100, 50)
                    submitted = st.form_submit_button("➕ Listeye Ekle")
                    if submitted:
                        category = "movies" if search_type == "Movie" else "shows"
                        ref.child(f"to_watch_firebase/{category}/{imdb_id or tmdb_id}").set({
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
