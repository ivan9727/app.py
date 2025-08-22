import streamlit as st
import pandas as pd
import os
import uuid
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
LOCK_FILE = DATA_FILE + ".lock"

# Pokušaj file-lock; ako nema paketa, koristi dummy lock
try:
    from filelock import FileLock
    def get_lock():
        return FileLock(LOCK_FILE)
except Exception:
    from contextlib import contextmanager
    @contextmanager
    def get_lock():
        yield

# Canonical columns in English (ID je prvi)
COLS = ["ID", "Unit Number", "Gate", "Departure Time", "Transport Type", "Destination", "Comment", "Created At"]

# Destination list (normalized)
DESTINATIONS = ["", "Førde", "Molde", "Haugesund", "Ålesund", "Trondheim", "Stavanger"]

# Language packs (EN + NO)
LANG = st.sidebar.selectbox("Language / Språk", ["English", "Norsk"], index=0)

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
        "duplicate": "⚠️ A departure with the same Unit, Time and Destination already exists.",
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
        "install_reportlab": 'Install <code>reportlab</code> for PDF export: <code>pip install reportlab</code>',
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
        "sort_time": "Avgangstid (kommende først)",
        "sort_dest": "Destinasjon (A–Å)",
        "validation": "⚠️ Vennligst fyll ut alle påkrevde felt.",
        "duplicate": "⚠️ Det finnes allerede en avgang med samme enhet, tid og destinasjon.",
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
        "install_reportlab": 'Installer <code>reportlab</code> for PDF-eksport: <code>pip install reportlab</code>',
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
            body, .block-container {{
                background-color: {base_bg} !important;
                color: {base_fg} !important;
            }}

            label, .stTextInput label, .stSelectbox label, .stTimeInput label, .stTextArea label {{
                color: {base_fg} !important;
                font-weight: 600 !important;
            }}

            .app-card {{
                background: {card_bg};
                border: 1px solid {border};
                padding: 1rem;
                border-radius: 12px;
                margin-bottom: 0.5rem;
            }}

            .transport-pill {{
                display:inline-block; padding: 2px 8px; border-radius: 999px; font-weight:600;
            }}
            .pill-train {{ background:#ffe5e5; color:#6a0000; }}
            .pill-car   {{ background:#e7ffe7; color:#064b00; }}

            .toggle-row button {{
                border-radius: 8px !important;
                padding: 0.5rem 0.9rem !important;
                font-weight: 700 !important;
                border: 1px solid {border} !important;
            }}

            .muted {{ opacity: 0.6; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# =========================
# ---- Util Functions -----
# =========================
def migrate_or_create(csv_path: str) -> pd.DataFrame:
    with get_lock():
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
    rename = {}
    for c in df.columns:
        if c in map_no_to_en:
            rename[c] = map_no_to_en[c]
    if rename:
        df = df.rename(columns=rename)

    # Ensure all required columns exist
    for c in COLS:
        if c not in df.columns:
            if c == "ID":
                df[c] = [str(uuid.uuid4()) for _ in range(len(df))] if len(df) else []
            elif c == "Created At":
                df[c] = pd.NaT
            else:
                df[c] = ""

    # Ensure ID for any missing/blank
    df["ID"] = df["ID"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else str(uuid.uuid4()))

    # Clean destination whitespace
    df["Destination"] = df["Destination"].astype(str).str.strip()

    # Normalize time col to "HH:MM"
    def _fix_time(t):
        t = str(t).strip()
        if not t or t.lower() == "nan":
            return ""
        try:
            hh, mm = t.split(":")[:2]
            return f"{int(hh):02d}:{int(mm):02d}"
        except Exception:
            return ""
    df["Departure Time"] = df["Departure Time"].astype(str).map(_fix_time)

    # Keep canonical order
    return df[COLS]

def save_data(df: pd.DataFrame):
    with get_lock():
        df.to_csv(DATA_FILE, index=False)

def upcoming_sort_key(t: str) -> datetime:
    """Sort by next occurrence (today or +1 day if already passed)."""
    try:
        h, m = map(int, t.split(":")[:2])
        today = date.today()
        dt = datetime.combine(today, time(h, m))
        if dt < datetime.now():
            dt += timedelta(days=1)
        return dt
    except Exception:
        return datetime.max

def export_excel(df: pd.DataFrame) -> bytes:
    output = BytesIO()
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

        # Title
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x_margin, y, "Departures")
        y -= 1.0*cm

        # Headers
        c.setFont("Helvetica-Bold", 10)
        headers = COLS
        header_line = " | ".join(headers)
        c.drawString(x_margin, y, header_line[:200])
        y -= 0.5*cm
        c.setFont("Helvetica", 9)

        line_height = 0.55*cm
        for _, row in df.iterrows():
            line = " | ".join(str(row.get(h, "")) for h in headers)
            if y < y_margin + line_height:
                c.showPage()
                y = height - y_margin
                c.setFont("Helvetica", 9)
            c.drawString(x_margin, y, line[:240])  # sigurnosno skraćenje
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
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None
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

with st.form("register_form", clear_on_submit=True):
    unit_number = st.text_input(f"{TXT['unit']} *")
    gate = st.text_input(f"{TXT['gate']} *")
    departure_time_val = st.time_input(f"{TXT['time']} *", step=timedelta(minutes=5))
    destination = st.selectbox(f"{TXT['destination']} *", DESTINATIONS)
    comment = st.text_area(TXT["comment"])

    transport_type = st.radio(
        f"{TXT['transport']} *",
        options=["Train", "Car"],
        horizontal=True,
        index=0 if st.session_state.get("transport_type") == "Train" else 1 if st.session_state.get("transport_type") == "Car" else 0
    )
    st.session_state["transport_type"] = transport_type

    submitted = st.form_submit_button(TXT["register"])

if submitted:
    if not unit_number.strip() or not gate.strip() or not departure_time_val or not destination or not st.session_state.get("transport_type"):
        st.warning(TXT["validation"])
    else:
        # Duplicate check (Unit + Time + Destination)
        dep_str = departure_time_val.strftime("%H:%M")
        dup_mask = (data["Unit Number"].astype(str).str.strip() == unit_number.strip()) & \
                   (data["Departure Time"].astype(str).str.strip() == dep_str) & \
                   (data["Destination"].astype(str).str.strip() == destination.strip())
        if dup_mask.any():
            st.warning(TXT["duplicate"])
        else:
            new_row = pd.DataFrame([{
                "ID": str(uuid.uuid4()),
                "Unit Number": unit_number.strip(),
                "Gate": gate.strip(),
                "Departure Time": dep_str,
                "Transport Type": st.session_state["transport_type"],
                "Destination": destination.strip(),
                "Comment": comment.strip(),
                "Created At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }])
            data = pd.concat([data, new_row], ignore_index=True)
            save_data(data)
            st.success(TXT["saved"])

# =========================
# ---- Filter & Sort -------
# =========================
st.markdown('<div class="app-card">', unsafe_allow_html=True)
fc1, fc2 = st.columns([2, 1])

search = fc1.selectbox(
    TXT["filter"],
    options=["All"] + [d for d in DESTINATIONS if d],
    index=0,
)

sort_choice = fc2.selectbox(TXT["sort"], [TXT["sort_time"], TXT["sort_dest"]])

filtered = data.copy()
if search != "All":
    filtered = filtered[filtered["Destination"] == search]

if sort_choice == TXT["sort_dest"]:
    filtered = filtered.sort_values(by=["Destination", "Departure Time"], kind="mergesort", na_position="last")
else:
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
    for _, row in filtered.iterrows():
        real_id = row["ID"]
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

            edit_pressed = c[6].button(TXT["edit"], key=f"edit_{real_id}", use_container_width=True)
            del_pressed = c[7].button(TXT["delete"], key=f"del_{real_id}", use_container_width=True)

            st.markdown('<hr style="margin:0.4rem 0; opacity:0.2;">', unsafe_allow_html=True)

            if edit_pressed:
                st.session_state.edit_id = real_id

            if del_pressed:
                st.session_state.confirm_delete = real_id

        # Delete confirmation
        if st.session_state.confirm_delete == real_id:
            with st.warning(TXT["confirm_title"]):
                dc1, dc2 = st.columns(2)
                if dc1.button(TXT["yes"], key=f"yes_{real_id}"):
                    data = data[data["ID"] != real_id].reset_index(drop=True)
                    save_data(data)
                    st.session_state.confirm_delete = None
                    st.success(TXT["toast_deleted"])
                    st.rerun()
                if dc2.button(TXT["no"], key=f"no_{real_id}"):
                    st.session_state.confirm_delete = None
                    st.rerun()

# =========================
# ---- Edit Form -----------
# =========================
if st.session_state.edit_id is not None and (data["ID"] == st.session_state.edit_id).any():
    idx = data.index[data["ID"] == st.session_state.edit_id][0]
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
        departure_time_val = e3.time_input(f"{TXT['time']} *", value=default_time, step=timedelta(minutes=5))
        destination = e4.selectbox(
            f"{TXT['destination']} *",
            DESTINATIONS,
            index=max(0, DESTINATIONS.index(str(data.loc[idx, "Destination"])) if str(data.loc[idx, "Destination"]) in DESTINATIONS else 0)
        )

        et1, et2, _sp = st.columns([1,1,3])
        curr_t = data.loc[idx, "Transport Type"]
        if "edit_transport" not in st.session_state:
            st.session_state.edit_transport = curr_t

        if et1.button(f"🚆 {TXT['train']}", key=f"edit_train_{idx}", use_container_width=True):
            st.session_state.edit_transport = "Train"
        if et2.button(f"🚗 {TXT['car']}", key=f"edit_car_{idx}", use_container_width=True):
            st.session_state.edit_transport = "Car"

        sel_pill_class = "pill-train" if st.session_state.edit_transport == "Train" else "pill-car"
        st.markdown(f"**{TXT['transport']}:** <span class='transport-pill {sel_pill_class}'>{st.session_state.edit_transport}</span>", unsafe_allow_html=True)

        comment = st.text_area(TXT["comment"], value=str(data.loc[idx, "Comment"]))

        save_changes = st.form_submit_button(TXT["save_changes"])

        if save_changes:
            # validation
            if not unit_number.strip() or not gate.strip() or not departure_time_val or not destination or not st.session_state.edit_transport:
                st.warning(TXT["validation"])
            else:
                # Duplicate check excluding this ID
                dep_str = departure_time_val.strftime("%H:%M")
                dup_mask = (data["ID"] != data.loc[idx, "ID"]) & \
                           (data["Unit Number"].astype(str).str.strip() == unit_number.strip()) & \
                           (data["Departure Time"].astype(str).str.strip() == dep_str) & \
                           (data["Destination"].astype(str).str.strip() == str(destination).strip())
                if dup_mask.any():
                    st.warning(TXT["duplicate"])
                else:
                    data.loc[idx, "Unit Number"] = unit_number.strip()
                    data.loc[idx, "Gate"] = gate.strip()
                    data.loc[idx, "Departure Time"] = dep_str
                    data.loc[idx, "Transport Type"] = st.session_state.edit_transport
                    data.loc[idx, "Destination"] = str(destination).strip()
                    data.loc[idx, "Comment"] = comment.strip()
                    if pd.isna(data.loc[idx, "Created At"]) or str(data.loc[idx, "Created At"]).strip() == "":
                        data.loc[idx, "Created At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    save_data(data)
                    st.success(TXT["updated"])
                    st.session_state.edit_id = None
                    st.session_state.edit_transport = None
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ---- Export Buttons ------
# =========================
st.markdown('<div class="app-card">', unsafe_allow_html=True)
ec1, ec2, ec3 = st.columns([1,1,1])
ec1.download_button(TXT["export_csv"], data.to_csv(index=False).encode("utf-8"), file_name="departures.csv")
xlsx_bytes = export_excel(data)
ec2.download_button(TXT["export_xlsx"], xlsx_bytes, file_name="departures.xlsx")
pdf_bytes = export_pdf(data)
if pdf_bytes:
    ec3.download_button(TXT["export_pdf"], pdf_bytes, file_name="departures.pdf")
else:
    ec3.write(f'<span class="muted">{TXT["install_reportlab"]}</span>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ---- Notes ---------------
# =========================
st.caption("Data is persisted to a local CSV file with a file lock for safety. For multi-user/cloud setups, replace CSV with a backend (e.g., Firebase or small API).")