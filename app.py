import os
import time
import uuid
import sqlite3
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# ---------------------------------------------------------------
# Branding (yahan se naam / tagline badal sakte ho)
# ---------------------------------------------------------------
BOT_NAME = "Krish AI"
BOT_TAGLINE = "Padhai, coding ya ideas: jo bhi poochna ho, Hindi, Hinglish ya English mein poochho."

SUGGESTIONS = [
    ("📖  Photosynthesis simple mein samjhao",
     "Photosynthesis ko simple Hinglish mein samjhao, ek real-life Indian example ke saath."),
    ("🐍  Python mein list kya hoti hai?",
     "Python mein list kya hoti hai? Chhote examples ke saath samjhao."),
    ("🎬  Educational YouTube channel ke 5 video ideas",
     "Ek educational YouTube channel ke liye 5 video ideas do."),
    ("📝  BCA student ka resume kaise banayein?",
     "BCA student ke liye ek strong resume kaise banayein? Practical tips do."),
]

st.set_page_config(
    page_title=BOT_NAME,
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="auto",
)

# ---------------------------------------------------------------
# Design (CSS)
# Palette: Ink #101a3a | Chalk #f6f7fb | Mist #e9ecf5 | Marigold #f0a020
# Font: Mukta (Hindi/Devanagari + Latin dono ke liye bana hai)
# ---------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Mukta:wght@400;500;600;700&display=swap');

.stApp, .stApp .stMarkdown, .stApp button, .stApp textarea,
.stApp h1, .stApp h2, .stApp h3, .stApp p {
    font-family: 'Mukta', 'Noto Sans Devanagari', 'Segoe UI', sans-serif;
}

/* Streamlit ka default chrome hatao */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }

.block-container { max-width: 780px; padding-top: 2.2rem; padding-bottom: 7rem; }

/* ---------- Top bar (chat chalne ke baad) ---------- */
.topbar { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
          padding-bottom: 12px; margin-bottom: 8px; border-bottom: 1px solid #dde1ee; }
.topbar b { font-size: 1.25rem; font-weight: 700; color: #101a3a; }
.topbar span { font-size: .9rem; color: #5b6482; }

/* ---------- Welcome screen ---------- */
.greet { margin: 3.2rem 0 1.6rem; }
.greet h1 { font-size: 2.5rem; line-height: 1.15; font-weight: 700; color: #101a3a;
            margin: 0 0 .6rem; padding: 0; }
.greet p  { font-size: 1.05rem; color: #5b6482; margin: 0; max-width: 34em; }

/* Suggestion rows (sirf main area ke buttons) */
[data-testid="stMain"] .stButton > button, section.main .stButton > button {
    width: 100%; justify-content: flex-start; text-align: left;
    background: transparent; color: #1a2038;
    border: none; border-bottom: 1px solid #dde1ee; border-radius: 0;
    padding: .95rem .35rem; font-size: 1.02rem; font-weight: 500;
    transition: background .15s ease, border-color .15s ease;
}
[data-testid="stMain"] .stButton > button:hover, section.main .stButton > button:hover {
    background: #ffffff; color: #1a2038; border-bottom-color: #f0a020;
}
[data-testid="stMain"] .stButton > button:focus-visible, section.main .stButton > button:focus-visible {
    outline: 3px solid rgba(240,160,32,.55); outline-offset: 2px;
}

/* ---------- Chat messages ---------- */
[data-testid="stChatMessage"] { background: transparent; border: none; padding: .65rem 0; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #e9ecf5; border-radius: 16px; padding: .8rem 1rem;
}
[data-testid="stCaptionContainer"] { color: #6b7494; }

/* Chat input */
[data-testid="stChatInput"], [data-testid="stChatInput"] > div { border-radius: 16px; }

/* ---------- Sidebar (dark ink) ---------- */
[data-testid="stSidebar"] { background: #101a3a; }
[data-testid="stSidebar"] * { color: #eef1fb; }
.side-brand { font-size: 1.35rem; font-weight: 700; margin: .2rem 0 1rem; }
.side-label { font-size: .9rem; font-weight: 600; color: #9aa4c7 !important; margin: 1.2rem 0 .4rem; }
.side-note  { font-size: .85rem; color: #9aa4c7 !important; }

[data-testid="stSidebar"] .stButton > button {
    width: 100%; justify-content: flex-start; text-align: left;
    background: transparent; border: 1px solid transparent; border-radius: 10px;
    font-weight: 500; padding: .45rem .7rem;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,.08); border-color: rgba(255,255,255,.14);
}
[data-testid="stSidebar"] .stButton > button p {
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin: 0;
}
/* "Nayi chat" = ek hi marigold button */
[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: #f0a020; border: none; justify-content: center; font-weight: 700;
}
[data-testid="stSidebar"] button[kind="primary"] *,
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] * { color: #101a3a !important; }

/* ---------- Mobile ---------- */
@media (max-width: 640px) {
    .block-container { padding: 1.2rem 1rem 7rem; }
    .greet { margin-top: 1.5rem; }
    .greet h1 { font-size: 1.8rem; }
    .topbar span { display: none; }
}
</style>
""",
    unsafe_allow_html=True,
)

if not os.getenv("GEMINI_API_KEY"):
    st.error("API key nahi mili. `.env` file (ya Streamlit Secrets) check karo: GEMINI_API_KEY=...")
    st.stop()


@st.cache_resource
def get_client():
    return genai.Client(
        api_key=os.getenv("GEMINI_API_KEY"),
        http_options=types.HttpOptions(timeout=20000),
    )


@st.cache_resource
def get_db():
    conn = sqlite3.connect("chat.db", check_same_thread=False)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chats ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "chat_id TEXT, role TEXT, content TEXT, info TEXT)"
    )
    # Purani DB mein user_id column add karo (har visitor ki chat alag rakhne ke liye)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(chats)")]
    if "user_id" not in cols:
        conn.execute("ALTER TABLE chats ADD COLUMN user_id TEXT")
    conn.commit()
    return conn


client = get_client()
db = get_db()

MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]
SYSTEM = f"""Tumhara naam "{BOT_NAME}" hai. Tumhe Krish Lakhera ne banaya hai.
Agar koi poochhe "tumhe kisne banaya?" to jawab do: "Mujhe Krish ne banaya hai."
Agar koi seedha poochhe ki andar kaunsa AI model chal raha hai, to sach batao ki tum Google ke Gemini model par based ho.
Tum ek helpful assistant ho. User ki language (Hindi/Hinglish/English) mein jawab do."""


def new_id(n=10):
    return uuid.uuid4().hex[:n]


def load_messages(cid, uid):
    rows = db.execute(
        "SELECT role, content, info FROM chats WHERE chat_id=? AND user_id=? ORDER BY id",
        (cid, uid),
    ).fetchall()
    return [{"role": r, "content": c, "info": i} for r, c, i in rows]


def use_suggestion(text):
    st.session_state.pending_prompt = text


# ---- Visitor ID + Chat ID (dono address bar mein rehte hain) ----
if "uid" not in st.query_params:
    st.query_params["uid"] = new_id(16)
user_id = st.query_params["uid"]

if "cid" not in st.query_params:
    st.query_params["cid"] = new_id()
chat_id = st.query_params["cid"]

if "messages" not in st.session_state:
    st.session_state.messages = load_messages(chat_id, user_id)

# ---- Sidebar: Nayi chat + purani chats ki list ----
with st.sidebar:
    st.markdown(f'<div class="side-brand">🤖 {BOT_NAME}</div>', unsafe_allow_html=True)

    if st.button("➕ Nayi chat", type="primary", use_container_width=True):
        st.query_params["cid"] = new_id()
        st.session_state.messages = []
        st.rerun()

    st.markdown('<div class="side-label">Purani chats</div>', unsafe_allow_html=True)
    chat_list = db.execute(
        "SELECT c.chat_id, "
        "(SELECT content FROM chats WHERE chat_id=c.chat_id AND user_id=c.user_id "
        " AND role='user' ORDER BY id LIMIT 1) "
        "FROM chats c WHERE c.user_id=? "
        "GROUP BY c.chat_id ORDER BY MAX(c.id) DESC LIMIT 30",
        (user_id,),
    ).fetchall()

    if not chat_list:
        st.markdown('<div class="side-note">Abhi koi chat nahi hai.</div>', unsafe_allow_html=True)

    for cid, first in chat_list:
        title = (first or "Chat").replace("\n", " ")[:28]
        label = ("● " if cid == chat_id else "○ ") + title
        if st.button(label, key=f"chat_{cid}", use_container_width=True):
            st.query_params["cid"] = cid
            st.session_state.messages = load_messages(cid, user_id)
            st.rerun()

    if st.session_state.messages:
        st.markdown('<div class="side-label">Is chat ke liye</div>', unsafe_allow_html=True)
        if st.button("🗑️ Ye chat delete karo", key="delete_chat", use_container_width=True):
            db.execute("DELETE FROM chats WHERE chat_id=? AND user_id=?", (chat_id, user_id))
            db.commit()
            st.query_params["cid"] = new_id()
            st.session_state.messages = []
            st.rerun()

notes = ""
# ===== STEP 3 (PDF) wala code yahan paste hoga =====


def system_text():
    if notes:
        return SYSTEM + "\n\nSirf in notes ke basis par jawab do:\n" + notes
    return SYSTEM


def make_config(fast):
    if fast:
        return types.GenerateContentConfig(
            system_instruction=system_text(),
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        )
    return types.GenerateContentConfig(system_instruction=system_text())


def ask_gemini(contents):
    errors = []
    for model in MODELS:
        for fast in (True, False):
            start = time.time()
            try:
                response = client.models.generate_content(
                    model=model, contents=contents, config=make_config(fast)
                )
                secs = time.time() - start
                text = response.text or "(Khali jawab aaya, dobara try karo)"
                return text, f"⏱ {model} • {secs:.1f} sec"
            except Exception as e:
                errors.append(f"{model}: {str(e)[:150]}")
                if fast and getattr(e, "code", None) == 400:
                    continue
                break
    raise RuntimeError("\n\n".join(errors))


# ---- Input (suggestion button ya typed message) ----
typed = st.chat_input("Kuch poochho...")
prompt = typed or st.session_state.pop("pending_prompt", None)

# ---- Header ----
if not st.session_state.messages and not prompt:
    st.markdown(
        f'<div class="greet"><h1>Namaste! Aaj kya seekhna hai?</h1><p>{BOT_TAGLINE}</p></div>',
        unsafe_allow_html=True,
    )
    for i, (label, text) in enumerate(SUGGESTIONS):
        st.button(label, key=f"sug_{i}", on_click=use_suggestion, args=(text,), use_container_width=True)
else:
    st.markdown(
        f'<div class="topbar"><b>{BOT_NAME}</b><span>{BOT_TAGLINE}</span></div>',
        unsafe_allow_html=True,
    )

# ---- Purani messages dikhao ----
for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar="🧑" if m["role"] == "user" else "🤖"):
        st.markdown(m["content"])
        if m.get("info"):
            st.caption(m["info"])

# ---- Naya message ----
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in st.session_state.messages
    ]

    saved = False
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Soch raha hu..."):
            try:
                reply, info = ask_gemini(contents)
                st.markdown(reply)
                st.caption(info)
                st.session_state.messages.append(
                    {"role": "assistant", "content": reply, "info": info}
                )
                db.execute(
                    "INSERT INTO chats (chat_id, role, content, info, user_id) VALUES (?,?,?,?,?)",
                    (chat_id, "user", prompt, None, user_id),
                )
                db.execute(
                    "INSERT INTO chats (chat_id, role, content, info, user_id) VALUES (?,?,?,?,?)",
                    (chat_id, "assistant", reply, info, user_id),
                )
                db.commit()
                saved = True
            except Exception as e:
                st.error(f"Jawab nahi aa paya:\n\n{e}")
                st.session_state.messages.pop()

    if saved:
        st.rerun()  # sidebar ki list turant update ho jaye
