import streamlit as st
import random
import time


# Streamed response emulator
def response_generator():
    response = random.choice(
        [
            "Hello there! How can I assist you today?",
            "Hi, human! Is there anything I can help you with?",
            "Do you need help?",
        ]
    )
    for word in response.split():
        yield word + " "
        time.sleep(0.05)

st.set_page_config(page_title="HR Agent", page_icon="🤖", layout="centered")

st.markdown("""
<style>
/* ===== App-wide Gradient Background ===== */
html, body, [data-testid="stAppViewContainer"], .stApp {
  background: linear-gradient(135deg, #612C53 0%, #24E0BB 100%) !important;
  color: #fff !important;
}

/* ===== Remove default white layers ===== */
[data-testid="stHeader"], footer, [data-testid="stToolbar"], [data-testid="stBottomBar"] {
  background: transparent !important;
  box-shadow: none !important;
}

.stApp, .stApp *:not(svg):not(path) {
  color: #fff !important;
}

/* ===== Chat input area transparency ===== */
[data-testid="stChatInputContainer"] {
  background: transparent !important;
  box-shadow: none !important;
}

/* Textarea styling for chat input */
[data-testid="stChatInputContainer"] textarea {
  background: rgba(255, 255, 255, 0.1) !important; /* semi-transparent */
  backdrop-filter: blur(8px);
  color: #fff !important;
  border: 1px solid rgba(255, 255, 255, 0.4) !important;
  border-radius: 10px;
}

/* Placeholder color */
[data-testid="stChatInputContainer"] textarea::placeholder {
  color: rgba(255, 255, 255, 0.7) !important;
}
            
            [data-testid="stBottomBar"]::after {
  content: "Demo UI Made with ❤️";
  display: block;
  text-align: center;
  margin-top: 8px;
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  pointer-events: none; /* ensure clicks go through */
}
            
</style>
""", unsafe_allow_html=True)




st.title("HR Agent")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        response = st.write_stream(response_generator())
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
