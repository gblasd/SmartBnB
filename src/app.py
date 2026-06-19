import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import time
import random
from datetime import datetime
# from anthropic import Anthropic
from openai import OpenAI

from dotenv import load_dotenv
import os
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("No se encontró OPENAI_API_KEY. Añádelo a tu entorno o archivo .env.")
    st.stop()


# ─── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PropSearch AI",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display&display=swap');

  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

  /* Background */
  .stApp { background: #F7F5F2; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #1C1917 !important;
  }
  [data-testid="stSidebar"] * { color: #E7E5E0 !important; }
  [data-testid="stSidebar"] .stSelectbox label,
  [data-testid="stSidebar"] .stSlider label,
  [data-testid="stSidebar"] .stMultiSelect label { color: #A8A29E !important; font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; }

  /* Header */
  .propsearch-header {
    background: linear-gradient(135deg, #1C1917 60%, #292524 100%);
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .propsearch-header h1 {
    font-family: 'DM Serif Display', serif;
    color: #FAFAF9;
    font-size: 2.1rem;
    margin: 0;
    letter-spacing: -0.5px;
  }
  .propsearch-header .subtitle {
    color: #A8A29E;
    font-size: 0.9rem;
    margin-top: 4px;
  }
  .accent-dot { color: #F97316; }

  /* Property cards */
  .prop-card {
    background: #FFFFFF;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 14px;
    border: 1px solid #E7E5E0;
    transition: box-shadow 0.2s;
    cursor: pointer;
  }
  .prop-card:hover { box-shadow: 0 6px 24px rgba(0,0,0,0.10); }
  .prop-card .price {
    font-family: 'DM Serif Display', serif;
    font-size: 1.35rem;
    color: #1C1917;
  }
  .prop-card .address { color: #78716C; font-size: 0.85rem; margin-top: 2px; }
  .prop-card .badges { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
  .badge {
    background: #F7F5F2;
    border: 1px solid #E7E5E0;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.78rem;
    color: #57534E;
  }
  .badge-highlight { background: #FFF7ED; border-color: #FDBA74; color: #C2410C; }

  /* Metric tiles */
  .metric-tile {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 16px 20px;
    border: 1px solid #E7E5E0;
    text-align: center;
  }
  .metric-tile .val {
    font-family: 'DM Serif Display', serif;
    font-size: 1.7rem;
    color: #1C1917;
  }
  .metric-tile .lbl { font-size: 0.78rem; color: #A8A29E; text-transform: uppercase; letter-spacing: 0.07em; }

  /* Float chat */
  .chat-container {
    background: #FFFFFF;
    border-radius: 16px;
    border: 1px solid #E7E5E0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    height: 520px;
  }
  .chat-header {
    background: #1C1917;
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .chat-header .dot { width: 8px; height: 8px; border-radius: 50%; background: #22C55E; }
  .chat-header span { color: #FAFAF9; font-size: 0.9rem; font-weight: 600; }
  .chat-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
  .msg-user {
    align-self: flex-end;
    background: #F97316;
    color: white;
    border-radius: 14px 14px 2px 14px;
    padding: 10px 14px;
    max-width: 80%;
    font-size: 0.88rem;
  }
  .msg-agent {
    align-self: flex-start;
    background: #F7F5F2;
    color: #1C1917;
    border-radius: 14px 14px 14px 2px;
    padding: 10px 14px;
    max-width: 85%;
    font-size: 0.88rem;
    border: 1px solid #E7E5E0;
  }
  .msg-time { font-size: 0.7rem; color: #A8A29E; margin-top: 3px; }

  /* Map wrapper */
  .map-wrapper { border-radius: 14px; overflow: hidden; border: 1px solid #E7E5E0; }

  /* Streamlit tweaks */
  .stTextInput > div > div > input {
    border-radius: 10px !important;
    border: 1px solid #E7E5E0 !important;
    background: #FFFFFF !important;
  }
  div[data-testid="stForm"] { border: none; padding: 0; }
  .stButton > button {
    background: #F97316 !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: opacity 0.2s !important;
  }
  .stButton > button:hover { opacity: 0.88 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Mock vector database ──────────────────────────────────────────────────────
PROPERTIES = [
    {"id": 1, "type": "apartment", "price": 285000, "bedrooms": 2, "bathrooms": 1,
     "area": 78, "address": "Av. Reforma 220, Col. Juárez", "city": "CDMX",
     "lat": 19.4284, "lon": -99.1677, "features": ["gym", "rooftop", "parking"],
     "score": 0.94, "description": "Modern apartment with floor-to-ceiling windows and stunning city views. Recently renovated kitchen with quartz countertops."},
    {"id": 2, "type": "house", "price": 560000, "bedrooms": 4, "bathrooms": 3,
     "area": 220, "address": "Calle Amores 18, Del Valle", "city": "CDMX",
     "lat": 19.3824, "lon": -99.1711, "features": ["garden", "garage", "study"],
     "score": 0.89, "description": "Spacious colonial house with private garden. Double garage and a quiet street in one of CDMX's most sought-after neighbourhoods."},
    {"id": 3, "type": "apartment", "price": 195000, "bedrooms": 1, "bathrooms": 1,
     "area": 52, "address": "Sonora 45, Roma Norte", "city": "CDMX",
     "lat": 19.4171, "lon": -99.1611, "features": ["pet-friendly", "concierge"],
     "score": 0.86, "description": "Bright studio-style apartment in the heart of Roma Norte. Steps from top cafes and restaurants."},
    {"id": 4, "type": "house", "price": 840000, "bedrooms": 5, "bathrooms": 4,
     "area": 380, "address": "Sierra Mojada 125, Polanco", "city": "CDMX",
     "lat": 19.4330, "lon": -99.1950, "features": ["pool", "gym", "smart home"],
     "score": 0.82, "description": "Luxury villa in Polanco with smart-home automation, private pool and rooftop terrace."},
    {"id": 5, "type": "apartment", "price": 320000, "bedrooms": 3, "bathrooms": 2,
     "area": 105, "address": "Ámsterdam 85, Condesa", "city": "CDMX",
     "lat": 19.4103, "lon": -99.1769, "features": ["balcony", "parking", "storage"],
     "score": 0.91, "description": "Corner apartment on the iconic Ámsterdam boulevard. Large balcony perfect for morning coffee."},
    {"id": 6, "type": "apartment", "price": 145000, "bedrooms": 1, "bathrooms": 1,
     "area": 45, "address": "Durango 30, Roma Sur", "city": "CDMX",
     "lat": 19.4096, "lon": -99.1653, "features": ["pet-friendly", "rooftop"],
     "score": 0.79, "description": "Cosy starter apartment in Roma Sur. Building has a lovely shared rooftop garden."},
    {"id": 7, "type": "house", "price": 410000, "bedrooms": 3, "bathrooms": 2,
     "area": 160, "address": "Copilco 99, Coyoacán", "city": "CDMX",
     "lat": 19.3431, "lon": -99.1613, "features": ["garden", "study", "parking"],
     "score": 0.87, "description": "Charming house near UNAM. Walled garden with mature trees, large study and two covered parking spaces."},
    {"id": 8, "type": "apartment", "price": 480000, "bedrooms": 3, "bathrooms": 2,
     "area": 130, "address": "Masaryk 189, Polanco", "city": "CDMX",
     "lat": 19.4368, "lon": -99.1942, "features": ["concierge", "gym", "pool"],
     "score": 0.88, "description": "High-end apartment on Masaryk Ave. Full amenities including infinity pool and 24/7 concierge."},
]

# ─── Vector search mock ────────────────────────────────────────────────────────
def vector_search(query: str, filters: dict) -> list[dict]:
    """Simulate semantic vector search with cosine similarity ranking."""
    results = []
    query_lower = query.lower()

    for prop in PROPERTIES:
        score = prop["score"]
        # Keyword boosts
        if any(k in query_lower for k in ["cheap", "affordable", "budget"]):
            if prop["price"] < 250000:
                score += 0.08
        if any(k in query_lower for k in ["luxury", "premium", "penthouse"]):
            if prop["price"] > 450000:
                score += 0.07
        if "pool" in query_lower and "pool" in prop["features"]:
            score += 0.06
        if "garden" in query_lower and "garden" in prop["features"]:
            score += 0.06
        if prop["type"] in query_lower:
            score += 0.05
        for n in ["1", "2", "3", "4", "5"]:
            if f"{n} bed" in query_lower and prop["bedrooms"] == int(n):
                score += 0.07

        # Apply sidebar filters
        if filters.get("type") and filters["type"] != "All":
            if prop["type"] != filters["type"].lower():
                continue
        if filters.get("max_price") and prop["price"] > filters["max_price"]:
            continue
        if filters.get("min_beds") and prop["bedrooms"] < filters["min_beds"]:
            continue

        results.append({**prop, "relevance": min(score, 1.0)})

    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:6]

# ─── AI agent ─────────────────────────────────────────────────────────────────
# client = Anthropic()
client = OpenAI(api_key=OPENAI_API_KEY, )
model_openai = "gpt-3.5-turbo"

SYSTEM_PROMPT = """You are PropBot, an expert real estate agent AI for PropSearch — a property search platform in Mexico City. You help users find houses and apartments using a semantic vector database.

When users describe what they're looking for, extract structured criteria and perform a search. Always be warm, knowledgeable, and concise.

For each search, respond with:
1. A brief friendly acknowledgement
2. A JSON block with search parameters (inside ```json ... ```) like:
{
  "query": "the user's natural language query",
  "filters": {
    "type": "apartment|house|All",
    "max_price": number or null,
    "min_beds": number or null
  },
  "summary": "1-2 sentence description of what you searched for"
}
3. Then say "Searching the vector database..." and describe results as if you found them.

If the user asks follow-up questions about neighbourhoods, prices, amenities or comparisons, answer helpfully from your knowledge of CDMX real estate without requiring a new search.

Always respond in the same language the user uses (Spanish or English)."""

def chat_with_agent(messages: list[dict]) -> tuple[str, dict | None]:
    """Call Claude API and extract any search parameters."""
    response = client.messages.create(
        # model="claude-sonnet-4-6",
        model=model_openai,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    text = response.content[0].text

    # Try to extract JSON search params
    search_params = None
    if "```json" in text:
        try:
            start = text.index("```json") + 7
            end = text.index("```", start)
            search_params = json.loads(text[start:end].strip())
        except Exception:
            pass

    return text, search_params

# ─── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "properties" not in st.session_state:
    st.session_state.properties = PROPERTIES[:5]
if "selected_prop" not in st.session_state:
    st.session_state.selected_prop = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ─── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏠 PropSearch AI")
    st.markdown("---")
    st.markdown("**FILTERS**")

    prop_type = st.selectbox("Property type", ["All", "Apartment", "House"])
    max_price = st.slider("Max price (USD)", 100_000, 1_000_000, 600_000, step=10_000,
                          format="$%d")
    min_beds = st.selectbox("Min bedrooms", [1, 2, 3, 4, 5], index=0)
    features = st.multiselect("Must-have features",
                              ["pool", "garden", "gym", "parking", "rooftop", "pet-friendly"])

    st.markdown("---")
    st.markdown("**QUICK SEARCHES**")
    if st.button("🏙️ Luxury Polanco"):
        st.session_state.quick_query = "luxury apartment in Polanco with amenities"
    if st.button("🌳 Family house w/ garden"):
        st.session_state.quick_query = "family house with garden 3+ bedrooms"
    if st.button("☕ Roma / Condesa vibes"):
        st.session_state.quick_query = "apartment in Roma or Condesa pet friendly"
    if st.button("💰 Budget under $200k"):
        st.session_state.quick_query = "affordable apartment budget under 200000"

    st.markdown("---")
    st.caption("Powered by Claude AI + Vector DB")

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="propsearch-header">
  <div>
    <h1>Prop<span class="accent-dot">Search</span> AI</h1>
    <div class="subtitle">Semantic property search · Mexico City · 8 listings indexed</div>
  </div>
  <div style="color:#A8A29E; font-size:0.8rem; text-align:right;">
    🟢 Vector DB connected<br>🤖 Agent online
  </div>
</div>
""", unsafe_allow_html=True)

# ─── Metrics row ──────────────────────────────────────────────────────────────
avg_price = int(sum(p["price"] for p in st.session_state.properties) / len(st.session_state.properties))
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-tile"><div class="val">{len(st.session_state.properties)}</div><div class="lbl">Results</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-tile"><div class="val">${avg_price:,.0f}</div><div class="lbl">Avg Price</div></div>', unsafe_allow_html=True)
with m3:
    apartments = sum(1 for p in st.session_state.properties if p["type"] == "apartment")
    st.markdown(f'<div class="metric-tile"><div class="val">{apartments}</div><div class="lbl">Apartments</div></div>', unsafe_allow_html=True)
with m4:
    houses = sum(1 for p in st.session_state.properties if p["type"] == "house")
    st.markdown(f'<div class="metric-tile"><div class="val">{houses}</div><div class="lbl">Houses</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ─── Main layout: Map + List | Chat ───────────────────────────────────────────
left_col, right_col = st.columns([3, 2], gap="medium")

# ── LEFT: Map + property list ──────────────────────────────────────────────────
with left_col:
    # Map
    center_lat = sum(p["lat"] for p in st.session_state.properties) / len(st.session_state.properties)
    center_lon = sum(p["lon"] for p in st.session_state.properties) / len(st.session_state.properties)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=13,
                   tiles="CartoDB positron")

    for prop in st.session_state.properties:
        color = "#F97316" if prop["type"] == "apartment" else "#1C1917"
        popup_html = f"""
        <div style='font-family:sans-serif;min-width:180px'>
          <b style='font-size:1rem'>${prop['price']:,}</b><br>
          <span style='color:#78716C;font-size:0.8rem'>{prop['address']}</span><br>
          <span style='font-size:0.8rem'>🛏 {prop['bedrooms']} · 🛁 {prop['bathrooms']} · 📐 {prop['area']}m²</span>
        </div>"""

        folium.CircleMarker(
            location=[prop["lat"], prop["lon"]],
            radius=14,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"${prop['price']:,} · {prop['bedrooms']}bd {prop['type']}",
        ).add_to(m)

    st.markdown('<div class="map-wrapper">', unsafe_allow_html=True)
    st_folium(m, height=320, use_container_width=True, returned_objects=[])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # Property list
    st.markdown("**Search results**")
    for prop in st.session_state.properties:
        rel_pct = int(prop.get("relevance", prop["score"]) * 100)
        feature_badges = "".join([f'<span class="badge">{f}</span>' for f in prop["features"][:3]])
        highlight = f'<span class="badge badge-highlight">⚡ {rel_pct}% match</span>'

        st.markdown(f"""
        <div class="prop-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
              <div class="price">${prop['price']:,} <span style='font-size:0.75rem;color:#78716C;font-family:DM Sans'>USD</span></div>
              <div class="address">📍 {prop['address']}</div>
            </div>
            <div style="text-align:right;font-size:0.78rem;color:#A8A29E;text-transform:uppercase">{prop['type']}</div>
          </div>
          <div style="margin-top:8px;font-size:0.82rem;color:#57534E">🛏 {prop['bedrooms']} beds · 🛁 {prop['bathrooms']} baths · 📐 {prop['area']} m²</div>
          <div style="margin-top:6px;font-size:0.8rem;color:#78716C">{prop['description'][:90]}…</div>
          <div class="badges">{highlight}{feature_badges}</div>
        </div>
        """, unsafe_allow_html=True)

# ── RIGHT: Float chat ──────────────────────────────────────────────────────────
with right_col:
    st.markdown("**AI Property Agent**")

    # Chat messages display
    chat_html = '<div class="chat-container"><div class="chat-header"><div class="dot"></div><span>PropBot · online</span></div><div class="chat-messages" id="chatbox">'

    if not st.session_state.chat_history:
        chat_html += '<div class="msg-agent">👋 Hi! I\'m PropBot. Tell me what you\'re looking for — neighbourhood, budget, bedrooms, lifestyle — and I\'ll search our vector database to find your perfect match.<div class="msg-time">just now</div></div>'
    else:
        for msg in st.session_state.chat_history[-12:]:
            ts = msg.get("time", "")
            if msg["role"] == "user":
                chat_html += f'<div class="msg-user">{msg["content"]}<div class="msg-time" style="text-align:right;color:rgba(255,255,255,0.7)">{ts}</div></div>'
            else:
                # Strip JSON blocks for display
                display = msg["content"]
                if "```json" in display:
                    display = display[:display.index("```json")].strip()
                    if "Searching the vector database" in msg["content"]:
                        after = msg["content"][msg["content"].index("Searching"):]
                        end_tick = after.find("```", 3)
                        if end_tick == -1:
                            display += "\n" + after
                        else:
                            display += "\n" + after[end_tick+3:].strip()
                display = display.replace("\n", "<br>")
                chat_html += f'<div class="msg-agent">{display}<div class="msg-time">{ts}</div></div>'

    chat_html += '</div></div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    # Handle quick query from sidebar
    prefill = ""
    if hasattr(st.session_state, "quick_query") and st.session_state.quick_query:
        prefill = st.session_state.quick_query
        st.session_state.quick_query = ""

    # Chat input
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Message PropBot…",
            value=prefill,
            placeholder="e.g. 2-bed apartment in Roma Norte under $300k",
            label_visibility="collapsed",
        )
        col_send, col_clear = st.columns([4, 1])
        with col_send:
            send = st.form_submit_button("Send →", use_container_width=True)
        with col_clear:
            clear = st.form_submit_button("🗑", use_container_width=True)

    if clear:
        st.session_state.chat_history = []
        st.session_state.messages = []
        st.rerun()

    if send and user_input.strip():
        now = datetime.now().strftime("%H:%M")
        st.session_state.chat_history.append({"role": "user", "content": user_input, "time": now})
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.spinner("PropBot is thinking…"):
            reply, search_params = chat_with_agent(st.session_state.messages)

        # Run vector search if agent returned params
        if search_params:
            filters = search_params.get("filters", {})
            # Apply sidebar filters too
            sidebar_filters = {
                "type": prop_type,
                "max_price": max_price,
                "min_beds": min_beds,
            }
            merged = {**sidebar_filters, **{k: v for k, v in filters.items() if v is not None and v != "All"}}
            results = vector_search(search_params.get("query", user_input), merged)
            # Feature filter
            if features:
                results = [p for p in results if any(f in p["features"] for f in features)]
            if results:
                st.session_state.properties = results

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.session_state.chat_history.append({"role": "assistant", "content": reply, "time": datetime.now().strftime("%H:%M")})
        st.rerun()

    # Suggested prompts
    st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.75rem;color:#A8A29E;margin-bottom:6px">SUGGESTED</div>', unsafe_allow_html=True)
    suggestions = [
        "3-bed house with garden under $500k",
        "Modern apartment with rooftop",
        "Best neighbourhoods for families?",
        "Compare Polanco vs Condesa",
    ]
    cols = st.columns(2)
    for i, sug in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state.quick_query = sug
                st.rerun()