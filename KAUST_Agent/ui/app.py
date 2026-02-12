# ui/app.py
import os
import uuid
import requests
import streamlit as st

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="HR Agent", page_icon="🤖", layout="wide")

# -------------------------------------------------
# MULTI-CHAT STATE
# -------------------------------------------------
if "chats" not in st.session_state:
    cid = str(uuid.uuid4())
    st.session_state.chats = {
        cid: {"title": "Chat 1", "session_id": cid, "messages": []}
    }
    st.session_state.current_chat_id = cid

def current_chat():
    return st.session_state.chats[st.session_state.current_chat_id]

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.title("Chats")

backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
username = "Dina"
is_ar = False

# New Chat
def new_chat():
    new_id = str(uuid.uuid4())
    index = len(st.session_state.chats) + 1
    st.session_state.chats[new_id] = {
        "title": f"Chat {index}",
        "session_id": new_id,
        "messages": [],
    }
    st.session_state.current_chat_id = new_id

if st.sidebar.button("➕ New chat", use_container_width=True):
    new_chat()
    st.rerun()

# Chat list
for cid, chat in st.session_state.chats.items():
    if st.sidebar.button(chat["title"], key=f"chat_{cid}", use_container_width=True):
        st.session_state.current_chat_id = cid
        st.rerun()
    if cid == st.session_state.current_chat_id:
        st.sidebar.caption(f"session: {chat['session_id']}")

# -------------------------------------------------
# CSS (ANIMATION + FADE)
# -------------------------------------------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #25C7BC, #602650, #ffffff);
    background-size: 200% 200%;
    animation: gradientMove 18s ease infinite;
}

@keyframes gradientMove {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}

.main-card {
    background: rgba(255,255,255,0.85);
    padding: 2rem 3rem;
    border-radius: 24px;
    max-width: 900px;
    margin: auto;
}

/* Greeting fade-out */
.greeting {
    transition: opacity .6s ease, max-height .6s ease, margin-bottom .6s ease;
    overflow: hidden;
}
.greet-visible {opacity:1; max-height:200px; margin-bottom:1rem;}
.greet-hidden  {opacity:0; max-height:0; margin-bottom:0;}

.sparkles {
    font-size: 2rem;
    animation: float 3s ease-in-out infinite;
}
@keyframes float {
    0% {transform: translateY(0);}
    50% {transform: translateY(-6px);}
    100% {transform: translateY(0);}
}
</style>
""", unsafe_allow_html=True)

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
    except:
        return "⚠️ Backend unreachable."

# -------------------------------------------------
# MAIN CHAT UI
# -------------------------------------------------
chat = current_chat()
session_id = chat["session_id"]

with st.container():
    # Seed initial assistant greeting
    if not chat["messages"]:
        chat["messages"].append({
            "role": "assistant",
            "content": "How can I help you with your SAP account or labor laws?"
        })

    # Detect if user already spoke
    user_has_spoken = any(m["role"] == "user" for m in chat["messages"])

    # -------------------------------
    # GREETING WITH FADE TRANSITION
    # -------------------------------
    greet_class = "greet-visible" if not user_has_spoken else "greet-hidden"
    st.markdown(f"""
    <div class="greeting {greet_class}">
        <div class="sparkles">✨</div>
        <h2>👋 Hi, {username}!</h2>
    </div>
    """, unsafe_allow_html=True)

# ----------- CHAT HISTORY + PLACEHOLDER ABOVE INPUT -----------
pending_container = st.empty()

# render saved history
for m in chat["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])





    # -------------------------------
    # SUGGESTION CHIPS (ONLY BEFORE FIRST USER MESSAGE)
    # -------------------------------
    if not user_has_spoken:
        suggestions = [
            "What is my employee ID number?",
            "Can you raise a leave?",
            "How many paid leaves do I have?",
        ]
        cols = st.columns(len(suggestions))
        for col, text in zip(cols, suggestions):
            with col:
                if st.button(text):
                    # User message
                    chat["messages"].append({"role": "user", "content": text})
                    with st.chat_message("user"):
                        st.markdown(text)

                    # Assistant reply
                    with st.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            reply = call_backend(username, text, session_id)
                            st.markdown(reply)

                    chat["messages"].append({"role": "assistant", "content": reply})
                    st.rerun()


# ----------- CHAT INPUT + LIVE RENDERING ABOVE INPUT -----------
input_text = st.chat_input("Type a message…")

if input_text:
    # show temporary messages ABOVE the input using placeholder
    with pending_container.container():
        with st.chat_message("user"):
            st.markdown(input_text)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = call_backend(username, input_text, session_id)

    # save messages permanently
    chat["messages"].append({"role": "user", "content": input_text})
    chat["messages"].append({"role": "assistant", "content": reply})

    st.rerun()
    