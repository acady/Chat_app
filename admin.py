import streamlit as st
import pandas as pd
import os
import random
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🎓 Lehrer:innen-Panel")

# Datei-Upload
st.subheader("📥 Schüler:innenliste hochladen")
uploaded_file = st.file_uploader("Excel-Datei hochladen (.xlsx)", type="xlsx")

# Thema-Einstellung
shared_topic = st.text_input("📚 Thema für alle Paare (optional)")
use_shared_topic = st.checkbox("Allen Paaren das gleiche Thema zuweisen", value=False)

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
        topics = [
                     "Umweltschutz", "Technologie", "Schule der Zukunft", "Soziale Medien",
                     "Reisen", "Künstliche Intelligenz", "Freundschaft", "Sport"
                 ] * 3

        pairs = []
        for i in range(0, len(students), 2):
            if i+1 < len(students):
                topic = shared_topic if use_shared_topic and shared_topic else topics[i // 2]
                pair = {
                    'student1': students[i],
                    'student2': students[i+1],
                    'topic': topic
                }
                pairs.append(pair)

        # Vorhandene Paare sicher löschen
        pairs_existing = supabase.table('pairs').select('id').execute()
        if pairs_existing.data:
            for pair in pairs_existing.data:
                supabase.table('pairs').delete().eq('id', pair['id']).execute()

        # Neue Paare speichern
        for pair in pairs:
            supabase.table('pairs').insert(pair).execute()

        st.success("Paarungen gespeichert!")

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
        st.write(f"**{pair['student1']} & {pair['student2']}** → Thema: *{pair['topic']}*")
else:
    st.info("Noch keine Paarungen gespeichert.")
