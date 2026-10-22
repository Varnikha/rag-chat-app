import streamlit as st
import requests
from typing import Optional, List, Dict, Any

API_BASE = "https://onrender.com"


st.set_page_config(page_title="RAG Chat", layout="wide")
 
if "jwt" not in st.session_state:
    st.session_state.jwt = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None


def api_headers() -> Dict[str, str]:
    headers = {"accept": "application/json"}
    if st.session_state.jwt:
        headers["Authorization"] = f"Bearer {st.session_state.jwt}"
    return headers


def login(username: str, password: str) -> Optional[str]:
    try:
        response = requests.post(
            f"{API_BASE}/auth/login",
            json={"username": username, "password": password},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("access_token") or data.get("token")
    except Exception as exc:
        st.error(f"Login failed: {exc}")
        return None


def register(username: str, password: str, email: str = "") -> bool:
    try:
        payload = {"username": username, "password": password}
        if email:
            payload["email"] = email
        requests.post(f"{API_BASE}/auth/register", json=payload, timeout=20).raise_for_status()
        return True
    except Exception as exc:
        st.error(f"Registration failed: {exc}")
        return False


def create_chat_session() -> Optional[int]:
    try:
        response = requests.post(f"{API_BASE}/chat/sessions", headers=api_headers(), timeout=20)
        response.raise_for_status()
        data = response.json()
        st.session_state.session_id = data.get("id")
        return st.session_state.session_id
    except Exception as exc:
        st.error(f"Could not create chat session: {exc}")
        return None


def fetch_session_messages(session_id: int) -> List[Dict[str, Any]]:
    try:
        response = requests.get(f"{API_BASE}/chat/sessions/{session_id}/messages", headers=api_headers(), timeout=20)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


def upload_document(file):
    try:
        files = {"file": (file.name, file.getvalue())}
        response = requests.post(f"{API_BASE}/documents/upload", files=files, headers=api_headers(), timeout=60)
        response.raise_for_status()
        st.success("Document uploaded and processed successfully.")
    except Exception as exc:
        st.error(f"Upload failed: {exc}")


def send_message(text: str):
    if st.session_state.session_id is None:
        if not create_chat_session():
            return None

    try:
        response = requests.post(
            f"{API_BASE}/chat/sessions/{st.session_state.session_id}/messages",
            json={"content": text},
            headers=api_headers(),
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"Message send failed: {exc}")
        return None


st.title("RAG Chat")

with st.sidebar:
    st.subheader("Account")

    if not st.session_state.jwt:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            token = login(username, password)
            if token:
                st.session_state.jwt = token
                st.session_state.session_id = None
                st.rerun()

        st.markdown("---")
        reg_user = st.text_input("New username", key="reg_user")
        reg_password = st.text_input("New password", type="password", key="reg_password")
        reg_email = st.text_input("Email (optional)", key="reg_email")
        if st.button("Register"):
            if register(reg_user, reg_password, reg_email):
                st.success("Registered successfully. Please log in.")
    else:
        st.success("Logged in")
        if st.button("Logout"):
            st.session_state.jwt = None
            st.session_state.session_id = None
            st.rerun()

if st.session_state.jwt and st.session_state.session_id is None:
    create_chat_session()

left_col, right_col = st.columns([1, 2])

with left_col:
    st.subheader("Upload document")
    uploaded_file = st.file_uploader("Choose a file", type=["txt", "md", "pdf", "docx"])
    if uploaded_file is not None:
        upload_document(uploaded_file)

with right_col:
    st.subheader("Chat")

    if st.session_state.session_id is not None:
        history = fetch_session_messages(st.session_state.session_id)
        for message in history:
            role = message.get("role", "assistant")
            content = message.get("content", "")
            if role == "user":
                st.chat_message("user").write(content)
            else:
                st.chat_message("assistant").write(content)

    prompt = st.chat_input("Ask a question about your documents...")
    if prompt:
        if st.session_state.session_id is None:
            create_chat_session()
        response = send_message(prompt)
        if response:
            content = response.get("content") or str(response)
            st.chat_message("user").write(prompt)
            st.chat_message("assistant").write(content)
            st.rerun()

