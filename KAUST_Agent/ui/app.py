# ui/app.py

import os
import uuid
import html
import time
import requests
import base64
import streamlit as st
from PIL import Image


# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
logo = Image.open("ui/tahakom-icon.png")  # or .png

st.set_page_config(
    page_title="HR Agent",
    page_icon=logo,
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# LOAD LOGO (INLINE SVG)
# -------------------------------------------------
def inline_svg(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

logo_b64 = inline_svg("ui/tahakom-logo.svg")

# -------------------------------------------------
# MULTI-CHAT STATE (NO CHAT ADDED UNTIL FIRST MSG)
# -------------------------------------------------
if "chats" not in st.session_state:
    st.session_state.chats = {}               # real chats
    st.session_state.current_chat_id = None   # current chat id (real or pending)
    st.session_state.pending_chat_id = None   # pending chat id (not listed yet)
    st.session_state.pending_chat = None      # ✅ persist pending chat object across reruns

# ✅ NEW: pending backend processing state
if "pending_user_text" not in st.session_state:
    st.session_state.pending_user_text = None

def current_chat():
    cid = st.session_state.current_chat_id

    if cid is None:
        return None

    # ✅ Pending chat: return persistent object (NOT ephemeral)
    if cid == st.session_state.get("pending_chat_id"):
        if st.session_state.pending_chat is None or st.session_state.pending_chat.get("session_id") != cid:
            st.session_state.pending_chat = {
                "title": "New Chat",
                "session_id": cid,
                "messages": [],
                "updated_at": time.time(),
                "auto_titled": False,
            }
        return st.session_state.pending_chat

    # Real chat
    return st.session_state.chats.get(cid)

def ensure_real_chat_exists():
    """
    If user is in a pending chat, promote it to a real chat entry
    (so it appears in the sidebar) right before first message is stored.
    """
    cid = st.session_state.current_chat_id

    if cid is None:
        cid = str(uuid.uuid4())
        st.session_state.current_chat_id = cid
        st.session_state.pending_chat_id = cid
        st.session_state.pending_chat = {
            "title": "New Chat",
            "session_id": cid,
            "messages": [],
            "updated_at": time.time(),
            "auto_titled": False,
        }

    if cid == st.session_state.get("pending_chat_id"):
        pending_obj = st.session_state.pending_chat or {
            "title": "New Chat",
            "session_id": cid,
            "messages": [],
            "updated_at": time.time(),
            "auto_titled": False,
        }

        # ✅ promote and keep pending messages (e.g., greeting)
        st.session_state.chats[cid] = {
            "title": pending_obj.get("title", "New Chat"),
            "session_id": cid,
            "messages": list(pending_obj.get("messages", [])),
            "updated_at": pending_obj.get("updated_at", time.time()),
            "auto_titled": pending_obj.get("auto_titled", False),
        }

        st.session_state.pending_chat_id = None
        st.session_state.pending_chat = None

def touch_and_title(chat_obj, user_text: str):
    """Update activity time (newest on top) + auto-title on first user message."""
    chat_obj["updated_at"] = time.time()

    if not chat_obj.get("auto_titled", False):
        topic = user_text.strip().split("\n")[0]
        topic = " ".join(topic.split())

        MAX_TITLE = 22  # ✅ shorter sidebar titles
        if len(topic) > MAX_TITLE:
            topic = topic[:MAX_TITLE].rstrip() + "…"

        chat_obj["title"] = topic if topic else "New Chat"
        chat_obj["auto_titled"] = True

# -------------------------------------------------
# CSS (STYLE STREAMLIT'S REAL HEADER TO AVOID FLICKER)
# -------------------------------------------------
HEADER_H = 92
st.markdown(
    f"""
<style>
/* ✅ DO NOT hide Streamlit's header anymore (we skin it instead) */
footer {{
    display: none;
}}

[data-testid="stAppViewContainer"] {{
    background: #f5f7fa;
}}

/* ✅ Ensure base app is below the header */
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    position: relative !important;
    z-index: 0 !important;
}}

/* ✅ Use Streamlit's header (stable top layer) => no flicker on reruns */
header[data-testid="stHeader"] {{
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: {HEADER_H}px !important;
    z-index: 2147483647 !important;
    isolation: isolate !important;

    background-image:
        linear-gradient(
            to right,
            rgba(255,255,255,0.92) 0%,
            rgba(255,255,255,0.70) 22%,
            rgba(255,255,255,0.25) 42%,
            rgba(255,255,255,0.00) 62%
        ),
        linear-gradient(135deg, #25C7BC 0%, #602650 45%, #25C7BC 100%);

    background-size: 100% 100%, 320% 320%;
    background-position: 0 0, 0% 50%;
    animation: gradientMove 8s ease-in-out infinite;

    box-shadow: 0 8px 22px rgba(0,0,0,0.12) !important;
}}

/* ✅ Hide Streamlit's built-in header controls visually */
header[data-testid="stHeader"] > div {{
    opacity: 0 !important;
    pointer-events: none !important;
}}

/* ✅ Inject your logo into the header using CSS (stable) */
header[data-testid="stHeader"]::before {{
    content: "" !important;
    position: absolute !important;
    left: 28px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;

    width: 120px !important;
    height: 120px !important;

    background-image: url("data:image/svg+xml;base64,{logo_b64}") !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
}}

/* Keep your animated gradient */
@keyframes gradientMove {{
    0%   {{ background-position: 0 0, 0% 50%; }}
    50%  {{ background-position: 0 0, 100% 50%; }}
    100% {{ background-position: 0 0, 0% 50%; }}
}}

/* Push content below the fixed header + control space above pinned input */
.block-container {{
    padding-top: {HEADER_H + 18}px;
    padding-bottom: 90px !important; /* ✅ TUNE THIS to reduce space above input */
}}

/* Sidebar spacing under header */
section[data-testid="stSidebar"] {{
    padding-top: 0px !important;
    background: #e9edf2 !important;
    z-index: 1 !important;
}}

section[data-testid="stSidebar"] > div {{
    margin-top: {HEADER_H - 30}px !important;
}}

section[data-testid="stSidebar"] > div:first-child {{
    padding-top: 30px !important;
}}

section[data-testid="stSidebar"] button[kind="header"] {{
    margin-bottom: 4px !important;
}}

/* Bottom/chat input styling */
div[data-testid="stBottomBlockContainer"],
div[data-testid="stBottomBlockContainer"] > div,
div[data-testid="stBottom"] {{
    background: #f5f7fa !important;
    box-shadow: none !important;
    border-top: none !important;
    height: auto !important;
    min-height: 60px !important;   /* ✅ keep this 60 */
    max-height: none !important;
    overflow: visible !important;
}}

div[data-testid="stChatInput"] {{
    padding-top: 0px !important;
    padding-bottom: 0px !important;
    background: #f5f7fa !important;
    height: auto !important;
    min-height: 60px !important;
    margin-top: 0px !important;
}}

div[data-testid="stChatInput"] > div {{
    background: #ffffff !important;
    border: 1px solid rgba(0,0,0,0.12) !important;
    border-radius: 28px !important;
    overflow: hidden !important;
    box-shadow: 0 8px 22px rgba(0,0,0,0.08),
            0 2px 6px rgba(96, 38, 80, 0.08) !important;
    width: 100% !important;
    max-width: 1300px !important;
    margin: 0 auto !important;
    height: 60px !important;
    min-height: 60px !important;
    display: flex !important;
    align-items: stretch !important;
}}

div[data-testid="stChatInput"] form {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    flex: 1 1 auto !important;
    width: 100% !important;
    display: flex !important;
    align-items: stretch !important;
}}

div[data-testid="stChatInput"] form > div,
div[data-testid="stChatInput"] form > div > div,
div[data-testid="stChatInput"] [data-baseweb="base-input"],
div[data-testid="stChatInput"] [data-baseweb="textarea"],
div[data-testid="stChatInput"] [data-baseweb="textarea"] > div,
div[data-testid="stChatInput"] [data-baseweb="textarea"] > div > div {{
    background: #ffffff !important;
    border: none !important;
    box-shadow: none !important;
    flex: 1 1 auto !important;
    width: 100% !important;
    height: 100% !important;
    min-height: 100% !important;
    align-items: stretch !important;
}}

div[data-testid="stChatInput"] textarea {{
    height: 100% !important;
    min-height: 100% !important;
    max-height: none !important;
    font-size: 20px !important;
    line-height: 1.4 !important;
    padding: 15px 24px !important;
    background: #ffffff !important;
    color: #111 !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    overflow-y: auto !important;
    resize: none !important;
}}

div[data-testid="stChatInput"] > div:focus-within {{
    border-color: rgba(96, 38, 80, 0.75) !important;
    box-shadow: 0 0 0 3px rgba(96, 38, 80, 0.15) !important;
    outline: none !important;
}}

/* Fix send button vertical alignment */
div[data-testid="stChatInput"] button {{
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 18px !important;
}}

/* Also fix the button's internal wrapper */
div[data-testid="stChatInput"] button > div {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}}

div[data-testid="stChatInput"] *:focus,
div[data-testid="stChatInput"] *:focus-visible {{
    outline: none !important;
    box-shadow: none !important;
}}

/* Greeting animation */
.greeting {{
    transition: opacity .6s ease, max-height .6s ease, margin-bottom .6s ease;
    overflow: hidden;
}}
.greet-visible {{opacity:1; max-height:200px; margin-bottom:0;}}
.greet-hidden  {{opacity:0; max-height:0; margin-bottom:0;}}

/* Buttons */
div[data-testid="stButton"] > button {{
    width: 100% !important;
    height: 44px !important;
    border-radius: 999px !important;
    border: none !important;
    box-shadow: none !important;
    background-color: #602650 !important;
    color: #ffffff !important;
    font-weight: 500 !important;
    white-space: nowrap;
    transition: all 0.2s ease !important;
}}
div[data-testid="stButton"] > button:hover {{
    background-color: #7a2f69 !important;
    transform: translateY(-1px);
}}
div[data-testid="stButton"] > button:focus,
div[data-testid="stButton"] > button:focus-visible {{
    outline: none !important;
    box-shadow: none !important;
}}

/* Chat bubbles */
.chat-wrap {{
    width: 100%;
    max-width: 1300px;
    margin: 0 auto;
}}
.chat-row {{
    width: 100%;
    display: flex;
    margin: 10px 0;
}}
.chat-row.user {{
    justify-content: flex-end;
}}
.chat-row.assistant {{
    justify-content: flex-start;
}}
.chat-bubble {{
    max-width: 85%;
    padding: 14px 20px;
    border-radius: 22px;
    font-size: 18px;
    line-height: 1.8;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    white-space: pre-wrap;
    word-wrap: break-word;
}}
.chat-bubble.assistant {{
    background: #ffffff;
    color: #111;
    border: 1px solid rgba(0,0,0,0.08);
    border-top-left-radius: 8px;
}}
.chat-bubble.user {{
    background: #602650;
    color: #ffffff;
    border: 1px solid rgba(0,0,0,0.05);
    border-top-right-radius: 8px;
}}

/* ✅ CHIPS pinned just above the chat input (no st.bottom needed) */
.chips-wrapper {{
    position: fixed;
    left: 0;
    right: 0;
    bottom: 78px;          /* ✅ TUNE THIS: distance above the input */
    z-index: 1000;
}}



</style>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.title("Chats")

backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
username = "Dina"

def new_chat():
    # Create a pending chat (NOT added to sidebar until first message)
    new_id = str(uuid.uuid4())
    st.session_state.pending_chat_id = new_id
    st.session_state.current_chat_id = new_id
    st.session_state.pending_chat = {
        "title": "New Chat",
        "session_id": new_id,
        "messages": [],
        "updated_at": time.time(),
        "auto_titled": False,
    }

if st.sidebar.button("＋ New chat", use_container_width=True):
    new_chat()
    st.rerun()

# ✅ Newest chats on top (by last activity)
sorted_chats = sorted(
    st.session_state.chats.items(),
    key=lambda x: x[1].get("updated_at", 0),
    reverse=True,
)

for cid, c in sorted_chats:
    if st.sidebar.button(c["title"], key=f"chat_{cid}", use_container_width=True):
        st.session_state.current_chat_id = cid
        st.rerun()
    if cid == st.session_state.current_chat_id:
        st.sidebar.caption(f"session: {c['session_id']}")

# -------------------------------------------------
# BACKEND CALL
# -------------------------------------------------
def call_backend(user, text, session_id):
    try:
        r = requests.post(
            f"{backend_url.rstrip('/')}/chat",
            json={"user": user, "text": text, "session": session_id},
            timeout=60,
        )
        return r.json().get("reply", "(no reply)")
    except Exception:
        return "⚠️ Backend unreachable."

# -------------------------------------------------
# CUSTOM BUBBLE RENDERER (NO STREAMLIT CHAT MESSAGE)
# -------------------------------------------------
def render_bubble(role: str, content: str):
    safe = html.escape(content)
    st.markdown(
        f"""
        <div class="chat-row {role}">
            <div class="chat-bubble {role}">{safe}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -------------------------------------------------
# MAIN CHAT UI
# -------------------------------------------------
chat = current_chat()

# If there is no chat yet and none pending, create a pending chat for UI
if chat is None and st.session_state.pending_chat_id is None:
    new_id = str(uuid.uuid4())
    st.session_state.pending_chat_id = new_id
    st.session_state.current_chat_id = new_id
    st.session_state.pending_chat = {
        "title": "New Chat",
        "session_id": new_id,
        "messages": [],
        "updated_at": time.time(),
        "auto_titled": False,
    }
    chat = current_chat()

session_id = chat["session_id"]

# Seed greeting (only if chat has no messages)
if not chat["messages"]:
    chat["messages"].append(
        {
            "role": "assistant",
            "content": "How can I help you with your SAP account or labor laws?",
        }
    )

user_has_spoken = any(m["role"] == "user" for m in chat["messages"])

# Greeting block
greet_class = "greet-visible" if not user_has_spoken else "greet-hidden"
st.markdown(
    f"""
<div class="greeting {greet_class}">
    <h2>Hi, {username}!</h2>
</div>
""",
    unsafe_allow_html=True,
)

# Render history (custom bubbles)
st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)

for m in chat["messages"]:
    render_bubble(m["role"], m["content"])

st.markdown("</div></div>", unsafe_allow_html=True)

# -------------------------------
# ✅ PROCESS PENDING BACKEND CALL HERE
# (User message is already rendered above)
# -------------------------------
if st.session_state.pending_user_text is not None:
    pending_text = st.session_state.pending_user_text

    # Ensure we are operating on the real chat if it was pending
    ensure_real_chat_exists()
    chat = current_chat()

    with st.spinner("Thinking..."):
        reply = call_backend(username, pending_text, chat["session_id"])

    chat["messages"].append({"role": "assistant", "content": reply})
    chat["updated_at"] = time.time()

    # clear pending flag
    st.session_state.pending_user_text = None

    st.rerun()

# -------------------------------
# ✅ CHIPS pinned just above chat input (older Streamlit compatible)
# -------------------------------
if not user_has_spoken:
    suggestions = [
        "What is my employee ID number?",
        "Can you raise a leave?",
        "How many paid leaves do I have?",
    ]

    st.markdown('<div class="chips-wrapper">', unsafe_allow_html=True)

    left, c1, c2, c3, right = st.columns([2, 3, 3, 3, 2], vertical_alignment="center")

    for col, text in zip([c1, c2, c3], suggestions):
        with col:
            if st.button(text, key=f"suggest_{text}", use_container_width=True):
                ensure_real_chat_exists()
                chat = current_chat()

                touch_and_title(chat, text)

                # ✅ append user msg and defer backend to next run
                chat["messages"].append({"role": "user", "content": text})
                chat["updated_at"] = time.time()
                st.session_state.pending_user_text = text

                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# Chat input
input_text = st.chat_input("Type a message…")

if input_text:
    ensure_real_chat_exists()
    chat = current_chat()

    touch_and_title(chat, input_text)

    # ✅ append user msg first, then defer backend call
    chat["messages"].append({"role": "user", "content": input_text})
    chat["updated_at"] = time.time()

    st.session_state.pending_user_text = input_text
    st.rerun()
