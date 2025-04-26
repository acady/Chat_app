#  pip install streamlit
# pip install fpdf
# pip install streamlit fpdf python-dotenv

# RUN: ]streamlit run app.py

import streamlit as st
import json
import os
import random
from datetime import datetime
from fpdf import FPDF
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

# Automatisch alle 3 Sekunden die Seite neu laden
st_autorefresh(interval=2000, key="chat_refresh")

# Load environment variables
load_dotenv()

# ----- CONFIG -----
STUDENT_FILE = os.getenv("STUDENT_FILE", "students.json")
PAIR_FILE = os.getenv("PAIR_FILE", "pairs.json")
CHAT_LOG_DIR = os.getenv("CHAT_LOG_DIR", "chat_logs")
PDF_DIR = os.getenv("PDF_DIR", "pdf_exports")

# Ensure dirs exist
os.makedirs(CHAT_LOG_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# Load students
if not os.path.exists(STUDENT_FILE):
    st.error("Die Datei students.json fehlt.")
    st.stop()

with open(STUDENT_FILE, "r") as f:
    students = json.load(f)

# Generate or load pairs
def get_or_generate_pairs():
    if os.path.exists(PAIR_FILE):
        with open(PAIR_FILE, "r") as f:
            return json.load(f)
    random.shuffle(students)
    pairs = {}
    topics = [
                 "Umweltschutz", "Technologie", "Schule der Zukunft", "Soziale Medien",
                 "Reisen", "Künstliche Intelligenz", "Freundschaft", "Sport"
             ] * 3  # Repeat to cover all
    for i in range(0, len(students), 2):
        pair = f"{students[i]} & {students[i+1]}"
        pairs[pair] = topics[i // 2]
    with open(PAIR_FILE, "w") as f:
        json.dump(pairs, f)
    return pairs

pairs = get_or_generate_pairs()

# Find the pair for a student
def find_pair(name):
    for pair in pairs:
        if name in pair:
            return pair, pairs[pair]
    return None, None

# PDF Export
def export_chat_to_pdf(pair_name):
    log_path = os.path.join(CHAT_LOG_DIR, f"{pair_name.replace(' & ', '_')}.txt")
    if not os.path.exists(log_path):
        return None

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Thema: {pairs[pair_name]}", ln=True)
    pdf.cell(200, 10, txt=f"Teilnehmer: {pair_name}", ln=True)
    pdf.ln(5)

    with open(log_path, "r") as f:
        for line in f:
            pdf.multi_cell(0, 10, txt=line.strip())

    pdf_path = os.path.join(PDF_DIR, f"{pair_name.replace(' & ', '_')}.pdf")
    pdf.output(pdf_path)
    return pdf_path

# --- Streamlit UI ---
st.title("💬 Schüler:innen-Chat")

name = st.text_input("Gib deinen Namen ein:")

if name:
    pair, topic = find_pair(name)
    if not pair:
        st.error("Du bist keiner Paarung zugewiesen.")
        st.stop()

    st.success(f"Willkommen im Chat, {name}!")
    st.info(f"🧠 Thema: {topic}")

    chat_log_path = os.path.join(CHAT_LOG_DIR, f"{pair.replace(' & ', '_')}.txt")

    # Load chat
    if os.path.exists(chat_log_path):
        with open(chat_log_path, "r") as f:
            chat_lines = f.readlines()
    else:
        chat_lines = []

    st.markdown("### Verlauf")
    for line in chat_lines:
        st.write(line.strip())

    # Message sending via callback
    def send_message():
        msg = st.session_state["msg_input"].strip()
        if msg:
            now = datetime.now().strftime("%H:%M")
            new_line = f"[{now}] {name}: {msg}\n"
            with open(chat_log_path, "a") as f:
                f.write(new_line)
            st.session_state["msg_input"] = ""
            st.query_params["refresh"] = str(datetime.now().timestamp())

    st.text_input("Deine Nachricht:", key="msg_input", on_change=send_message)

    # Export button
    if st.button("📄 Konversation als PDF exportieren"):
        pdf_file = export_chat_to_pdf(pair)
        if pdf_file:
            with open(pdf_file, "rb") as f:
                st.download_button("Download PDF", f, file_name=os.path.basename(pdf_file))
        else:
            st.error("Keine Chatdaten vorhanden zum Exportieren.")