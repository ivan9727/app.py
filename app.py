import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
from streamlit_autorefresh import st_autorefresh
from io import BytesIO
from xlsxwriter import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Inicijalizacija baze podataka
DB_FILE = 'data.db'

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_date TEXT,
                unit_number TEXT,
                gate INTEGER,
                departure_time TEXT,
                transport_type TEXT,
                destination TEXT,
                comment TEXT,
                created_at TEXT
            )
        ''')
        conn.commit()

init_db()

# Funkcije za rad s bazom (keširane s TTL=2s)
@st.cache_data(ttl=2)
def get_departures(service_date):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM departures WHERE service_date = ?",
            conn,
            params=(service_date,)
        )
    return df

def add_or_update_departure(id=None, service_date=None, unit_number=None, gate=None, departure_time=None, 
                            transport_type=None, destination=None, comment=None):
    unit_number = unit_number.upper() if unit_number else None
    created_at = datetime.now().isoformat()
    
    # Provjera jedinstvenosti (isključujući trenutni ID ako je update)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        if id:
            cursor.execute('''
                SELECT COUNT(*) FROM departures 
                WHERE service_date = ? AND unit_number = ? AND departure_time = ? AND destination = ? AND id != ?
            ''', (service_date, unit_number, departure_time, destination, id))
        else:
            cursor.execute('''
                SELECT COUNT(*) FROM departures 
                WHERE service_date = ? AND unit_number = ? AND departure_time = ? AND destination = ?
            ''', (service_date, unit_number, departure_time, destination))
        if cursor.fetchone()[0] > 0:
            return False, "Duplicate entry for Unit, Time, and Destination on this date."
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        if id:
            cursor.execute('''
                UPDATE departures SET service_date=?, unit_number=?, gate=?, departure_time=?, 
                transport_type=?, destination=?, comment=?, created_at=?
                WHERE id=?
            ''', (service_date, unit_number, gate, departure_time, transport_type, destination, comment, created_at, id))
        else:
            cursor.execute('''
                INSERT INTO departures (service_date, unit_number, gate, departure_time, transport_type, 
                destination, comment, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (service_date, unit_number, gate, departure_time, transport_type, destination, comment, created_at))
        conn.commit()
    st.cache_data.clear()  # Invalidacija cachea
    return True, "Success"

def delete_departure(id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM departures WHERE id = ?', (id,))
        conn.commit()
    st.cache_data.clear()  # Invalidacija cachea

# Destinacije (iz originala, na engleskom)
DESTINATIONS = ["TRONDHEIM", "ÅLESUND", "MOLDE", "FØRDE", "HAUGESUND", "STAVANGER"]

# Custom CSS za lijep dizajn (dark tema, zaobljeni elementi, sjene, boje)
st.markdown("""
    <style>
    /* Osnovni stilovi */
    .stApp { background-color: #0e1117; color: #fafafa; }
    .stButton>button { border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    input, select, .stTextInput>div>div>input { border-radius: 8px; background-color: #1f2937; color: #fafafa; border: 1px solid #4b5563; }
    .stTimeInput>div>div>input { border-radius: 8px; background-color: #1f2937; color: #fafafa; border: 1px solid #4b5563; }
    .stSelectbox>div>div>select { border-radius: 8px; background-color: #1f2937; color: #fafafa; border: 1px solid #4b5563; }
    
    /* Plavi Add gumb */
    button[kind="primary"] { background-color: #3b82f6; color: white; }
    
    /* Chipovi i tileovi */
    .tile { background-color: #1f2937; border-radius: 8px; padding: 10px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chip { display: inline-block; padding: 4px 8px; border-radius: 16px; margin-right: 5px; font-size: 12px; }
    .train-chip { background-color: #ef4444; color: white; }
    .car-chip { background-color: #22c55e; color: white; }
    
    /* Popover (expander) */
    .stExpander { border: none; }
    .stExpander>summary { background-color: #1f2937; border-radius: 8px; padding: 8px; }
    
    /* Comment kompaktan */
    .comment { font-size: 12px; color: #9ca3af; margin-top: 5px; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #111827; }
    </style>
""", unsafe_allow_html=True)

# Auto-refresh svakih 3 sekunde
st_autorefresh(interval=3000, key="data_refresh")

# Sidebar: Date picker, quick buttons, summary
with st.sidebar:
    st.title("Service Date")
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    
    col1, col2 = st.columns(2)
    if col1.button("Today"):
        st.session_state.selected_date = today.strftime("%Y-%m-%d")
    if col2.button("Yesterday"):
        st.session_state.selected_date = yesterday.strftime("%Y-%m-%d")
    
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = today.strftime("%Y-%m-%d")
    
    selected_date = st.date_input("Select Date", value=datetime.strptime(st.session_state.selected_date, "%Y-%m-%d"))
    service_date = selected_date.strftime("%Y-%m-%d")
    st.session_state.selected_date = service_date
    
    # Summary
    df = get_departures(service_date)
    if not df.empty:
        total = len(df)
        train_count = len(df[df['transport_type'] == 'Train'])
        car_count = len(df[df['transport_type'] == 'Car'])
        st.subheader("Summary")
        st.write(f"Total: {total}")
        st.write(f"Train: {train_count}")
        st.write(f"Car: {car_count}")
    else:
        st.subheader("Summary")
        st.write("No data for this date.")

# Glavni sadržaj
st.title("Departure Manager")

# Forma za dodavanje (plavi Add gumb, validacija, auto-clear)
with st.form(key='add_form'):
    st.subheader("Add Departure")
    unit = st.text_input("Unit")
    gate_str = st.text_input("Gate (numbers only)")
    
    # Live validacija za Gate
    gate_valid = gate_str.isdigit() if gate_str else True
    if not gate_valid and gate_str:
        st.error("Gate must contain only numbers.")
    gate = int(gate_str) if gate_valid and gate_str else None
    
    time = st.time_input("Time")
    departure_time = time.strftime("%H:%M") if time else None
    transport = st.selectbox("Transport", ["Train", "Car"])
    destination = st.selectbox("Destination", DESTINATIONS)
    comment = st.text_area("Comment", height=50)  # Kompaktan po visini
    
    submit = st.form_submit_button("Add", type="primary")
    
    if submit:
        if not (unit and gate_valid and gate_str and departure_time and transport and destination):
            st.error("All fields are required. Gate must be a number.")
        else:
            success, message = add_or_update_departure(None, service_date, unit, gate, departure_time, transport, destination, comment)
            if success:
                st.success("Departure added successfully!")
                st.form_submit_button("Clear Form")  # Auto-clear simuliran refreshom, ali Streamlit reruns
                st.rerun()  # Force rerun za clear forme
            else:
                st.error(message)

# Filteri i sortiranje u popoveru (expander)
with st.expander("Filters & Sorting"):
    if "filter_destination" not in st.session_state:
        st.session_state.filter_destination = "All"
    if "sort_by" not in st.session_state:
        st.session_state.sort_by = "Time"
    if "search_unit" not in st.session_state:
        st.session_state.search_unit = ""
    
    st.session_state.filter_destination = st.selectbox("Destination Filter", ["All"] + DESTINATIONS, index=["All"] + DESTINATIONS.index(st.session_state.filter_destination))
    st.session_state.sort_by = st.selectbox("Sort By", ["Time", "Destination"], index=["Time", "Destination"].index(st.session_state.sort_by))
    st.session_state.search_unit = st.text_input("Quick Search by Unit", value=st.session_state.search_unit)
    
    if st.button("Clear Filters"):
        st.session_state.filter_destination = "All"
        st.session_state.sort_by = "Time"
        st.session_state.search_unit = ""
        st.rerun()

# Filtriranje i sortiranje dataframea
df = get_departures(service_date)
if not df.empty:
    if st.session_state.filter_destination != "All":
        df = df[df['destination'] == st.session_state.filter_destination]
    if st.session_state.search_unit:
        df = df[df['unit_number'].str.contains(st.session_state.search_unit.upper(), case=False)]
    if st.session_state.sort_by == "Time":
        df = df.sort_values('departure_time')
    elif st.session_state.sort_by == "Destination":
        df = df.sort_values('destination')

# Prikaz liste kao tileova
st.subheader("Departures List")
if df.empty:
    st.info("No departures for this date.")
else:
    for idx, row in df.iterrows():
        with st.container():
            # Tile s chip redom
            st.markdown(f"""
                <div class="tile">
                    <span class="chip">Unit: {row['unit_number']}</span>
                    <span class="chip">Gate: {row['gate']}</span>
                    <span class="chip">Time: {row['departure_time']}</span>
                    <span class="chip {'train-chip' if row['transport_type'] == 'Train' else 'car-chip'}">{row['transport_type']}</span>
                    <span class="chip">Destination: {row['destination']}</span>
                    <div class="comment">Comment: {row['comment'] if row['comment'] else '-'}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # 3 točkice popover za