"""Streamlit web interface for the Gardening Chatbot."""

import streamlit as st

import config
from main import GardeningChatbot


st.set_page_config(
    page_title="GreenThumb Gardening Assistant",
    page_icon="🌿",
    layout="centered",
)


def initialize_chatbot() -> GardeningChatbot:
    """Create one chatbot instance for the current browser session."""
    config.validate_config()
    chatbot = GardeningChatbot()
    chatbot.check_api_connection()
    return chatbot


def reset_chat() -> None:
    """Clear the current browser session's conversation."""
    chatbot = st.session_state.get("chatbot")
    if chatbot is not None:
        chatbot.reset_conversation()
    st.session_state.messages = []


st.title("🌿 GreenThumb")
st.caption("A gardening assistant protected by layered AI guardrails")

with st.sidebar:
    st.subheader("About")
    st.write(
        "Ask questions about plants, soil, watering, pests, pruning, "
        "compost, lawns, or general gardening."
    )
    st.info("Messages outside the gardening topic may be refused.")
    st.button("Reset conversation", use_container_width=True, on_click=reset_chat)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chatbot" not in st.session_state:
    try:
        with st.spinner("Connecting to the AI service..."):
            st.session_state.chatbot = initialize_chatbot()
    except Exception:
        st.error("The chatbot could not connect to the AI service.")
        st.info(
            "Check the Azure OpenAI environment variables configured for this app, "
            "then reload the page."
        )
        st.stop()

if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🌱"):
        st.write(
            "Hello! I am GreenThumb. Ask me anything about plants, soil, "
            "watering, pests, pruning, or compost."
        )

for message in st.session_state.messages:
    avatar = "🌱" if message["role"] == "assistant" else None
    with st.chat_message(message["role"], avatar=avatar):
        st.write(message["content"])

if prompt := st.chat_input("Ask a gardening question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant", avatar="🌱"):
        with st.spinner("Checking and preparing a response..."):
            try:
                response = st.session_state.chatbot.process_input(prompt)
            except Exception:
                response = (
                    "The request could not be completed because the AI service "
                    "is temporarily unavailable. Please try again."
                )
        st.write(response)

    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )
