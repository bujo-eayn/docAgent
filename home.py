# home.py (Complete Redesign for Chat Interface)
import json
import os

import requests
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(
    page_title="Document Chat Agent", layout="wide", initial_sidebar_state="expanded"
)

# Initialize session state
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chats" not in st.session_state:
    st.session_state.chats = []


def load_chats():
    """Load all available chats"""
    try:
        resp = requests.get(f"{BACKEND}/chats")
        if resp.status_code == 200:
            st.session_state.chats = resp.json()
    except Exception as e:
        st.error(f"Error loading chats: {e}")


def load_chat_messages(chat_id):
    """Load messages for a specific chat"""
    try:
        resp = requests.get(f"{BACKEND}/chats/{chat_id}")
        if resp.status_code == 200:
            chat_data = resp.json()
            st.session_state.messages = chat_data.get("messages", [])
            return chat_data
    except Exception as e:
        st.error(f"Error loading chat: {e}")
    return None


def create_new_chat(uploaded_file):
    """Create a new chat by uploading a document"""
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

    with st.spinner("📄 Processing document... This may take a minute."):
        try:
            resp = requests.post(f"{BACKEND}/chats/create", files=files, timeout=600)
            if resp.status_code == 200:
                result = resp.json()
                st.session_state.current_chat_id = result["chat_id"]
                load_chats()
                load_chat_messages(result["chat_id"])
                st.success(
                    f"✅ Chat created! Processed {result['chunks_created']} context chunks."
                )
                st.rerun()
            else:
                st.error(f"Error: {resp.status_code} - {resp.text}")
        except Exception as e:
            st.error(f"Error creating chat: {e}")


def send_message(chat_id, question):
    """Send a message in the current chat with streaming response"""
    st.session_state.messages.append({"role": "user", "content": question})

    data = {"question": question}

    def response_stream():
        """Generator that yields streamed text chunks from backend"""
        try:
            with requests.post(
                f"{BACKEND}/chats/{chat_id}/message",
                data=data,
                stream=True,
                timeout=600,
            ) as resp:
                resp.raise_for_status()

                for chunk in resp.iter_lines():
                    if not chunk:
                        continue
                    decoded = chunk.decode("utf-8")

                    # Expected format: "data: <text>"
                    if decoded.startswith("data:"):
                        payload = decoded[len("data:") :].strip()

                        # Skip control tokens
                        if not payload or payload == "[DONE]":
                            continue

                        # 🔧 Add a space between fragments for proper word spacing
                        if not payload.startswith(
                            (" ", "\n", ".", ",", "!", "?", ";", ":")
                        ):
                            yield " "
                        yield payload

        except Exception as e:
            yield f"\n⚠️ Error: {str(e)}\n"

    # 🧠 Stream response live to UI and capture final output
    with st.chat_message("assistant"):
        full_response = st.write_stream(response_stream)

    # Store the assistant message in session state
    st.session_state.messages.append({"role": "assistant", "content": full_response})


# ===== UI LAYOUT =====


# Sidebar
with st.sidebar:
    st.title("💬 Chats")

    # New Chat Section
    st.subheader("Start New Chat")
    uploaded_file = st.file_uploader(
        "Upload a document image",
        type=["png", "jpg", "jpeg", "webp"],
        key="new_chat_uploader",
    )

    if uploaded_file and st.button("Create New Chat", type="primary"):
        create_new_chat(uploaded_file)

    st.divider()

    # Load existing chats
    if st.button("🔄 Refresh Chats"):
        load_chats()

    # Display chat list
    st.subheader("Your Chats")
    load_chats()

    if st.session_state.chats:
        for chat in st.session_state.chats:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(
                    f"📄 {chat['title'][:30]}...",
                    key=f"chat_{chat['id']}",
                    use_container_width=True,
                ):
                    st.session_state.current_chat_id = chat["id"]
                    load_chat_messages(chat["id"])
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_{chat['id']}"):
                    requests.delete(f"{BACKEND}/chats/{chat['id']}")
                    if st.session_state.current_chat_id == chat["id"]:
                        st.session_state.current_chat_id = None
                        st.session_state.messages = []
                    load_chats()
                    st.rerun()
    else:
        st.info("No chats yet. Upload a document to start!")

# Main Chat Area
st.title("📚 Document Chat Agent")

if st.session_state.current_chat_id:
    # Load current chat details
    chat_data = load_chat_messages(st.session_state.current_chat_id)

    if chat_data:
        st.caption(f"💬 Chat: {chat_data['title']}")
        st.caption(f"📄 Document: {chat_data['document_filename']}")

    # Display chat messages
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]

        if role == "system":
            st.info(content)
        elif role == "user":
            with st.chat_message("user"):
                st.write(content)
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.write(content)

                # Show context if available
                if message.get("context_used"):
                    with st.expander("📚 Context Used"):
                        st.markdown(message["context_used"])

    # Chat input
    question = st.chat_input("Ask a question about the document...")
    if question:
        send_message(st.session_state.current_chat_id, question)
        st.rerun()

else:
    st.info("👈 Start a new chat by uploading a document in the sidebar!")

    # Show welcome message with instructions
    st.markdown(
        """
    ## Welcome to Document Chat Agent! 🚀
    
    ### How it works:
    1. **Upload a Document** - Upload an image of a chart, graph, diagram, or any document
    2. **AI Extracts Information** - The system extracts ALL information from your document
    3. **Ask Questions** - Chat with the AI about your document using natural language
    4. **Context-Aware Answers** - Get accurate answers based on the document content
    
    ### Features:
    - 📄 **Multiple Chats** - Manage multiple document conversations
    - 🔍 **Smart Search** - pgvector-powered semantic search for accurate context
    - 💬 **Chat History** - All conversations are saved and accessible
    - 🎯 **Scoped Context** - Each chat only accesses its own document
    
    **Get started by uploading a document in the sidebar!** →
    """
    )
