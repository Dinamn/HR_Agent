import streamlit as st

# ----- Page config -----
st.set_page_config(page_title="HR Agent", page_icon="🤖", layout="centered")

# ----- Global styles -----
st.markdown(
    """
    <style>
      /* Full gradient background for entire page */
      .stApp {
        background: linear-gradient(135deg, #612C53 0%, #24E0BB 100%) fixed;
      }

      /* White card container for chat */
      .chat-card {
        background: #FFFFFF;
        border-radius: 22px;
        box-shadow: 0 10px 35px rgba(0,0,0,0.2);
        padding: 3rem 2.5rem 2rem 2.5rem;
        max-width: 900px;
        margin: 4rem auto 5rem auto;
        min-height: 70vh;  /* ensure it feels tall enough */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
      }

      /* Chat message bubbles */
      [data-testid="stChatMessage"] {
        border-radius: 12px;
      }

      /* Title styling */
      .page-title {
        text-align: center;
        color: white;
        margin-top: 3rem;
        font-size: 2.2rem;
        font-weight: 600;
      }

      /* Footer styling */
      .app-footer {
        text-align: center;
        color: rgba(255,255,255,0.85);
        font-size: 0.9rem;
        margin-bottom: 2rem;
      }

      /* Mobile responsiveness */
      @media (max-width: 640px) {
        .chat-card {
          margin: 2rem auto;
          padding: 1.5rem 1.25rem;
          min-height: 80vh;
        }
        .page-title {
          font-size: 1.7rem;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----- Header -----
st.markdown("<h2 class='page-title'>🤖 HR Agent</h2>", unsafe_allow_html=True)

# ----- White card wrapper -----
with st.container():
    st.markdown("<div class='chat-card'>", unsafe_allow_html=True)

    # ----- Session state -----
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm your personal HR assistant, how can I help you today?"}
        ]

    # ----- Dummy backend -----
    def ask_hr_agent(user_text: str) -> str:
        return f"I received: “{user_text}”. (Backend integration coming soon!)"

    # ----- Chat messages -----
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # ----- Input (inside the white card now) -----
    user_text = st.chat_input("Ask Anything...")

    if user_text:
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.write(user_text)

        reply = ask_hr_agent(user_text)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.write(reply)

    st.markdown("</div>", unsafe_allow_html=True)

# ----- Footer -----
st.markdown(
    "<div class='app-footer'>Demo UI • Made with ❤️</div>",
    unsafe_allow_html=True,
)
