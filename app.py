import os
import time
import uuid
import sqlite3
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

st.set_page_config(page_title="Mera AI Chatbot", page_icon="🤖")
st.title("🤖 Mera AI Chatbot")

if not os.getenv("GEMINI_API_KEY"):
    st.error("API key nahi mili. `.env` file check karo: GEMINI_API_KEY=...")
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
    conn.commit()
    return conn


client = get_client()
db = get_db()

MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]
SYSTEM = "Tum ek helpful assistant ho. User ki language (Hindi/Hinglish/English) mein jawab do."


def load_messages(cid):
    rows = db.execute(
        "SELECT role, content, info FROM chats WHERE chat_id=? ORDER BY id",
        (cid,),
    ).fetchall()
    return [{"role": r, "content": c, "info": i} for r, c, i in rows]


# ---- Chat ID (address bar mein rehti hai) ----
if "cid" not in st.query_params:
    st.query_params["cid"] = uuid.uuid4().hex[:10]
chat_id = st.query_params["cid"]

if "messages" not in st.session_state:
    st.session_state.messages = load_messages(chat_id)

# ---- Sidebar: Nayi chat + purani chats ki list ----
with st.sidebar:
    if st.button("➕ Nayi chat", use_container_width=True):
        st.query_params["cid"] = uuid.uuid4().hex[:10]
        st.session_state.messages = []
        st.rerun()

    st.markdown("### 💬 Purani chats")
    chat_list = db.execute(
        "SELECT chat_id FROM chats GROUP BY chat_id ORDER BY MAX(id) DESC LIMIT 30"
    ).fetchall()

    if not chat_list:
        st.caption("Abhi koi chat nahi hai.")

    for (cid,) in chat_list:
        first = db.execute(
            "SELECT content FROM chats WHERE chat_id=? AND role='user' ORDER BY id LIMIT 1",
            (cid,),
        ).fetchone()
        title = (first[0] if first else "Chat").replace("\n", " ")[:28]
        label = ("🟢 " if cid == chat_id else "💬 ") + title
        if st.button(label, key=f"chat_{cid}", use_container_width=True):
            st.query_params["cid"] = cid
            st.session_state.messages = load_messages(cid)
            st.rerun()

notes = ""
# ===== STEP 3 (PDF) wala code yahan paste hoga =====


def system_text():
    if notes:
        return SYSTEM + "\n\nSirf in notes ke basis par jawab do:\n" + notes
    return SYSTEM


for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("info"):
            st.caption(m["info"])


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


if prompt := st.chat_input("Kuch poochho..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in st.session_state.messages
    ]

    saved = False
    with st.chat_message("assistant"):
        with st.spinner("Soch raha hu..."):
            try:
                reply, info = ask_gemini(contents)
                st.markdown(reply)
                st.caption(info)
                st.session_state.messages.append(
                    {"role": "assistant", "content": reply, "info": info}
                )
                db.execute(
                    "INSERT INTO chats (chat_id, role, content, info) VALUES (?,?,?,?)",
                    (chat_id, "user", prompt, None),
                )
                db.execute(
                    "INSERT INTO chats (chat_id, role, content, info) VALUES (?,?,?,?)",
                    (chat_id, "assistant", reply, info),
                )
                db.commit()
                saved = True
            except Exception as e:
                st.error(f"Jawab nahi aa paya:\n\n{e}")
                st.session_state.messages.pop()

    if saved:
        st.rerun()  # sidebar ki list turant update ho jaye