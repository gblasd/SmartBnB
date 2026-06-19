"""
PropSearch AI — Streamlit Frontend
Talks exclusively to the FastAPI backend via HTTP.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime

# ─── Config ────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Smartbnb Advisor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #F7F5F2; }

[data-testid="stSidebar"] { background: #1C1917 !important; }
[data-testid="stSidebar"] * { color: #E7E5E0 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stMultiSelect label {
    color: #A8A29E !important; font-size: 0.78rem;
    letter-spacing: 0.08em; text-transform: uppercase;
}

.propsearch-header {
    background: linear-gradient(135deg, #1C1917 60%, #292524 100%);
    border-radius: 16px; padding: 28px 36px; margin-bottom: 20px;
    display: flex; align-items: center; justify-content: space-between;
}
.propsearch-header h1 {
    font-family: 'DM Serif Display', serif; color: #FAFAF9;
    font-size: 2.1rem; margin: 0; letter-spacing: -0.5px;
}
.propsearch-header .subtitle { color: #A8A29E; font-size: 0.9rem; margin-top: 4px; }
.accent-dot { color: #F97316; }

.prop-card {
    background: #FFFFFF; border-radius: 14px; padding: 18px 20px;
    margin-bottom: 14px; border: 1px solid #E7E5E0;
    transition: box-shadow 0.2s; cursor: pointer;
}
.prop-card:hover { box-shadow: 0 6px 24px rgba(0,0,0,0.10); }
.prop-price { font-family: 'DM Serif Display', serif; font-size: 1.35rem; color: #1C1917; }
.prop-address { color: #78716C; font-size: 0.85rem; margin-top: 2px; }
.badges { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
.badge {
    background: #F7F5F2; border: 1px solid #E7E5E0; border-radius: 6px;
    padding: 3px 10px; font-size: 0.78rem; color: #57534E;
}
.badge-match { background: #FFF7ED; border-color: #FDBA74; color: #C2410C; }
.badge-type-apt { background: #EFF6FF; border-color: #93C5FD; color: #1D4ED8; }
.badge-type-house { background: #F0FDF4; border-color: #86EFAC; color: #15803D; }

.metric-tile {
    background: #FFFFFF; border-radius: 12px; padding: 16px 20px;
    border: 1px solid #E7E5E0; text-align: center;
}
.metric-val { font-family: 'DM Serif Display', serif; font-size: 1.7rem; color: #1C1917; }
.metric-lbl { font-size: 0.78rem; color: #A8A29E; text-transform: uppercase; letter-spacing: 0.07em; }

.chat-container {
    background: #FFFFFF; border-radius: 16px; border: 1px solid #E7E5E0;
    overflow: hidden; display: flex; flex-direction: column; height: 530px;
}
.chat-header {
    background: #1C1917; padding: 14px 20px;
    display: flex; align-items: center; gap: 10px;
}
.chat-dot { width: 8px; height: 8px; border-radius: 50%; background: #22C55E; display:inline-block; }
.chat-header-text { color: #FAFAF9; font-size: 0.9rem; font-weight: 600; }
.chat-messages {
    flex: 1; overflow-y: auto; padding: 16px;
    display: flex; flex-direction: column; gap: 10px;
}
.msg-user {
    align-self: flex-end; background: #F97316; color: white;
    border-radius: 14px 14px 2px 14px; padding: 10px 14px;
    max-width: 82%; font-size: 0.88rem;
}
.msg-agent {
    align-self: flex-start; background: #F7F5F2; color: #1C1917;
    border-radius: 14px 14px 14px 2px; padding: 10px 14px;
    max-width: 88%; font-size: 0.88rem; border: 1px solid #E7E5E0;
}
.msg-time { font-size: 0.7rem; color: #A8A29E; margin-top: 3px; }
.msg-time-light { font-size: 0.7rem; color: rgba(255,255,255,0.65); margin-top: 3px; text-align:right; }

.map-wrapper { border-radius: 14px; overflow: hidden; border: 1px solid #E7E5E0; }

.stTextInput > div > div > input {
    border-radius: 10px !important; border: 1px solid #E7E5E0 !important;
    background: #FFFFFF !important;
}
div[data-testid="stForm"] { border: none; padding: 0; }
.stButton > button {
    background: #F97316 !important; color: white !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }

.api-error {
    background: #FEF2F2; border: 1px solid #FECACA; border-radius: 10px;
    padding: 12px 16px; color: #DC2626; font-size: 0.85rem; margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)


# ─── API helpers ───────────────────────────────────────────────────────────────

def api_health() -> bool:
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.ok
    except Exception:
        return False


def api_search(query: str, filters: dict) -> list[dict]:
    payload = {
        "query": query,
        "k": 6,
        "property_type": filters.get("property_type") if filters.get("property_type", "All") != "All" else None,
        "price": filters.get("price"),
        "beds": filters.get("beds") if filters.get("beds", 1) > 1 else None,
    }
    r = requests.post(f"{API_BASE}/search", json=payload, timeout=10)
    r.raise_for_status()
    return r.json().get("properties", [])


def api_chat(message: str, session_id: str | None, filters: dict) -> dict:
    payload = {
        "message": message,
        "session_id": session_id,
        "property_type": filters.get("type") if filters.get("type", "All") != "All" else None,
        "max_price": filters.get("price"),
        "min_bedrooms": filters.get("beds") if filters.get("beds", 1) > 1 else None,
    }
    r = requests.post(f"{API_BASE}/chat", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def api_reset(session_id: str):
    requests.post(f"{API_BASE}/chat/reset", params={"session_id": session_id}, timeout=5)


def api_db_status() -> dict:
    r = requests.get(f"{API_BASE}/db/status", timeout=5)
    r.raise_for_status()
    return r.json()


def api_all_properties() -> list[dict]:
    r = requests.get(f"{API_BASE}/properties", timeout=5)
    r.raise_for_status()
    return r.json().get("properties", [])


# ─── Session state ─────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "properties" not in st.session_state:
    st.session_state.properties = []
if "api_ok" not in st.session_state:
    st.session_state.api_ok = False
if "quick_query" not in st.session_state:
    st.session_state.quick_query = ""
if "db_count" not in st.session_state:
    st.session_state.db_count = 0

# Check API + seed initial properties
if not st.session_state.api_ok:
    if api_health():
        st.session_state.api_ok = True
        try:
            st.session_state.properties = api_all_properties()[:6]
            st.session_state.db_count = api_db_status().get("document_count", 0)
        except Exception:
            pass


# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏠 SmartBnB Advisor")

    # API status
    if st.session_state.api_ok:
        st.markdown(f"🟢 **API online** · {st.session_state.db_count} docs in Chroma")
        if st.session_state.db_count == 0:
            st.session_state.db_count = api_db_status().get("document_count", 0)
            st.rerun()

    else:
        st.markdown("🔴 **API offline** — start the FastAPI server")
        if st.button("Retry connection"):
            st.session_state.api_ok = api_health()
            st.rerun()

    st.markdown("---")
    st.markdown("**FILTERS**")

    prop_type = st.selectbox("Property type", ["All", "Apartment", "House", "Private room in condo", "Private room"])
    price = st.slider("Max price (USD)", 1_000, 50_000, 1_00, step=1_00, format="$%d")
    beds = st.selectbox("Min bedrooms", [1, 2, 3, 4, 5])
    req_features = st.multiselect(
        "Must-have features",
        ["pool", "garden", "gym", "parking", "rooftop", "pet-friendly", "balcony", "Smoking allowed"],
    )

    sidebar_filters = {
        "type": prop_type,
        "price": price,
        "beds": beds,
    }

    if st.button("🔍 Search with filters", use_container_width=True):
        if st.session_state.api_ok:
            with st.spinner("Searching..."):
                try:
                    results = api_search("properties in Mexico City", sidebar_filters)
                    #if req_features:
                    # results = [p for p in results if any(f in p.get("properties", []) for f in req_features)]
                    st.session_state.properties = results
                    st.rerun()
                except Exception as e:
                    st.error(f"Search failed: {e}")

    st.markdown("---")
    st.markdown("**QUICK SEARCHES**")
    qs = [
        ("🏙️ Luxury Polanco", "luxury apartment in Polanco with pool and amenities"),
        ("🌳 Family house", "family house with garden 3 bedrooms"),
        ("☕ Roma / Condesa", "apartment in Roma or Condesa pet friendly"),
        ("💰 Budget under $200k", "affordable apartment budget under 200000"),
    ]
    for label, query in qs:
        if st.button(label, use_container_width=True):
            st.session_state.quick_query = query

    st.markdown("---")
    if st.button("🗑 Reset chat", use_container_width=True):
        if st.session_state.session_id:
            try:
                api_reset(st.session_state.session_id)
            except Exception:
                pass
        st.session_state.session_id = None
        st.session_state.chat_history = []
        st.rerun()

    st.caption("LangChain · Chroma · OpenAI · FastAPI · Streamlit")


# ─── Header ────────────────────────────────────────────────────────────────────
props = st.session_state.properties
api_status_html = "🟢 API online · Vector DB ready" if st.session_state.api_ok else "🔴 API offline"

st.markdown(f"""
<div class="propsearch-header">
  <div>
    <h1>Prop<span class="accent-dot">Search</span> AI</h1>
    <div class="subtitle">LangChain · Chroma Vector DB · OpenAI · Mexico City</div>
  </div>
  <div style="color:#A8A29E; font-size:0.8rem; text-align:right">
    {api_status_html}<br>🤖 PropBot agent ready
  </div>
</div>
""", unsafe_allow_html=True)

# ─── Metrics ───────────────────────────────────────────────────────────────────
# if props:
#     avg_price = int(sum(p["price"] for p in props) / len(props))
#     n_apt = sum(1 for p in props if p["type"] == "apartment")
#     n_house = sum(1 for p in props if p["type"] == "house")
#     avg_rel = int(sum(p.get("relevance", 0) for p in props) / len(props) * 100) if props else 0
# else:
#     avg_price = n_apt = n_house = avg_rel = 0

# m1, m2, m3, m4 = st.columns(4)
# tiles = [
#     (len(props), "Results"),
#     (f"${avg_price:,}" if avg_price else "—", "Avg Price"),
#     (n_apt, "Apartments"),
#     (n_house, "Houses"),
# ]
# for col, (val, lbl) in zip([m1, m2, m3, m4], tiles):
#     with col:
#         st.markdown(f'<div class="metric-tile"><div class="metric-val">{val}</div><div class="metric-lbl">{lbl}</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ─── Main layout ───────────────────────────────────────────────────────────────
left_col, right_col = st.columns([3, 2], gap="medium")

# ── LEFT: Map + Cards ──────────────────────────────────────────────────────────
with left_col:
    # Map
    # if props:
    #     clat = sum(p["latitude"] for p in props) / len(props)
    #     clon = sum(p["longitude"] for p in props) / len(props)
    # else:
    #     clat, clon = 19.4284, -99.1677  # CDMX default

    clat, clon = 19.4284, -99.1677  # CDMX default


    m = folium.Map(location=[clat, clon], zoom_start=12, tiles="CartoDB positron")

    for p in props:
        color = "#F97316" if p["type"] == "apartment" else "#1C1917"
        rel_str = f" · {p['relevance']:.0%} match" if p.get("relevance") else ""
        popup_html = (
            f"<div style='font-family:sans-serif;min-width:190px'>"
            # f"<b style='font-size:1rem'>${p['price']:,}</b>{rel_str}<br>"
            f"<b style='font-size:1rem'>${dict(p).get("metadata").get("price"):,}</b>{rel_str}<br>"
            # f"<span style='color:#78716C;font-size:0.8rem'>{p['address']}</span><br>"
            f"<span style='color:#78716C;font-size:0.8rem'>{dict(p).get("metadata").get("neighbourhood_cleansed")}</span><br>"
            # f"<span style='font-size:0.8rem'>🛏 {p['bedrooms']} · 🛁 {p['bathrooms']} · 📐 {p['area']}m²</span>"
            f"<span style='font-size:0.8rem'>🛏 {dict(p).get("metadata").get("beds")} · 🛁 {dict(p).get("metadata").get("bathrooms")}</span>"
            f"</div>"
        )
        # dict(p).get("metadata").get("latitude")
        folium.CircleMarker(
            # location=[p["lat"], p["lon"]],
            location=[dict(p).get("metadata").get("latitude"), dict(p).get("metadata").get("longitude")],
            radius=14,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=230),
            # tooltip=f"${p['price']:,} · {p['bedrooms']}bd {p['type']}",
            tooltip=f"${dict(p).get("metadata").get("price"):,} · {dict(p).get("metadata").get("beds")}bd {dict(p).get("metadata").get("property_type")}",
        ).add_to(m)

    st.markdown('<div class="map-wrapper">', unsafe_allow_html=True)
    st_folium(m, height=320, use_container_width=True, returned_objects=[])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Property cards
    if not props:
        st.info("Ask PropBot to search for properties, or use the sidebar filters.")
    else:
        st.markdown(f"**{len(props)} result{'s' if len(props) != 1 else ''}**") # room_type
        for p in props:
            rel_pct = int(p.get("relevance", 0) * 100)
            feat_html = "".join(f'<span class="badge">{f}</span>' for f in p.get("features", [])[:3])
            type_class = "badge-type-apt" if dict(p).get("metadata").get("room_type") == "apartment" else "badge-type-house"
            match_badge = f'<span class="badge badge-match">⚡ {rel_pct}% match</span>' if rel_pct else ""

            st.markdown(f"""
            <div class="prop-card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div>
                  <div class="prop-price">${dict(p).get("metadata").get("price"):,} <span style='font-size:0.75rem;color:#78716C;font-family:DM Sans'>USD</span></div>
                  <div class="prop-address">📍 {dict(p).get("metadata").get("neighbourhood_cleansed")}</div>
                </div>
                <span class="badge {type_class}">{dict(p).get("metadata").get("room_type")}</span>
              </div>
              <div style="margin-top:8px;font-size:0.82rem;color:#57534E">
                🛏 {dict(p).get("metadata").get("beds")} beds · 🛁 {dict(p).get("metadata").get("bathrooms")} baths
              </div>
              <div style="margin-top:6px;font-size:0.8rem;color:#78716C">{dict(p).get("page_content")[:100]}…</div>
              <div class="badges">{match_badge}{feat_html}</div>
            </div>
            """, unsafe_allow_html=True)


# ── RIGHT: Chat ─────────────────────────────────────────────────────────────────
with right_col:
    st.markdown("**AI Property Agent**")

    # Build chat HTML
    msgs_html = ""
    if not st.session_state.chat_history:
        msgs_html = (
            '<div class="msg-agent">👋 Hi! I\'m <b>PropBot</b>, your AI real estate agent.<br><br>'
            'Tell me what you\'re looking for — neighbourhood, budget, bedrooms, lifestyle — '
            'and I\'ll query our Chroma vector database to find your perfect match.'
            '<div class="msg-time">just now</div></div>'
        )
    else:
        for msg in st.session_state.chat_history[-14:]:
            ts = msg.get("time", "")
            content = msg["content"].replace("\n", "<br>")
            if msg["role"] == "user":
                msgs_html += f'<div class="msg-user">{content}<div class="msg-time-light">{ts}</div></div>'
            else:
                msgs_html += f'<div class="msg-agent">{content}<div class="msg-time">{ts}</div></div>'

    st.markdown(f"""
    <div class="chat-container">
      <div class="chat-header">
        <span class="chat-dot"></span>
        <span class="chat-header-text">PropBot · LangChain Agent · online</span>
      </div>
      <div class="chat-messages">{msgs_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # Handle quick_query prefill
    prefill = ""
    if st.session_state.quick_query:
        prefill = st.session_state.quick_query
        st.session_state.quick_query = ""

    # Input form
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Message",
            value=prefill,
            placeholder="e.g. 2-bed apartment in Roma Norte under $300k",
            label_visibility="collapsed",
        )
        send = st.form_submit_button("Send →", use_container_width=True)

    if send and user_input.strip():
        if not st.session_state.api_ok:
            st.error("API is offline. Please start the FastAPI server.")
        else:
            now = datetime.now().strftime("%H:%M")
            st.session_state.chat_history.append(
                {"role": "user", "content": user_input, "time": now}
            )
            with st.spinner("PropBot is thinking…"):
                try:
                    resp = api_chat(
                        message=user_input,
                        session_id=st.session_state.session_id,
                        filters=sidebar_filters,
                    )
                    st.session_state.session_id = resp["session_id"]
                    reply = resp["reply"]
                    new_props = resp.get("properties", [])
                    if new_props:
                        # Feature filter from sidebar
                        if req_features:
                            new_props = [p for p in new_props if any(f in p.get("features", []) for f in req_features)]
                        if new_props:
                            st.session_state.properties = new_props
                except requests.exceptions.ConnectionError:
                    reply = "⚠️ Cannot reach the API server. Make sure FastAPI is running on port 8000."
                except Exception as e:
                    reply = f"⚠️ Error: {e}"

            st.session_state.chat_history.append(
                {"role": "assistant", "content": reply, "time": datetime.now().strftime("%H:%M")}
            )
            st.rerun()

    # Suggestion chips
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.75rem;color:#A8A29E;margin-bottom:6px">SUGGESTIONS</div>', unsafe_allow_html=True)
    suggestions = [
        "3-bed house with garden under $500k",
        "Modern apartment with rooftop",
        "Best areas for expats in CDMX?",
        "Compare Polanco vs Condesa",
    ]
    cols = st.columns(2)
    for i, sug in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state.quick_query = sug
                st.rerun()