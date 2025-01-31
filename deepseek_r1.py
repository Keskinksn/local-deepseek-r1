import ollama
import streamlit as st
import json
import os
import pandas as pd
import PyPDF2
import docx
from io import StringIO
from datetime import datetime


st.set_page_config(page_title="🧠 DeepSeek R1 ChatBot", layout="wide")
st.title("🧠 DeepSeek R1 ChatBot")
st.write("**Local DeepSeek R1**!")


selected_model = "deepseek-r1:7b"


CHAT_HISTORY_FILE = "chat_history.json"

def load_chat_history():
    """Loads the chat history."""
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_chat_history():
    """Saves the chat history."""
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.all_chats, f, ensure_ascii=False, indent=4)


def read_file(file):
    """Reads supported file types and returns their content as text."""
    if file.name.endswith(".txt") or file.name.endswith(".md"):
        return file.getvalue().decode("utf-8")

    elif file.name.endswith(".csv"):
        df = pd.read_csv(file)
        return df.to_string(index=False)

    elif file.name.endswith(".json"):
        json_data = json.load(file)
        return json.dumps(json_data, indent=4, ensure_ascii=False)

    elif file.name.endswith(".xlsx"):
        df = pd.read_excel(file, engine="openpyxl")
        return df.to_string(index=False)

    elif file.name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])

    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        return "\n".join([para.text for para in doc.paragraphs])

    return None


if "file_content" not in st.session_state:
    st.session_state.file_content = None

uploaded_file = st.sidebar.file_uploader("📂 Upload a file",
                                         type=["txt", "md", "csv", "json", "xlsx", "pdf", "docx"])

if uploaded_file:
    file_content = read_file(uploaded_file)
    if file_content:
        st.session_state.file_content = file_content[:3000]
        st.sidebar.success("✅ File uploaded, you can now ask questions to the model!")

if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_chat_history()

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

def new_chat():
    """Starts a new chat and clears the previous file content."""
    if st.session_state.current_chat_id and st.session_state.messages:
        st.session_state.all_chats[st.session_state.current_chat_id] = st.session_state.messages
        save_chat_history()

    new_chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.session_state.current_chat_id = new_chat_id
    st.session_state.messages = []

    st.session_state.file_content = None
    st.session_state.uploaded_file = None

st.sidebar.button("🆕 New Chat", on_click=new_chat)

st.sidebar.write("📁 **Past Chats**")
if st.session_state.all_chats:
    for chat_id in sorted(st.session_state.all_chats.keys(), reverse=True):
        col1, col2 = st.sidebar.columns([0.8, 0.2])
        if col1.button(f"🔍 {chat_id}"):
            st.session_state.messages = st.session_state.all_chats[chat_id]
            st.session_state.current_chat_id = chat_id
        if col2.button("🗑", key=f"delete_{chat_id}", help="Delete chat", use_container_width=True):
            del st.session_state.all_chats[chat_id]
            save_chat_history()
            st.rerun()
else:
    st.sidebar.write("❌ No chat history found!")

if st.session_state.current_chat_id is None:
    new_chat()


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(f"**{'👤 User' if msg['role'] == 'user' else '🤖 Assistant'}:** {msg['content']}")


user_input = st.chat_input("Type your message and press Enter...")

def format_message(role, content):
    """
    Detects <think> parts in the message and places them in a gray box.
    """
    if "<think>" in content:
        parts = content.split("<think>")
        formatted_content = parts[0]
        for part in parts[1:]:
            if "</think>" in part:
                think_part, rest = part.split("</think>", 1)
                think_box = f"<div style='border:2px solid gray; padding:10px; background-color:#585858; border-radius:5px; margin:10px 0;'><b>🤔 Model Thinking:</b><br>{think_part}</div>"
                formatted_content += think_box + rest
        return f"<b>{role}:</b> {formatted_content}"
    return f"<b>{role}:</b> {content}"

if user_input:
    if st.session_state.file_content:
        full_message = f"File content:\n\n{st.session_state.file_content}\n\nQuestion: {user_input}"
    else:
        full_message = user_input

    st.session_state.messages.append({"role": "user", "content": full_message})

    with st.chat_message("user"):
        st.markdown(f"**👤 User:** {user_input}")

    bot_reply = ""
    response = ollama.chat(
        model=selected_model,
        messages=st.session_state.messages,
        stream=True
    )

    with st.chat_message("assistant"):
        bot_response_area = st.empty()
        for chunk in response:
            chunk_text = chunk.get("message", {}).get("content", "")
            bot_reply += chunk_text
            bot_response_area.markdown(format_message("🤖 Assistant", bot_reply), unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    st.session_state.all_chats[st.session_state.current_chat_id] = st.session_state.messages
    save_chat_history()
