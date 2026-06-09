import streamlit as st
import pandas as pd
import os
import random
import json
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "lehrer")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Lehrer:innen-Panel", page_icon="🎓")

# Passwortschutz
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if not st.session_state["admin_authenticated"]:
    st.title("🔒 Admin-Bereich")
    pwd = st.text_input("Passwort:", type="password")
    if st.button("Anmelden"):
        if pwd == ADMIN_PASSWORD:
            st.session_state["admin_authenticated"] = True
            st.rerun()
        else:
            st.error("Falsches Passwort.")
    st.stop()

config_path = "chat_config.json"
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        saved_config = json.load(f)
else:
    saved_config = {}

st.title("🎓 Lehrer:innen-Panel")

if st.button("🔓 Abmelden", type="secondary"):
    st.session_state["admin_authenticated"] = False
    st.rerun()

# Datei-Upload
st.subheader("📥 Schüler:innenliste hochladen")
uploaded_file = st.file_uploader("Excel-Datei hochladen (.xlsx)", type="xlsx")

# Spracheinstellung
st.subheader("🌍 Spracheinstellungen")
language = st.selectbox("Wähle die Sprache:", options=["de", "en", "fr", "es"], index=0)

# Thema-Einstellung
shared_topic = st.text_input("📚 Thema für alle Paare (optional)")
use_shared_topic = st.checkbox("Allen Paaren das gleiche Thema zuweisen", value=False)

# Regeln für Chatüberwachung
st.subheader("🔒 Chat Regeln")
max_characters_per_refresh = st.number_input(
    "Maximale neue Zeichen pro 5 Sekunden:",
    min_value=10, max_value=200,
    value=saved_config.get("max_characters_per_refresh", 120),
    step=5
)
max_words_per_message = st.number_input(
    "Maximale Wörter pro Nachricht:",
    min_value=10, max_value=200,
    value=saved_config.get("max_words_per_message", 30),
    step=5
)

if st.button("💾 Einstellungen speichern"):
    config = {
        "max_characters_per_refresh": int(max_characters_per_refresh),
        "max_words_per_message": int(max_words_per_message),
    }
    with open(config_path, "w") as f:
        json.dump(config, f)
    st.success("Einstellungen gespeichert.")

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    names = df.iloc[:, 0].dropna().tolist()

    # Vorhandene Students sicher löschen
    students = supabase.table('students').select('id').execute()
    if students.data:
        for student in students.data:
            supabase.table('students').delete().eq('id', student['id']).execute()

    # Neue Students einfügen
    for name in names:
        supabase.table('students').insert({'name': name}).execute()

    st.success(f"{len(names)} Schüler:innen gespeichert.")

# Paarungen erstellen
if st.button("🔁 Paarungen erstellen"):
    data = supabase.table('students').select('*').execute()
    students = [item['name'] for item in data.data]

    if len(students) < 2:
        st.error("Nicht genug Schüler:innen vorhanden.")
    else:
        random.shuffle(students)
        topics = {
            "de": ["Umweltschutz", "Technologie", "Schule der Zukunft", "Soziale Medien", "Reisen", "Künstliche Intelligenz", "Freundschaft", "Sport"] * 3,
            "en": ["Environmental Protection", "Technology", "School of the Future", "Social Media", "Traveling", "Artificial Intelligence", "Friendship", "Sports"] * 3,
            "fr": ["Protection de l'environnement", "Technologie", "École du futur", "Médias sociaux", "Voyager", "Intelligence artificielle", "Amitié", "Sports"] * 3,
            "es": ["Protección del medio ambiente", "Tecnología", "Escuela del futuro", "Redes sociales", "Viajar", "Inteligencia artificial", "Amistad", "Deportes"] * 3,
        }

        pairs = []
        for i in range(0, len(students), 2):
            if i+1 < len(students):
                topic = shared_topic if use_shared_topic and shared_topic else topics[language][i // 2]
                pair = {
                    'student1': students[i],
                    'student2': students[i+1],
                    'topic': topic,
                    'language': language
                }
                pairs.append(pair)

        # Vorhandene Paare sicher löschen (nur für ausgewählte Sprache)
        pairs_existing = supabase.table('pairs').select('id', 'language').execute()
        if pairs_existing.data:
            for pair in pairs_existing.data:
                if pair['language'] == language:
                    supabase.table('pairs').delete().eq('id', pair['id']).execute()

        # Neue Paare speichern
        for pair in pairs:
            supabase.table('pairs').insert(pair).execute()

        st.success(f"Paarungen für {language} gespeichert!")

# Button um alle Paarungen zu löschen
if st.button("🗑️ Alle Paarungen löschen"):
    pairs_existing = supabase.table('pairs').select('id').execute()
    if pairs_existing.data:
        for pair in pairs_existing.data:
            supabase.table('pairs').delete().eq('id', pair['id']).execute()
        st.success("Alle Paarungen wurden gelöscht.")
    else:
        st.info("Keine Paarungen zum Löschen gefunden.")

# Aktuelle Paare anzeigen
st.subheader("👥 Aktuelle Paarungen")
data = supabase.table('pairs').select('*').execute()
pairs = data.data

if pairs:
    for pair in pairs:
        st.write(f"**{pair['student1']} & {pair['student2']}** → ({pair['language']}) Thema: *{pair['topic']}*")
else:
    st.info("Noch keine Paarungen gespeichert.")
