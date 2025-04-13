# pip uninstall numpy pandas -y
# pip install --upgrade numpy pandas

# RUN: streamlit run admin.py
import streamlit as st
import pandas as pd
import os
import json
import random
import shutil
from datetime import datetime
from zipfile import ZipFile

# CONFIG
STUDENTS_FILE = "../students.json"
PAIRS_FILE = "../pairs.json"
CONFIG_FILE = "../config.json"
PDF_DIR = "../pdf_exports"
ARCHIVE_DIR = "../pdf_archiv"
TRANSLATIONS_DIR = "../translations"

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

st.title("🎓 Lehrer:innen-Panel")

# Load or initialize config
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"language": "de"}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

# Load or initialize pairs
def load_pairs():
    if os.path.exists(PAIRS_FILE):
        with open(PAIRS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_pairs(pairs):
    with open(PAIRS_FILE, "w") as f:
        json.dump(pairs, f, indent=2)

# Upload Excel and generate students.json
def process_excel(file):
    df = pd.read_excel(file)
    names = df.iloc[:, 0].dropna().tolist()
    with open(STUDENTS_FILE, "w") as f:
        json.dump(names, f, indent=2)
    return names

# Generate pairs
def generate_pairs(names, shared_topic=None):
    random.shuffle(names)
    topics = [
                 "Umweltschutz", "Technologie", "Schule der Zukunft", "Soziale Medien",
                 "Reisen", "Künstliche Intelligenz", "Freundschaft", "Sport"
             ] * 3
    pairs = {}
    for i in range(0, len(names), 2):
        pair = f"{names[i]} & {names[i+1]}"
        topic = shared_topic if shared_topic else topics[i // 2]
        pairs[pair] = topic
    save_pairs(pairs)
    return pairs

# Spracheinstellung
config = load_config()
lang = st.selectbox("🌐 Sprache wählen:", ["de", "en", "fr", "es"], index=["de", "en", "fr", "es"].index(config["language"]))
config["language"] = lang
save_config(config)

# Datei-Upload
st.subheader("📥 Schüler:innenliste hochladen")
uploaded_file = st.file_uploader("Excel-Datei hochladen (.xlsx)", type="xlsx")

use_shared_topic = st.checkbox("Gleiches Thema für alle Paare vorgeben")
shared_topic_input = ""
if use_shared_topic:
    shared_topic_input = st.text_input("Thema für alle Paare eingeben:")

if uploaded_file:
    names = process_excel(uploaded_file)
    st.success(f"{len(names)} Schüler:innen geladen.")
    shared = shared_topic_input if use_shared_topic else None
    pairs = generate_pairs(names, shared_topic=shared)
    st.success("Zufällige Paarungen wurden erstellt.")

# Paarübersicht anzeigen
pairs = load_pairs()
if pairs:
    st.subheader("👥 Aktuelle Paarungen")
    updated = False
    for pair, topic in pairs.items():
        new_topic = st.text_input(f"Thema für {pair}", value=topic, key=pair)
        if new_topic != topic:
            pairs[pair] = new_topic
            updated = True
    if updated:
        save_pairs(pairs)
        st.success("Themen aktualisiert.")

    if st.button("🔁 Paarungen neu mischen"):
        with open(STUDENTS_FILE, "r") as f:
            names = json.load(f)
        shared = shared_topic_input if use_shared_topic else None
        pairs = generate_pairs(names, shared_topic=shared)
        st.success("Neue Paarungen wurden erstellt.")

# PDF-Verwaltung
st.subheader("📄 Exportierte Konversationen")
pdfs = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
if pdfs:
    for pdf in pdfs:
        with open(os.path.join(PDF_DIR, pdf), "rb") as f:
            st.download_button(label=f"📥 {pdf}", data=f, file_name=pdf)

    if st.button("🗜️ Alle PDFs als ZIP exportieren"):
        zip_name = f"alle_konversationen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(PDF_DIR, zip_name)
        with ZipFile(zip_path, 'w') as zipf:
            for pdf in pdfs:
                zipf.write(os.path.join(PDF_DIR, pdf), arcname=pdf)
        with open(zip_path, "rb") as f:
            st.download_button("ZIP herunterladen", f, file_name=zip_name)

    if st.button("📦 PDFs archivieren"):
        for pdf in pdfs:
            shutil.move(os.path.join(PDF_DIR, pdf), os.path.join(ARCHIVE_DIR, pdf))
        st.success("Alle PDFs wurden ins Archiv verschoben.")
else:
    st.info("Noch keine PDFs vorhanden.")
