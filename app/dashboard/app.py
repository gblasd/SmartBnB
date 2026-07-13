"""SmartBnB — Premium Streamlit Dashboard.

Connects to the FastAPI backend (app.main) to power:
- Onboarding banner with suggest-chip quick queries
- Dynamic search bar with spinner skeleton
- Property result cards (3-column grid)
- Floating card detail dialog on card click
- Floating chat panel (streamlit-float) for conversational search
"""
from __future__ import annotations

import uuid
from typing import Any

import requests
import streamlit as st
from streamlit_float import float_init, float_css_helper

# ─────────────────────────────────────────────
# Page config – must be the very first st call
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SmartBnB · Intelligent Property Search",
    page_icon=":material/home:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

float_init(theme=True, include_unstable_primary=False)

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
try:
    from app.config import settings
    BASE_URL = settings.BACKEND_URL
except Exception:
    BASE_URL = "http://localhost:8000"

REQUEST_TIMEOUT = 30

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .hero-banner {
        background: linear-gradient(135deg, #0ea5e9 0%, #7c3aed 60%, #db2777 100%);
        border-radius: 16px;
        padding: 40px 48px;
        margin-bottom: 8px;
        position: relative;
        overflow: hidden;
    }
    .hero-banner::before {
        content: "";
        position: absolute;
        inset: 0;
        background: rgba(0,0,0,.35);
        border-radius: 16px;
    }
    .hero-content { position: relative; z-index: 1; }
    .hero-title { font-size: 2.6rem; font-weight: 700; color: #fff; margin: 0 0 6px 0; line-height: 1.15; }
    .hero-sub { font-size: 1.1rem; color: rgba(255,255,255,.82); margin: 0 0 24px 0; }
    .hero-kpi-row { display: flex; gap: 32px; margin-top: 8px; }
    .hero-kpi { text-align: center; }
    .hero-kpi-val { font-size: 1.7rem; font-weight: 700; color: #fff; }
    .hero-kpi-lbl { font-size: .75rem; color: rgba(255,255,255,.7); text-transform: uppercase; letter-spacing: .05em; }

    .prop-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        cursor: pointer;
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        height: 100%;
    }
    .prop-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(0,0,0,.45);
        border-color: #60A5FA;
    }
    .prop-title { font-size: 1rem; font-weight: 600; color: #F1F5F9; margin: 0 0 6px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .prop-hood { font-size: .8rem; color: #94A3B8; margin: 0 0 14px 0; }
    .prop-meta { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
    .prop-chip { background: #0F172A; border: 1px solid #334155; border-radius: 20px; padding: 2px 10px; font-size: .72rem; color: #94A3B8; }
    .prop-price { font-size: 1.2rem; font-weight: 700; color: #60A5FA; margin: 0 0 4px 0; }
    .prop-snippet { font-size: .78rem; color: #94A3B8; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }

    .chat-bubble-user {
        background: #1d4ed8; color: #fff;
        border-radius: 12px 12px 0 12px;
        padding: 8px 12px; margin: 6px 0 6px 30%;
        font-size: .83rem; line-height: 1.4;
    }
    .chat-bubble-ai {
        background: #1E293B; color: #F1F5F9;
        border-radius: 12px 12px 12px 0;
        padding: 8px 12px; margin: 6px 30% 6px 0;
        font-size: .83rem; line-height: 1.4;
    }

    .stSpinner > div { border-top-color: #60A5FA !important; }
    .stTextInput > div > div > input { border-radius: 50px !important; padding-left: 20px !important; font-size: 1rem !important; }

    .section-title { font-size: 1.3rem; font-weight: 700; color: #F1F5F9; margin: 0 0 4px 0; }
    .section-sub { font-size: .85rem; color: #94A3B8; margin: 0 0 20px 0; }

    .empty-state { text-align: center; padding: 60px 24px; color: #64748B; }
    .empty-icon { font-size: 3rem; margin-bottom: 12px; }
    .empty-msg { font-size: 1rem; font-weight: 500; }

    .detail-label { font-size: .7rem; color: #94A3B8; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 2px; }
    .detail-val { font-size: .95rem; color: #F1F5F9; font-weight: 500; margin-bottom: 12px; }

    .strategy-badge {
        display: inline-block;
        background: rgba(96,165,250,.15);
        border: 1px solid rgba(96,165,250,.3);
        color: #60A5FA;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: .72rem;
        font-weight: 600;
        letter-spacing: .04em;
        margin-left: 8px;
    }

    #MainMenu, footer { visibility: hidden; }
    header { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# Session-state initialisation
# ─────────────────────────────────────────────
def _init_state() -> None:
    defaults: dict[str, Any] = {
        "search_results": [],
        "search_query": "",
        "search_answer": "",
        "search_strategy": "",
        "searched": False,
        "selected_property": None,
        "show_detail": False,
        "chat_messages": [],
        "chat_session_id": str(uuid.uuid4()),
        "show_chat": False,
        "_pending_query": "",  # staging key for suggestion chips
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

_init_state()

# ─────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def check_health() -> dict:
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        return r.json()
    except Exception:
        return {"status": "unreachable", "vector_store": "unavailable"}


def search_properties(query: str, top_k: int = 9, strategy: str = "hybrid") -> dict:
    payload = {"query": query, "top_k": top_k}
    r = requests.post(
        f"{BASE_URL}/search",
        json=payload,
        params={"strategy": strategy},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def chat_with_agent(message: str, session_id: str) -> dict:
    payload = {"message": message, "session_id": session_id}
    r = requests.post(f"{BASE_URL}/chat", json=payload, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


# ─────────────────────────────────────────────
# Dialog: property detail
# ─────────────────────────────────────────────
@st.dialog("Property details", width="large")
def show_property_detail(prop: dict) -> None:
    name = prop.get("name") or prop.get("listing_id", "Property")
    st.markdown(f"### {name}")

    neighbourhood = prop.get("neighbourhood_cleansed") or prop.get("neighbourhood", "—")
    room_type = prop.get("room_type", "—")
    price = prop.get("price", prop.get("predicted_price", "—"))
    beds = prop.get("beds", "—")
    bedrooms = prop.get("bedrooms", "—")
    bathrooms = prop.get("bathrooms", "—")
    accommodates = prop.get("accommodates", "—")
    score = prop.get("review_scores_rating", "—")
    listing_id = prop.get("listing_id", prop.get("id", "—"))
    content = prop.get("content", "")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<p class="detail-label">Neighbourhood</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="detail-val">{neighbourhood}</p>', unsafe_allow_html=True)
        st.markdown('<p class="detail-label">Room type</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="detail-val">{room_type}</p>', unsafe_allow_html=True)
    with c2:
        st.markdown('<p class="detail-label">Price / night</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="detail-val">${price}</p>', unsafe_allow_html=True)
        st.markdown('<p class="detail-label">Rating</p>', unsafe_allow_html=True)
        score_str = f"&#9733; {score}" if score != "—" else "—"
        st.markdown(f'<p class="detail-val">{score_str}</p>', unsafe_allow_html=True)
    with c3:
        st.markdown('<p class="detail-label">Beds / Bedrooms / Baths</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="detail-val">{beds} beds · {bedrooms} bdr · {bathrooms} bath</p>', unsafe_allow_html=True)
        st.markdown('<p class="detail-label">Accommodates</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="detail-val">{accommodates} guests</p>', unsafe_allow_html=True)

    if content:
        st.markdown("**Description**")
        st.markdown(f"> {content}")

    with st.container(horizontal=True):
        if listing_id and listing_id != "—":
            url = f"https://www.airbnb.com/rooms/{listing_id}"
            st.link_button(
                "View on Airbnb",
                url,
                icon=":material/open_in_new:",
                type="primary",
            )
        if st.button("Ask AI about this", icon=":material/chat:", key="ask_ai_detail"):
            q = f"Tell me more about property {name} in {neighbourhood}"
            st.session_state.chat_messages.append({"role": "user", "content": q})
            st.session_state.show_chat = True
            st.rerun()

    with st.expander("Raw metadata", icon=":material/data_object:"):
        remaining = {k: v for k, v in prop.items() if k != "content"}
        st.json(remaining)


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### :material/tune: Search filters")
    strategy = st.segmented_control(
        "Retrieval strategy",
        options=["hybrid", "vector", "bm25"],
        default="hybrid",
        key="strategy",
    )
    top_k = st.slider("Max results", min_value=3, max_value=20, value=9, step=3)

    st.markdown("---")
    st.markdown("### :material/monitor_heart: API status")
    health = check_health()
    vs_status = health.get("vector_store", "unavailable")
    api_status = health.get("status", "unreachable")

    if api_status == "ok":
        st.badge("API online", icon=":material/check_circle:", color="green")
    else:
        st.badge("API offline", icon=":material/error:", color="red")

    if vs_status == "connected":
        st.badge("Vector store connected", icon=":material/database:", color="blue")
    else:
        st.badge(f"Vector store: {vs_status}", icon=":material/warning:", color="orange")

    st.markdown("---")
    if st.button(
        "Toggle chat assistant",
        icon=":material/chat_bubble:",
        type="secondary",
        key="toggle_chat_sidebar",
    ):
        st.session_state.show_chat = not st.session_state.show_chat
        st.rerun()

    st.caption("SmartBnB v0.3 · Powered by LangGraph + ChromaDB")


# ─────────────────────────────────────────────
# Hero / onboarding banner
# ─────────────────────────────────────────────
if not st.session_state.searched:
    st.markdown(
        """
        <div class="hero-banner">
          <div class="hero-content">
            <p class="hero-title">🏡 SmartBnB</p>
            <p class="hero-sub">
              AI-powered property search for Mexico City — semantic, BM25 &amp; hybrid retrieval
            </p>
            <div class="hero-kpi-row">
              <div class="hero-kpi">
                <div class="hero-kpi-val">15k+</div>
                <div class="hero-kpi-lbl">Listings</div>
              </div>
              <div class="hero-kpi">
                <div class="hero-kpi-val">3</div>
                <div class="hero-kpi-lbl">Search modes</div>
              </div>
              <div class="hero-kpi">
                <div class="hero-kpi-val">AI</div>
                <div class="hero-kpi-lbl">Chat agent</div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# Search bar
# ─────────────────────────────────────────────
st.markdown(
    '<p class="section-title">:material/search: Find your perfect stay</p>',
    unsafe_allow_html=True,
)

search_col, btn_col = st.columns([6, 1], vertical_alignment="bottom")
with search_col:
    # Use _pending_query as the controlled value; never write to a widget key directly.
    query_input = st.text_input(
        "Search query",
        value=st.session_state._pending_query,
        placeholder="e.g. cozy apartment in Condesa with balcony, under $80/night",
        label_visibility="collapsed",
    )
with btn_col:
    search_btn = st.button(
        "Search",
        type="primary",
        icon=":material/search:",
        key="search_btn",
    )

# ─────────────────────────────────────────────
# Suggestion chips (onboarding)
# ─────────────────────────────────────────────
SUGGESTIONS = {
    ":material/apartment: Condesa under $60": "Apartment in Condesa neighbourhood under 60 dollars",
    ":material/bed: 2 bedrooms Roma Norte": "2 bedroom property in Roma Norte",
    ":material/star: Top-rated Polanco": "Best rated listings in Polanco",
    ":material/family_restroom: Family-friendly CDMX": "Family friendly house with 3 beds near park",
    ":material/wifi: Entire home with fast WiFi": "Entire home or apartment with fast wifi for remote work",
    ":material/savings: Budget stay under $40": "Budget friendly room under 40 dollars per night",
}

if not st.session_state.searched:
    st.caption("Try a suggestion:")
    selected_pill = st.pills(
        "Quick searches",
        list(SUGGESTIONS.keys()),
        label_visibility="collapsed",
        key="suggestion_pills",
    )
    if selected_pill:
        # Store in staging key and rerun so the text_input renders with the value.
        st.session_state._pending_query = SUGGESTIONS[selected_pill]
        st.rerun()

# ─────────────────────────────────────────────
# Execute search
# ─────────────────────────────────────────────
active_query = query_input.strip()

# Auto-trigger search when a suggestion pill populated the input on a fresh rerun.
if not search_btn and active_query and st.session_state._pending_query == active_query:
    search_btn = True

if search_btn and active_query:
    with st.spinner("Searching with AI… analysing properties"):
        with st.skeleton(height=40):
            try:
                strat = st.session_state.get("strategy", "hybrid")
                result = search_properties(active_query, top_k=top_k, strategy=strat)
                st.session_state.search_results = result.get("documents", [])
                st.session_state.search_answer = result.get("answer", "")
                st.session_state.search_query = result.get("rewritten", active_query)
                st.session_state.search_strategy = result.get("strategy", strat)
                st.session_state.searched = True
                st.session_state._pending_query = ""  # clear staging key
            except requests.exceptions.ConnectionError:
                st.error(
                    "Cannot connect to the API. Make sure `uvicorn app.main:app` is running.",
                    icon=":material/error:",
                )
            except Exception as exc:
                st.error(f"Search failed: {exc}", icon=":material/error:")

# ─────────────────────────────────────────────
# Results area
# ─────────────────────────────────────────────
if st.session_state.searched:
    results = st.session_state.search_results
    strategy_label = st.session_state.search_strategy
    rewritten_query = st.session_state.search_query
    answer = st.session_state.search_answer

    strat_badge = f'<span class="strategy-badge">{strategy_label.upper()}</span>'
    st.markdown(
        f'<p class="section-title">Results for &ldquo;{rewritten_query}&rdquo; {strat_badge}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="section-sub">{len(results)} properties found</p>',
        unsafe_allow_html=True,
    )

    if answer:
        with st.container(border=True):
            st.markdown(":material/auto_awesome: **AI summary**")
            st.markdown(answer)

    if not results:
        st.markdown(
            """
            <div class="empty-state">
              <div class="empty-icon">🔍</div>
              <div class="empty-msg">No properties matched your query. Try different keywords.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        cols_per_row = 3
        for row_start in range(0, len(results), cols_per_row):
            row_props = results[row_start: row_start + cols_per_row]
            cols = st.columns(cols_per_row, gap="medium")
            for col, prop in zip(cols, row_props):
                with col:
                    name = prop.get("name") or f"Listing {prop.get('listing_id', '')}"
                    hood = prop.get("neighbourhood_cleansed") or prop.get("neighbourhood", "Mexico City")
                    price = prop.get("price") or prop.get("predicted_price", "—")
                    room = prop.get("room_type", "")
                    beds = prop.get("beds", "—")
                    score = prop.get("review_scores_rating", "")
                    snippet = prop.get("content", "")[:180]

                    chips_html = ""
                    if room:
                        chips_html += f'<span class="prop-chip">{room}</span>'
                    if beds and beds != "—":
                        chips_html += f'<span class="prop-chip">{beds} beds</span>'
                    if score:
                        chips_html += f'<span class="prop-chip">&#9733; {score}</span>'

                    card_html = f"""
                    <div class="prop-card">
                        <p class="prop-title">{name}</p>
                        <p class="prop-hood">&#128205; {hood}</p>
                        <div class="prop-meta">{chips_html}</div>
                        <p class="prop-price">${price}<span style="font-size:.7rem;font-weight:400;color:#94A3B8;"> /night</span></p>
                        <p class="prop-snippet">{snippet}</p>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)

                    if st.button(
                        "View details",
                        key=f"card_btn_{row_start}_{prop.get('listing_id', id(prop))}",
                        icon=":material/open_in_new:",
                        type="secondary",
                    ):
                        st.session_state.selected_property = prop
                        st.session_state.show_detail = True
                        st.rerun()

    st.markdown("---")
    if st.button(
        "New search",
        icon=":material/refresh:",
        type="secondary",
        key="new_search_btn",
    ):
        st.session_state.searched = False
        st.session_state.search_results = []
        st.session_state.search_answer = ""
        st.session_state.search_query = ""
        st.rerun()

else:
    if not st.session_state.searched:
        st.markdown(
            """
            <div class="empty-state">
              <div class="empty-icon">🏙️</div>
              <div class="empty-msg">Discover amazing stays in Mexico City</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# Property detail dialog trigger
# ─────────────────────────────────────────────
if st.session_state.show_detail and st.session_state.selected_property:
    show_property_detail(st.session_state.selected_property)
    st.session_state.show_detail = False

# ─────────────────────────────────────────────
# Floating chat assistant (streamlit-float)
# ─────────────────────────────────────────────
if st.session_state.show_chat:
    float_css = float_css_helper(
        width="380px",
        height="560px",
        right="24px",
        bottom="24px",
        z_index="10000",
        background="rgba(15,23,42,0.97)",
        border="1px solid #334155",
        shadow="0 20px 60px rgba(0,0,0,0.6)",
        css="border-radius:16px; backdrop-filter:blur(12px); overflow:hidden;",
    )

    chat_container = st.container()
    chat_container.float(float_css)

    with chat_container:
        hdr_col, close_col = st.columns([4, 1], vertical_alignment="center")
        with hdr_col:
            st.markdown(":material/chat_bubble: **AI chat assistant**")
        with close_col:
            if st.button("✕", key="close_chat_btn", help="Close chat"):
                st.session_state.show_chat = False
                st.rerun()

        chat_history_html = ""
        for msg in st.session_state.chat_messages[-20:]:
            role_class = "chat-bubble-user" if msg["role"] == "user" else "chat-bubble-ai"
            content = msg["content"].replace("<", "&lt;").replace(">", "&gt;")
            chat_history_html += f'<div class="{role_class}">{content}</div>'

        if chat_history_html:
            st.markdown(
                f'<div style="overflow-y:auto;max-height:380px;padding-right:4px;">{chat_history_html}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Ask me anything about Mexico City properties…")

        chat_prompt = st.chat_input(
            "Ask about properties…",
            key="float_chat_input",
            submit_mode="disable",
        )

        if chat_prompt:
            st.session_state.chat_messages.append({"role": "user", "content": chat_prompt})
            with st.spinner("Thinking…"):
                try:
                    resp = chat_with_agent(chat_prompt, st.session_state.chat_session_id)
                    reply = resp.get("reply", "Sorry, I could not get a response.")
                    st.session_state.chat_session_id = resp.get(
                        "session_id", st.session_state.chat_session_id
                    )
                    props = resp.get("properties")
                    if props:
                        st.session_state.search_results = props
                        st.session_state.search_answer = reply
                        st.session_state.search_query = chat_prompt
                        st.session_state.search_strategy = "agent"
                        st.session_state.searched = True
                except requests.exceptions.ConnectionError:
                    reply = "Cannot connect to the API."
                except Exception as exc:
                    reply = f"Error: {exc}"

            st.session_state.chat_messages.append({"role": "assistant", "content": reply})
            st.rerun()

else:
    toggle_container = st.container()
    toggle_css = float_css_helper(
        width="56px",
        height="56px",
        right="24px",
        bottom="24px",
        z_index="9999",
        background="linear-gradient(135deg,#0ea5e9,#7c3aed)",
        border="none",
        shadow="0 8px 24px rgba(14,165,233,.45)",
        css="border-radius:50%; display:flex; align-items:center; justify-content:center;",
    )
    toggle_container.float(toggle_css)
    with toggle_container:
        if st.button("💬", key="open_chat_btn", help="Open AI chat assistant"):
            st.session_state.show_chat = True
            st.rerun()
