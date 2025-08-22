import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, time, timedelta
from io import BytesIO

# =========================
# ---- App Configuration ---
# =========================
st.set_page_config(
    page_title="Departures Manager",
    page_icon="🚉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------
# Constants & Data Schema
# -------------------------
DATA_FILE = "departures.csv"

# Canonical columns in English
COLS = ["Unit Number", "Gate", "Departure Time", "Transport Type", "Destination", "Comment", "Created At"]

# Destination list (normalized)
DESTINATIONS = ["", "Førde", "Molde", "Haugesund", "Ålesund", "Trondheim", "Stavanger"]

# Language packs (default EN). You said UI in English, but adding NO switch as extra feature.
LANG = st.sidebar.selectbox("Language", ["English", "Norsk"], index=0)

TXT = {
    "English": {
        "title": "🚉 Departures Registration System",
        "register": "➕ Register Departure",
        "unit": "Unit Number",
        "gate": "Gate",
        "time": "Departure Time",
        "transport": "Transport Type",
        "train": "Train",
        "car": "Car",
        "destination": "Destination",
        "comment": "Comment",
        "saved": "✅ Departure added!",
        "updated": "✅ Departure updated!",
        "list": "📋 Registered Departures",
        "none": "No departures yet.",
        "edit": "✏️ Edit",
        "delete": "🗑️ Delete",
        "confirm_title": "Are you sure you want to delete this departure?",
        "yes": "✅ Yes, delete",
        "no": "❌ Cancel",
        "filter": "Filter by destination",
        "sort": "Sort by",
        "sort_time": "Departure time (upcoming first)",
        "sort_dest": "Destination (A–Z)",
        "validation": "⚠️ Please fill in all required fields.",
        "export_csv": "⬇️ Export CSV",
        "export_xlsx": "⬇️ Export Excel",
        "export_pdf": "⬇️ Export PDF",
        "count_title": "Summary",
        "total": "Total",
        "train_count": "Train",
        "car_count": "Car",
        "edit_title": "✏️ Edit Departure",
        "save_changes": "💾 Save Changes",
        "appearance": "Appearance",
        "dark_mode": "Dark mode",
        "toast_deleted": "🗑️ Departure deleted.",
    },
    "Norsk": {
        "title": "🚉 Avgangsregistreringssystem",
        "register": "➕ Registrer avgang",
        "unit": "Enhetnummer",
        "gate": "Luke",
        "time": "Avgangstid",
        "transport": "Transporttype",
        "train": "Tog",
        "car": "Bil",
        "destination": "Destinasjon",
        "comment": "Kommentar",
        "saved": "✅ Avgang registrert!",
        "updated": "✅ Avgang oppdatert!",
        "list": "📋 Registrerte avganger",
        "none": "Ingen avganger ennå.",
        "edit": "✏️ Rediger",
        "delete": "🗑️ Slett",
        "confirm_title": "Er du sikker på at du vil slette denne avgangen?",
        "yes": "✅ Ja, slett",
        "no": "❌ Avbryt",
        "filter": "Filtrer etter destinasjon",
        "sort": "Sorter etter",
        "sort_time": "Avgangstid (naredne prvo)",
        "sort_dest": "Destinasjon (A–Å)",
        "validation": "⚠️ Vennligst fyll ut alle påkrevde felt.",
        "export_csv": "⬇️ Eksporter CSV",
        "export_xlsx": "⬇️ Eksporter Excel",
        "export_pdf": "⬇️ Eksporter PDF",
        "count_title": "Oppsummering",
        "total": "Totalt",
        "train_count": "Tog",
        "car_count": "Bil",
        "edit_title": "✏️ Rediger avgang",
        "save_changes": "💾 Lagre endringer",
        "appearance": "Utseende",
        "dark_mode": "Mørk modus",
        "toast_deleted": "🗑️ Avgang slettet.",
    },
}[LANG]

# =========================
# ---- Styles (CSS) -------
# =========================
def inject_css(dark: bool):
    base_bg = "#111315" if dark else "#fafafa"
    base_fg = "#eaeaea" if dark else "#222222"
    card_bg = "#1a1d1f" if dark else "#ffffff"
    border = "#2a2f33" if dark else "#e8e8e8"

    st.markdown(
        f"""
        <style>
            html, body, .block-container {{
                background-color: {base_bg} !important;
                color: {base_fg} !important;
            }}
            .app-card {{
                background: {card_bg};
                border: 1px solid {border};
                padding: 1rem;
                border-radius: 12px;
                box-shadow: none;
                margin-bottom: 0.5rem;
            }}
            .transport-pill {{
                display:inline-block; padding: 2px 8px; border-radius: 999px; font-weight:600;
            }}
            .pill-train {{ background:#ffe5e5; color:#6a0000; }}
            .pill-car   {{ background:#e7ffe7; color:#064b00; }}

            /* Toggle buttons look */
            .toggle-row button {{
                border-radius: 8px !important;
                padding: 0.5rem 0.9rem !important;
                font-weight: 700 !important;
                border: 1px solid {border} !important;
            }}
            .btn-train-active {{
                background:#ffd6d6 !important; color:#5c0000 !important;
            }}
            .btn-car-active {{
                background:#d9ffd9 !important; color:#024b00 !important;
            }}
            .btn-inactive {{
                background:{card_bg} !important; color:{base_fg} !important;
            }}

            /* Buttons general */
            .stButton>button {{
                border-radius: 10px;
            }}

            /* Inputs */
            .stTextInput>div>div>input, .stTextArea textarea {{
                border-radius: 10px;
            }}

            /* Small muted text */
            .muted {{
                opacity: 0.7; font-size: 0.9rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# =========================
# ---- Util Functions -----
# =========================
def migrate_or_create(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        df = pd.DataFrame(columns=COLS)
        df.to_csv(csv_path, index=False)
        return df
    df = pd.read_csv(csv_path)

    # Try to migrate old Norwegian columns to English
    map_no_to_en = {
        "Enhetnummer": "Unit Number",
        "Luke": "Gate",
        "Avgangstid": "Departure Time",
        "Transporttype": "Transport Type",
        "Destinasjon": "Destination",
        "Kommentar": "Comment",
    }
    # Normalize columns
    rename = {}
    for c in df.columns:
        if c in map_no_to_en:
            rename[c] = map_no_to_en[c]
    if rename:
        df = df.rename(columns=rename)

    # Ensure all required columns exist
    for c in COLS:
        if c not in df.columns:
            df[c] = "" if c != "Created At" else pd.NaT

    # Clean destination whitespace
    df["Destination"] = df["Destination"].astype(str).str.strip()

    # Ensure types
    df["Departure Time"] = df["Departure Time"].astype(str).str.strip()
    return df[COLS]

def save_data(df: pd.DataFrame):
    df.to_csv(DATA_FILE, index=False)

def upcoming_sort_key(t: str) -> datetime:
    """Sort times by next occurrence (today or tomorrow if already passed)."""
    try:
        h, m = [int(x) for x in t.split(":")]
        dt_today = datetime.combine(date.today(), time(h, m))
        if dt_today < datetime.now():
            dt_today += timedelta(days=1)
        return dt_today
    except Exception:
        return datetime.max

def export_excel(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    # Keep column order & types
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Departures")
        ws = writer.sheets["Departures"]
        ws.set_column(0, len(df.columns)-1, 20)
    return output.getvalue()

def export_pdf(df: pd.DataFrame) -> bytes | None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        x_margin, y_margin = 2*cm, 2*cm
        y = height - y_margin

        c.setFont("Helvetica-Bold", 14)
        c.drawString(x_margin, y, "Departures")
        y -= 1.0*cm
        c.setFont("Helvetica", 10)

        headers = COLS
        line_height = 0.6*cm
        for idx, row in df.iterrows():
            line = " | ".join(str(row.get(h, "")) for h in headers)
            if y < y_margin + line_height:
                c.showPage()
                y = height - y_margin
                c.setFont("Helvetica", 10)
            c.drawString(x_margin, y, line[:180])  # truncate for safety
            y -= line_height

        c.showPage()
        c.save()
        pdf = buffer.getvalue()
        buffer.close()
        return pdf
    except Exception:
        return None

# =========================
# ---- Load & Theme --------
# =========================
if "transport_type" not in st.session_state:
    st.session_state.transport_type = None
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = None

dark_mode = st.sidebar.toggle(f"{TXT['dark_mode']}", value=False, help="Optional dark theme")
inject_css(dark_mode)

# =========================
# ---- Title & Summary -----
# =========================
st.title(TXT["title"])

data = migrate_or_create(DATA_FILE)

# Summary counters
total = len(data)
train_cnt = (data["Transport Type"] == "Train").sum()
car_cnt = (data["Transport Type"] == "Car").sum()

with st.sidebar:
    st.subheader(TXT["count_title"])
    c1, c2, c3 = st.columns(3)
    c1.metric(TXT["total"], total)
    c2.metric(TXT["train_count"], int(train_cnt))
    c3.metric(TXT["car_count"], int(car_cnt))

# =========================
# ---- Registration Form ---
# =========================
st.markdown('<div class="app-card">', unsafe_allow_html=True)
st.subheader(TXT["register"])

form_cols = st.columns([1, 1, 1, 1])
with st.form("register_form", clear_on_submit=True):
    unit_number = form_cols[0].text_input(f"{TXT['unit']} *")
    gate = form_cols[1].text_input(f"{TXT['gate']} *")
    departure_time = form_cols[2].time_input(f"{TXT['time']} *", value=None)
    destination = form_cols[3].selectbox(f"{TXT['destination']} *", DESTINATIONS, index=0)

    st.markdown('<div class="toggle-row">', unsafe_allow_html=True)
    tc1, tc2, _sp = st.columns([1,1,3])
    # Transport toggle as stylish buttons
    train_active = (st.session_state.transport_type == "Train")
    car_active = (st.session_state.transport_type == "Car")

    if tc1.button(f"🚆 {TXT['train']}", use_container_width=True,
                  key="btn_train",
                  help=TXT["transport"],
                  ):
        st.session_state.transport_type = "Train"
        train_active, car_active = True, False

    if tc2.button(f"🚗 {TXT['car']}", use_container_width=True,
                  key="btn_car",
                  help=TXT["transport"],
                  ):
        st.session_state.transport_type = "Car"
        train_active, car_active = False, True

    # Apply visual state to the two buttons via JS-less CSS hint (class names on container not directly supported per-button in Streamlit)
    # We'll show current state as text pill:
    if st.session_state.transport_type:
        sel = st.session_state.transport_type
        pill_class = "pill-train" if sel == "Train" else "pill-car"
        st.markdown(f'<span class="transport-pill {pill_class}">{sel}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    comment = st.text_area(TXT["comment"], placeholder="Optional notes...")

    submitted = st.form_submit_button(TXT["register"])

    if submitted:
        # Validation
        if not unit_number.strip() or not gate.strip() or not departure_time or not destination or not st.session_state.transport_type:
            st.warning(TXT["validation"])
        else:
            new_row = pd.DataFrame([{
                "Unit Number": unit_number.strip(),
                "Gate": gate.strip(),
                "Departure Time": departure_time.strftime("%H:%M"),
                "Transport Type": st.session_state.transport_type,
                "Destination": str(destination).strip(),
                "Comment": comment.strip(),
                "Created At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }])
            data = pd.concat([data, new_row], ignore_index=True)
            save_data(data)
            st.success(TXT["saved"])
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ---- Filter & Sort -------
# =========================
st.markdown('<div class="app-card">', unsafe_allow_html=True)
fc1, fc2 = st.columns([2, 1])
search = fc1.text_input(TXT["filter"], placeholder="e.g., Stavanger")
sort_choice = fc2.selectbox(TXT["sort"], [TXT["sort_time"], TXT["sort_dest"]])

filtered = data.copy()
if search:
    filtered = filtered[filtered["Destination"].astype(str).str.contains(search.strip(), case=False, na=False)]

if sort_choice == TXT["sort_dest"]:
    filtered = filtered.sort_values(by=["Destination", "Departure Time"], kind="mergesort", na_position="last")
else:
    # Upcoming time first
    filtered = filtered.assign(_sortkey=filtered["Departure Time"].apply(upcoming_sort_key)) \
                       .sort_values(by=["_sortkey", "Destination"], kind="mergesort") \
                       .drop(columns=["_sortkey"])
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ---- Departures List -----
# =========================
st.subheader(TXT["list"])
if filtered.empty:
    st.info(TXT["none"])
else:
    for i, row in filtered.reset_index().iterrows():
        real_index = row["index"]  # keep original index in data
        wrap = st.container()
        with wrap:
            c = st.columns([1.3, 1, 1, 1.2, 1.3, 2, 0.6, 0.6])
            c[0].markdown(f"**{TXT['unit']}:** {row['Unit Number']}")
            c[1].markdown(f"**{TXT['gate']}:** {row['Gate']}")
            c[2].markdown(f"**{TXT['time']}:** {row['Departure Time']}")
            pill_class = "pill-train" if row["Transport Type"] == "Train" else "pill-car"
            c[3].markdown(f"**{TXT['transport']}:** <span class='transport-pill {pill_class}'>{row['Transport Type']}</span>", unsafe_allow_html=True)
            c[4].markdown(f"**{TXT['destination']}:** {row['Destination']}")
            c[5].markdown(f"**{TXT['comment']}:** {row['Comment'] if str(row['Comment']).strip() else '<span class=\"muted\">—</span>'}", unsafe_allow_html=True)

            edit_pressed = c[6].button(TXT["edit"], key=f"edit_{real_index}", use_container_width=True)
            del_pressed = c[7].button(TXT["delete"], key=f"del_{real_index}", use_container_width=True)

            st.markdown('<hr style="margin:0.4rem 0; opacity:0.2;">', unsafe_allow_html=True)

            if edit_pressed:
                st.session_state.edit_index = real_index

            if del_pressed:
                st.session_state.confirm_delete = real_index

        # Delete confirmation
        if st.session_state.confirm_delete == real_index:
            with st.warning(TXT["confirm_title"]):
                dc1, dc2 = st.columns(2)
                if dc1.button(TXT["yes"], key=f"yes_{real_index}"):
                    data = data.drop(real_index).reset_index(drop=True)
                    save_data(data)
                    st.session_state.confirm_delete = None
                    st.success(TXT["toast_deleted"])
                    st.experimental_rerun()
                if dc2.button(TXT["no"], key=f"no_{real_index}"):
                    st.session_state.confirm_delete = None
                    st.experimental_rerun()

# =========================
# ---- Edit Form -----------
# =========================
if st.session_state.edit_index is not None and st.session_state.edit_index < len(data):
    idx = st.session_state.edit_index
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.subheader(TXT["edit_title"])
    with st.form("edit_form"):
        e1, e2, e3, e4 = st.columns([1,1,1,1])
        unit_number = e1.text_input(f"{TXT['unit']} *", value=str(data.loc[idx, "Unit Number"]))
        gate = e2.text_input(f"{TXT['gate']} *", value=str(data.loc[idx, "Gate"]))
        # parse stored time
        try:
            hh, mm = str(data.loc[idx, "Departure Time"]).split(":")
            default_time = time(int(hh), int(mm))
        except Exception:
            default_time = None
        departure_time = e3.time_input(f"{TXT['time']} *", value=default_time)
        destination = e4.selectbox(f"{TXT['destination']} *", DESTINATIONS,
                                   index=max(0, DESTINATIONS.index(str(data.loc[idx, "Destination"])) if str(data.loc[idx, "Destination"]) in DESTINATIONS else 0))

        # transport toggle in edit
        et1, et2, _sp = st.columns([1,1,3])
        curr_t = data.loc[idx, "Transport Type"]
        if "edit_transport" not in st.session_state:
            st.session_state.edit_transport = curr_t

        if et1.button(f"🚆 {TXT['train']}", key="edit_train", use_container_width=True):
            st.session_state.edit_transport = "Train"
        if et2.button(f"🚗 {TXT['car']}", key="edit_car", use_container_width=True):
            st.session_state.edit_transport = "Car"

        sel_pill_class = "pill-train" if st.session_state.edit_transport == "Train" else "pill-car"
        st.markdown(f"**{TXT['transport']}:** <span class='transport-pill {sel_pill_class}'>{st.session_state.edit_transport}</span>", unsafe_allow_html=True)

        comment = st.text_area(TXT["comment"], value=str(data.loc[idx, "Comment"]))

        save_changes = st.form_submit_button(TXT["save_changes"])

        if save_changes:
            # validation
            if not unit_number.strip() or not gate.strip() or not departure_time or not destination or not st.session_state.edit_transport:
                st.warning(TXT["validation"])
            else:
                data.loc[idx] = [
                    unit_number.strip(),
                    gate.strip(),
                    departure_time.strftime("%H:%M"),
                    st.session_state.edit_transport,
                    str(destination).strip(),
                    comment.strip(),
                    data.loc[idx, "Created At"] if pd.notna(data.loc[idx, "Created At"]) else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ]
                save_data(data)
                st.success(TXT["updated"])
                st.session_state.edit_index = None
                st.session_state.edit_transport = None
                st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ---- Export Buttons ------
# =========================
st.markdown('<div class="app-card">', unsafe_allow_html=True)
ec1, ec2, ec3 = st.columns([1,1,1])
ec1.download_button(TXT["export_csv"], data.to_csv(index=False).encode("utf-8"), file_name="departures.csv", mime="text/csv")
xlsx_bytes = export_excel(data)
ec2.download_button(TXT["export_xlsx"], xlsx_bytes, file_name="departures.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
pdf_bytes = export_pdf(data)
if pdf_bytes:
    ec3.download_button(TXT["export_pdf"], pdf_bytes, file_name="departures.pdf", mime="application/pdf")
else:
    ec3.write('<span class="muted">Install <code>reportlab</code> for PDF export: <code>pip install reportlab</code></span>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ---- Notes ---------------
# =========================
st.caption("Data is persisted to a local CSV file for simplicity. For multi-user/cloud setups, swap CSV for a backend (e.g., Firebase or a small Node/Flask API).")
