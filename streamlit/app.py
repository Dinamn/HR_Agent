import streamlit as st

st.set_page_config(page_title="HR Agent", page_icon="🤖", layout="centered")

# ===================== STYLES =====================
st.markdown("""
<style>
/* Full-page gradient */
html, body, .stApp, [data-testid="stAppViewContainer"] {
  background: linear-gradient(135deg, #612C53 0%, #24E0BB 100%) !important;
  min-height: 100%;
  color: #fff !important;
}

/* Transparent Streamlit chrome */
[data-testid="stHeader"], footer, [data-testid="stToolbar"], [data-testid="stBottomBar"] {
  background: transparent !important;
  box-shadow: none !important;
  border: none !important;
  color: #fff !important;
}

/* Content area (reserve space bottom for chat input + footer) */
.block-container {
  background: transparent !important;
  max-width: 900px;
  margin: 5rem auto 0 auto !important;
  padding: 0 1rem !important;
}
.block-container::after { content:""; display:block; height: 9.5rem; } /* keep last messages visible */

/* Footer that sits just above the input */
.page-footer {
  opacity: .85;
  text-align: center;
  margin: 1rem 0 0 0;
  font-size: 0.9rem;
}

/* ===================== INPUT FIELD ===================== */
/* container */
[data-testid="stChatInput"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* inner textarea wrapper */
[data-testid="stChatInput"] textarea {
  background: rgba(0,0,0,0.45) !important;

  border-radius: 22px !important;
  color: #fff !important;
  padding: 0.9rem 1.1rem !important;
  box-shadow: 0 6px 20px rgba(0,0,0,0.22);

}

/* placeholder color */
[data-testid="stChatInput"] textarea::placeholder {
  color: rgba(255,255,255,0.85);
}

/* send button icon area */
[data-testid="stChatInput"] button {
  border-radius: 999px !important;
  border: 1px solid rgba(255,255,255,0.35) !important;
  background: rgba(0,0,0,0.45) !important;
  box-shadow: 0 6px 20px rgba(0,0,0,0.22);
}

</style>
""", unsafe_allow_html=True)

# ===================== HEADER =====================
st.markdown("<h2 style='text-align:center; margin:0;'>HR Agent</h2>", unsafe_allow_html=True)

# ===================== STATE =====================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm your personal HR assistant — how can I help you today?"}
    ]

def ask_hr_agent(user_text: str) -> str:
    # TODO: replace with your backend call
    return f"I received: “{user_text}”. ( Backend integration here later :) )"

# ===================== CHAT HISTORY =====================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ===================== FOOTER (above the input) =====================
st.markdown("<div class='page-footer'>Demo UI • Made with Love ❤️</div>", unsafe_allow_html=True)

# ===================== INPUT =====================
prompt = st.chat_input(placeholder="Ask Anything..")

# ===================== HANDLE SUBMIT =====================
if prompt and prompt.strip():
    # Update state first
    st.session_state.messages.append({"role": "user", "content": prompt})
    reply = ask_hr_agent(prompt)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    # Rerun so new messages render in the history above the footer/input (not below)
    st.rerun()
