# ui/app.py
import os
import uuid
import requests
import streamlit as st

# ------------- Page setup -------------
st.set_page_config(page_title="HR Agent Chat", page_icon="🤖", layout="centered")

# ------------- Sidebar controls -------------
st.sidebar.title("⚙️ Settings")

backend_default = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
backend_url = st.sidebar.text_input("Backend URL", value=backend_default, help="Your FastAPI base URL")

username = st.sidebar.text_input("Username", value="Elaph", help="Must exist in the DB (e.g., 'Elaph')")
lang = st.sidebar.radio("UI Language", options=["English", "العربية"], horizontal=True)

# Per-tab session id for backend memory threads
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# New chat MUST create a new session id
if st.sidebar.button("🧹 New chat"):
    st.session_state.messages = []
    st.session_state.session_id = str(uuid.uuid4())   # NEW thread id
    st.rerun()

# (Optional) show current session id for debugging
st.sidebar.caption(f"session: {st.session_state.session_id}")

# ------------- RTL/LTR tweak -------------
is_ar = (lang == "العربية")
direction_css = (
    "<style>html, body, [data-testid='stAppViewContainer'] * { direction: RTL; text-align: right; }</style>"
    if is_ar else
    "<style>html, body, [data-testid='stAppViewContainer'] * { direction: LTR; text-align: left; }</style>"
)
st.markdown(direction_css, unsafe_allow_html=True)

# ------------- Header -------------
st.title("🤖 HR Agent")
st.caption("Chat with your HR agent (DB-backed).")

# ------------- Chat history -------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! How can I help you with leaves or profile today?"} if not is_ar
        else {"role": "assistant", "content": "مرحبًا! كيف أستطيع مساعدتك في الإجازات أو ملفك الشخصي؟"}
    ]

for m in st.session_state.messages:
    with st.chat_message("assistant" if m["role"] == "assistant" else "user"):
        st.markdown(m["content"])

# ------------- Backend call -------------
def call_backend(user: str, text: str, session_id: str) -> str:
    """POST to FastAPI /chat and return the 'reply' string or a friendly error."""
    try:
        resp = requests.post(
            f"{backend_url.rstrip('/')}/chat",
            json={"user": user, "text": text, "session": session_id},  # include session!
            timeout=60,
        )
        if resp.status_code != 200:
            try:
                data = resp.json()
                detail = data.get("detail") or data
            except Exception:
                detail = resp.text
            return f"Server error ({resp.status_code}): {detail}"
        data = resp.json()
        return data.get("reply", "(no reply)")
    except requests.exceptions.ConnectionError:
        return "Could not reach backend. Is FastAPI running on the given URL?"
    except Exception as e:
        return f"Unexpected error: {e}"

# ------------- Chat input -------------
prompt_label = "Type a message…" if not is_ar else "اكتب رسالتك…"
user_text = st.chat_input(prompt_label)

if user_text:
    # show the user's message
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # call the backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking…" if not is_ar else "يفكّر…"):
            reply = call_backend(username.strip(), user_text.strip(), st.session_state.session_id)
            st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
