import streamlit as st
import pandas as pd
import os
import json
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

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    names = df.iloc[:, 0].dropna().tolist()

    # Vorhandene Students löschen
    supabase.table('students').delete().neq('id', 'null').execute()

    # Neue Students einfügen
    for name in names:
        supabase.table('students').insert({'name': name}).execute()

    st.success(f"{len(names)} Schüler:innen gespeichert.")

# Paarungen erstellen
if st.button("🔁 Paarungen zufällig erstellen"):
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
                pair = {
                    'student1': students[i],
                    'student2': students[i+1],
                    'topic': topics[i // 2]
                }
                pairs.append(pair)

        supabase.table('pairs').delete().neq('id', 'null').execute()

        for pair in pairs:
            supabase.table('pairs').insert(pair).execute()

        st.success("Paarungen gespeichert!")

# Aktuelle Paare anzeigen
st.subheader("👥 Aktuelle Paarungen")
data = supabase.table('pairs').select('*').execute()
pairs = data.data

if pairs:
    for pair in pairs:
        st.write(f"**{pair['student1']} & {pair['student2']}** → Thema: *{pair['topic']}*")
else:
    st.info("Noch keine Paarungen gespeichert.")
