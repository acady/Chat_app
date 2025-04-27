import streamlit as st
import os
import json
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
from fpdf import FPDF
import time

# Load environment
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Load chat configuration
config_path = "chat_config.json"
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
    max_characters_per_refresh = config.get("max_characters_per_refresh", 20)
    max_words_per_message = config.get("max_words_per_message", 50)
else:
    max_characters_per_refresh = 20
    max_words_per_message = 50

st.title("💬 Schüler:innen-Chat")

# Setup Session State for name and chat history
if "name" not in st.session_state:
    st.session_state["name"] = ""
if "chat_lines" not in st.session_state:
    st.session_state["chat_lines"] = []
if "last_chat_length" not in st.session_state:
    st.session_state["last_chat_length"] = 0

# Name input with on_change
def save_name():
    st.session_state["name"] = st.session_state["name_input"]

if st.session_state["name"] == "":
    st.text_input("Gib deinen Namen ein:", key="name_input", on_change=save_name)
else:
    name = st.session_state["name"]

    # Suche nach Paar
    data = supabase.table('pairs').select('*').execute()
    pairs = data.data

    pair = None
    topic = None
    for p in pairs:
        if name == p['student1'] or name == p['student2']:
            pair = f"{p['student1']} & {p['student2']}"
            topic = p['topic']
            break

    if not pair:
        st.error("Du bist keiner Paarung zugewiesen.")
        st.stop()

    st.success(f"Willkommen im Chat, {name}!")
    st.info(f"🧠 Thema: {topic}")

    chat_log_dir = "chat_logs"
    os.makedirs(chat_log_dir, exist_ok=True)
    chat_log_path = os.path.join(chat_log_dir, f"{pair.replace(' & ', '_')}.txt")

    chat_placeholder = st.empty()

    def load_chat():
        if os.path.exists(chat_log_path):
            with open(chat_log_path, "r") as f:
                chat_lines = f.readlines()
        else:
            chat_lines = []
        return chat_lines

    def display_chat(chat_lines):
        with chat_placeholder.container():
            st.markdown("### Verlauf")
            for line in chat_lines:
                if name in line:
                    st.markdown(f"<div style='background-color: #cce5ff; padding: 10px; border-radius: 10px; margin: 5px; text-align: left; color: black;'>{line.strip()}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='background-color: #d6d6d6; padding: 10px; border-radius: 10px; margin: 5px; text-align: right; color: black;'>{line.strip()}</div>", unsafe_allow_html=True)

    new_chat_lines = load_chat()
    if new_chat_lines != st.session_state["chat_lines"]:
        st.session_state["chat_lines"] = new_chat_lines
    display_chat(st.session_state["chat_lines"])

    def send_message():
        msg = st.session_state["msg_input"].strip()
        if msg:
            if len(msg.split()) > max_words_per_message:
                st.warning(f"⚠️ Deine Nachricht enthält mehr als {max_words_per_message} Wörter. Bitte kürze sie.")
                return

            now = datetime.now().strftime("%H:%M")
            new_line = f"[{now}] {name}: {msg}\n"
            with open(chat_log_path, "a") as f:
                f.write(new_line)
            st.session_state["msg_input"] = ""

    st.text_input("Deine Nachricht:", key="msg_input", on_change=send_message)

    def export_chat_to_pdf():
        if not os.path.exists(chat_log_path):
            return None
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Thema: {topic}", ln=True)
        pdf.cell(200, 10, txt=f"Teilnehmer: {pair}", ln=True)
        pdf.ln(5)
        with open(chat_log_path, "r") as f:
            for line in f:
                if name in line:
                    pdf.set_x(10)
                    pdf.multi_cell(0, 10, txt=line.strip())
                else:
                    pdf.set_x(80)
                    pdf.multi_cell(0, 10, txt=line.strip())
        pdf_dir = "pdf_exports"
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, f"{pair.replace(' & ', '_')}.pdf")
        pdf.output(pdf_path)
        return pdf_path

    if st.button("📄 Konversation als PDF exportieren"):
        pdf_file = export_chat_to_pdf()
        if pdf_file:
            with open(pdf_file, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label="📥 Download Konversation als PDF",
                data=pdf_bytes,
                file_name=os.path.basename(pdf_file),
                mime="application/pdf"
            )

    if os.path.exists(chat_log_path) and st.button("🗑️ Konversation löschen"):
        os.remove(chat_log_path)
        st.success("Konversation erfolgreich gelöscht!")
        st.session_state["chat_lines"] = []
        st.rerun()

    current_chat_length = sum([len(line.strip()) for line in st.session_state["chat_lines"]])
    if current_chat_length - st.session_state["last_chat_length"] > max_characters_per_refresh:
        st.warning(f"⚠️ Zu viele Zeichen auf einmal hinzugefügt! (>{max_characters_per_refresh}) Bitte fair bleiben.")
    st.session_state["last_chat_length"] = current_chat_length

    time.sleep(5)
    st.rerun()
