import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# Inicijalizacija baze podataka
def init_db():
    with sqlite3.connect('avganger.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_number TEXT,
                destination TEXT,
                time TEXT,
                gate TEXT
            )
        ''')
        conn.commit()

# Pokretanje baze podataka
init_db()

# Lista destinacija
DESTINATIONS = [
    "TRONDHEIM",
    "ÅLESUND",
    "MOLDE",
    "FØRDE",
    "HAUGESUND",
    "STAVANGER"
]

# Funkcija za dohvaćanje svih polazaka
def get_departures():
    with sqlite3.connect('avganger.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, unit_number, destination, time, gate FROM departures')
        return cursor.fetchall()

# Funkcija za dodavanje polaska
def add_departure(unit_number, destination, time, gate):
    if unit_number and destination in DESTINATIONS and time and gate:
        with sqlite3.connect('avganger.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO departures (unit_number, destination, time, gate)
                VALUES (?, ?, ?, ?)
            ''', (unit_number, destination, time, gate))
            conn.commit()
        return True
    return False

# Funkcija za brisanje pojedinog polaska
def delete_departure(id):
    with sqlite3.connect('avganger.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM departures WHERE id = ?', (id,))
        conn.commit()

# Funkcija za brisanje svih polazaka
def delete_all_departures():
    with sqlite3.connect('avganger.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM departures')
        conn.commit()

# Streamlit aplikacija
st.title("Registrer Avganger")

# Forma za unos polaska
with st.form(key='departure_form'):
    st.subheader("Unos novog polaska")
    unit_number = st.text_input("Enhetsnummer")
    destination = st.selectbox("Destinasjon", [""] + DESTINATIONS)
    time = st.time_input("Tid")
    gate = st.text_input("Luke")
    submit_button = st.form_submit_button("Registrer Avgang")

    if submit_button:
        if unit_number and destination and time and gate:
            time_str = time.strftime("%H:%M")
            if add_departure(unit_number, destination, time_str, gate):
                st.success("Polazak uspješno registriran!")
            else:
                st.error("Greška pri unosu. Provjerite podatke.")
        else:
            st.error("Sva polja su obavezna!")

# Prikaz tablice polazaka
st.subheader("Popis polazaka")
departures = get_departures()
if departures:
    # Pretvorba u DataFrame za ljepši prikaz
    df = pd.DataFrame(departures, columns=['ID', 'Enhetsnummer', 'Destinasjon', 'Tid', 'Luke'])
    # Prikaz tablice bez stupca ID
    st.dataframe(df[['Enhetsnummer', 'Destinasjon', 'Tid', 'Luke']], use_container_width=True)

    # Brisanje pojedinog polaska
    st.subheader("Upravljanje polascima")
    delete_id = st.selectbox("Odaberite polazak za brisanje (po ID-u)", [dep[0] for dep in departures])
    if st.button("Slett"):
        delete_departure(delete_id)
        st.success("Polazak obrisan!")
        st.rerun()  # Osvježavanje stranice

    # Brisanje svih polazaka
    if st.button("Tøm alle avganger"):
        delete_all_departures()
        st.success("Svi polasci obrisani!")
        st.rerun()  # Osvježavanje stranice
else:
    st.info("Nema registriranih polazaka.")

# Gumb za ispis (otvara ispisni dijalog preglednika)
st.markdown("""
    <button onclick="window.print()" style="background-color: #28a745; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
        Skriv ut
    </button>
""", unsafe_allow_html=True)