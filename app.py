import streamlit as st
import pandas as pd
import os

# CSV datoteka za spremanje podataka
DATA_FILE = "departures.csv"

# Ako datoteka ne postoji, kreiraj ju
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Enhetnummer", "Luke", "Avgangstid", "Transporttype", "Destinasjon"])
    df.to_csv(DATA_FILE, index=False)

# Funkcija za učitavanje podataka
def load_data():
    return pd.read_csv(DATA_FILE)

# Funkcija za spremanje podataka
def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# Naslov
st.title("🚉 Destinasjonsregistreringssystem")

# Učitaj postojeće podatke
data = load_data()

# --- Forma ---
with st.form("register_form", clear_on_submit=True):
    unit_number = st.text_input("Enhetnummer")
    gate = st.text_input("Luke")
    departure_time = st.time_input("Avgangstid")
    transport_type = st.selectbox("Transporttype", ["", "Tog", "Bil"])
    destination = st.selectbox(
        "Destinasjon",
        ["", "Destinasjon 1", "Destinasjon 2", "Destinasjon 3",
         "Destinasjon 4", "Destinasjon 5", "Destinasjon 6"]
    )

    submit = st.form_submit_button("➕ Registrer avgang")

if submit and unit_number.strip() != "" and gate.strip() != "" and transport_type != "" and destination != "":
    new_row = pd.DataFrame([{
        "Enhetnummer": unit_number,
        "Luke": gate,
        "Avgangstid": departure_time.strftime("%H:%M"),
        "Transporttype": transport_type,
        "Destinasjon": destination
    }])
    data = pd.concat([data, new_row], ignore_index=True)
    save_data(data)
    st.success("✅ Avgang registrert!")

# --- Prikaz tablice ---
st.subheader("📋 Registrerte avganger")

if data.empty:
    st.info("Ingen avganger registrert ennå.")
else:
    for i, row in data.iterrows():
        cols = st.columns([2, 2, 2, 2, 2, 1, 1])
        cols[0].write(row["Enhetnummer"])
        cols[1].write(row["Luke"])
        cols[2].write(row["Avgangstid"])
        cols[3].write(row["Transporttype"])
        cols[4].write(row["Destinasjon"])

        # Uredi
        if cols[5].button("✏️", key=f"edit_{i}"):
            st.session_state.edit_index = i

        # Obriši
        if cols[6].button("🗑️", key=f"delete_{i}"):
            data = data.drop(i).reset_index(drop=True)
            save_data(data)
            st.experimental_rerun()

# --- Uredi zapis ---
if "edit_index" in st.session_state:
    idx = st.session_state.edit_index
    st.subheader("✏️ Rediger avgang")

    with st.form("edit_form"):
        unit_number = st.text_input("Enhetnummer", value=data.loc[idx, "Enhetnummer"])
        gate = st.text_input("Luke", value=data.loc[idx, "Luke"])
        departure_time = st.time_input("Avgangstid")
        transport_type = st.selectbox("Transporttype", ["Tog", "Bil"],
                                      index=["Tog", "Bil"].index(data.loc[idx, "Transporttype"]))
        destination = st.selectbox(
            "Destinasjon",
            ["Destinasjon 1", "Destinasjon 2", "Destinasjon 3",
             "Destinasjon 4", "Destinasjon 5", "Destinasjon 6"],
            index=["Destinasjon 1", "Destinasjon 2", "Destinasjon 3",
                   "Destinasjon 4", "Destinasjon 5", "Destinasjon 6"].index(data.loc[idx, "Destinasjon"])
        )

        save_changes = st.form_submit_button("💾 Spremi")

    if save_changes:
        data.loc[idx] = [unit_number, gate, departure_time.strftime("%H:%M"), transport_type, destination]
        save_data(data)
        del st.session_state["edit_index"]
        st.success("✅ Avgang oppdatert!")
        st.experimental_rerun()
