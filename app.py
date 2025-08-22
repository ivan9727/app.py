import streamlit as st
import pandas as pd
import os
import uuid
from datetime import datetime, date, time, timedelta
from io import BytesIO
import streamlit.components.v1 as components

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

# Canonical columns (ID + Service Date)
COLS = [
    "ID",
    "Service Date",      # YYYY-MM-DD (dan na koji se polazak odnosi)
    "Unit Number",
    "Gate",
    "Departure Time",
    "Transport Type",
    "Destination",
    "Comment",
    "Created At"
]

# Destination list (normalized)
DESTINATIONS = ["", "Førde", "Molde", "Haugesund", "Ålesund", "Trondheim", "Stavanger"]

# Jezik UI-a (ostavljam English/Norsk kao i do sada)
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
        "duplicate": "⚠️ A departure with the same Unit, Time and Destination already exists for the selected day.",
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
        "view_mode": "View mode",
        "view_list": "List",
        "view_table": "Table",
        "actions": "Actions",
        "service_date": "Service date",
        "today": "Today",
        "prev_day": "◀ Yesterday",
        "next_day": "Tomorrow ▶",
        "suggestions": "Suggestions",
        "search_unit": "Quick search by Unit Number",
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
        "duplicate": "⚠️ Det finnes allerede en avgang med samme enhet, tid og destinasjon for valgt dag.",
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
        "view_mode": "Visning",
        "view_list": "Liste",
        "view_table": "Tabell",
        "actions": "Handlinger",
        "service_date": "Dato",
        "today": "I dag",
        "prev_day": "◀ I går",
        "next_day": "I morgen ▶",
        "suggestions": "Forslag",
        "search_unit": "Hurtigsøk etter enhet",
    },
}[LANG]

# Poznate oznake jedinica – početna lista + automatsko učenje iz povijesti
BASE_KNOWN_UNITS = ["PTRU", "BGLU"]

# =========================
# ---- Styles (CSS/JS) ----
# =========================
def inject_css(dark: bool):
    # jači, ali ukusni akcenti
    green = "#16a34a"     # emerald-600
    green_bg = "#eaf7ef"
    red = "#ef4444"       # red-500
    red_bg = "#fdecec"
    blue = "#2563eb"      # blue-600
    blue_soft = "#e8f0ff"
    gray_border = "#e8e8e8"

    # Za dark – ručno; za light – default Streamlit boje
    if dark:
        base_bg = "#0e1116"
        base_fg = "#eaeaea"
        card_bg = "#14181f"
        border = "#2a2f33"
        list_bg = "rgba(20,24,31,0.92)"
        list_border = "#2c3237"
        list_fg = "#f1f1f1"
        shadow = "0 14px 40px rgba(0,0,0,0.45)"
        header_grad = "linear-gradient(90deg, rgba(37,99,235,0.22), rgba(22,163,74,0.22))"
        section_strip = "#2a9249"
    else:
        base_bg = "transparent"
        base_fg = "inherit"
        card_bg = "#ffffff"
        border = gray_border
        list_bg = "rgba(255,255,255,0.92)"
        list_border = "#e6e6e6"
        list_fg = "#222222"
        shadow = "0 16px 40px rgba(0,0,0,0.12)"
        header_grad = "linear-gradient(90deg, rgba(37,99,235,0.10), rgba(22,163,74,0.10))"
        section_strip = "#20b15a"

    st.markdown(
        f"""
        <style>
            /* Header bar s blagim gradijentom */
            .block-container > div:first-child h1 {{
                background: {header_grad};
                border: 1px solid {border};
                padding: 12px 16px;
                border-radius: 14px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.04);
            }}

            /* Kartice s lijevim obojenim "stripom" */
            .app-card {{
                position: relative;
                background: {card_bg};
                border: 1px solid {border};
                padding: 1rem 1rem 1rem 1.1rem;
                border-radius: 12px;
                margin-bottom: 0.8rem;
                box-shadow: 0 1px 0 rgba(0,0,0,0.02);
                overflow: hidden;
            }}
            .app-card:before {{
                content: "";
                position: absolute;
                left: 0; top: 0; bottom: 0;
                width: 6px;
                background: {section_strip};
                opacity: 0.8;
            }}

            {".stMarkdown h1, .stMarkdown h2, .stMarkdown h3, label { color: %s !important; }" % base_fg if dark else ""}

            .transport-pill {{
                display:inline-block; padding: 2px 10px; border-radius: 999px; font-weight:700; border: 1px solid transparent;
            }}
            .pill-train {{ background:{red_bg}; color:{red}; border-color: rgba(239,68,68,0.22); }}
            .pill-car   {{ background:{green_bg}; color:{green}; border-color: rgba(22,163,74,0.22); }}

            /* Jači CTA gumbi */
            .stButton > button {{
                border-radius: 12px !important;
                border: 1px solid {border} !important;
                padding: 0.5rem 0.95rem !important;
                font-weight: 800 !important;
                background: {blue_soft};
                color: {blue};
            }}
            .stButton > button:hover {{
                transform: translateY(-1px);
                box-shadow: 0 6px 16px rgba(0,0,0,0.08);
            }}

            /* Edit/Delete stilovi – List view (7. i 8. kolona) */
            .row-line div[data-testid="column"]:nth-child(7) .stButton > button {{
                background: {green_bg}; color: {green};
                border-color: rgba(22,163,74,0.25) !important;
            }}
            .row-line div[data-testid="column"]:nth-child(8) .stButton > button {{
                background: {red_bg}; color: {red};
                border-color: rgba(239,68,68,0.25) !important;
            }}

            /* Table view – akcije u zadnjoj koloni */
            .table-row div[data-testid="column"]:last-child .stButton:nth-of-type(1) > button {{
                background: {green_bg}; color: {green};
                border-color: rgba(22,163,74,0.25) !important;
            }}
            .table-row div[data-testid="column"]:last-child .stButton:nth-of-type(2) > button {{
                background: {red_bg}; color: {red};
                border-color: rgba(239,68,68,0.25) !important;
            }}

            /* Dropdown – proziran + blur */
            div[role="listbox"] {{
                background: {list_bg} !important;
                -webkit-backdrop-filter: blur(6px);
                backdrop-filter: blur(6px);
                color: {list_fg};
                border: 1px solid {list_border};
                box-shadow: {shadow};
                border-radius: 10px;
            }}
            div[role="option"] {{ padding-top: 8px !important; padding-bottom: 8px !important; }}
            div[role="option"][aria-selected="true"],
            div[role="option"]:hover {{ background: rgba(22,163,74,0.12) !important; }}

            /* Select/Input fokus */
            div[data-baseweb="select"] > div {{ border-radius: 10px; border-color: {border}; box-shadow: none; }}
            div[data-baseweb="select"] > div:focus-within {{
                border-color: rgba(22,163,74,0.55);
                box-shadow: 0 0 0 2px rgba(22,163,74,0.25);
            }}
            .stTextInput > div > div > input,
            .stTextArea textarea,
            .stTimeInput input {{ border-radius: 10px !important; }}
            .stTextInput > div > div:has(input:focus),
            .stTextArea:has(textarea:focus),
            .stTimeInput:has(input:focus) {{
                box-shadow: 0 0 0 2px rgba(37,99,235,0.22);
                border-color: rgba(37,99,235,0.55);
            }}

            /* Header tabličnog prikaza */
            .table-header {{
                font-weight: 800; opacity: 0.9; padding: 0.35rem 0;
                border-bottom: 2px solid {blue};
                margin-bottom: 0.25rem;
            }}

            /* Badges za datumske kontrole */
            .date-badge {{
                display:inline-block; padding: 4px 10px; border-radius: 999px;
                background: {blue_soft}; color: {blue}; font-weight: 800; border: 1px solid {border};
            }}

            .muted {{ opacity: 0.6; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # JS: zatvori otvorene dropdownove klikom vani ili ESC
    components.html("""
        <script>
        (function(){
            const closeOpenSelects = () => {
                document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape'}));
                document.querySelectorAll('div[data-baseweb="select"] input').forEach(i => i.blur());
            };
            document.addEventListener('click', function(e){
                const isInside = e.target.closest('div[role="listbox"], div[data-baseweb="select"]');
                if(!isInside){ closeOpenSelects(); }
            }, true);
            document.addEventListener('keydown', function(e){
                if(e.key === 'Escape'){ closeOpenSelects(); }
            });
        })();
        </script>
    """, height=0)

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

    # Mapa NO -> EN (ako je netko staro ime kolone)
    map_no_to_en = {
        "Enhetnummer": "Unit Number",
        "Luke": "Gate",
        "Avgangstid": "Departure Time",
        "Transporttype": "Transport Type",
        "Destinasjon": "Destination",
        "Kommentar": "Comment",
        "Dato": "Service Date",
    }
    rename = {}
    for c in df.columns:
        if c in map_no_to_en:
            rename[c] = map_no_to_en[c]
    if rename:
        df = df.rename(columns=rename)

    # Stvori nedostajuće kolone
    for c in COLS:
        if c not in df.columns:
            if c == "ID":
                df[c] = [str(uuid.uuid4()) for _ in range(len(df))] if len(df) else []
            elif c == "Created At":
                df[c] = pd.NaT
            elif c == "Service Date":
                # ako nemamo, deriviraj iz Created At ako postoji; inače danas
                if "Created At" in df.columns and df["Created At"].notna().any():
                    try:
                        tmp = pd.to_datetime(df["Created At"], errors="coerce")
                        df[c] = tmp.dt.date.astype(str).fillna(date.today().strftime("%Y-%m-%d"))
                    except Exception:
                        df[c] = date.today().strftime("%Y-%m-%d")
                else:
                    df[c] = date.today().strftime("%Y-%m-%d")
            else:
                df[c] = ""

    # Cleanup
    df["ID"] = df["ID"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else str(uuid.uuid4()))
    df["Destination"] = df["Destination"].astype(str).str.strip()

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

    # Service Date kao YYYY-MM-DD
    try:
        df["Service Date"] = pd.to_datetime(df["Service Date"], errors="coerce").dt.date.astype(str)
    except Exception:
        df["Service Date"] = df["Service Date"].astype(str)

    return df[COLS]

def save_data(df: pd.DataFrame):
    with get_lock():
        df.to_csv(DATA_FILE, index=False)

def upcoming_sort_key(t: str, base_day: date) -> datetime:
    """Sort ‘upcoming’ u okviru zadanog dana (ako je to danas, onda +1 dan ako je vrijeme prošlo)."""
    try:
        h, m = map(int, str(t).split(":")[:2])
        dt = datetime.combine(base_day, time(h, m))
        # Ako gledamo današnji dan i vrijeme je prošlo – gurni iza
        if base_day == date.today() and dt < datetime.now():
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
        title = "Departures - " + (df["Service Date"].iloc[0] if not df.empty else date.today().strftime("%Y-%m-%d"))
        c.drawString(x_margin, y, title)
        y -= 1.0*cm

        # Headers
        c.setFont("Helvetica-Bold", 10)
        headers = df.columns.tolist()
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
            c.drawString(x_margin, y, line[:240])
            y -= line_height

        c.showPage()
        c.save()
        pdf = buffer.getvalue()
        buffer.close()
        return pdf
    except Exception:
        return None

# =========================
# ---- State & Theme -------
# =========================
if "transport_type" not in st.session_state:
    st.session_state.transport_type = None
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = None
if "service_date" not in st.session_state:
    st.session_state.service_date = date.today()

dark_mode = st.sidebar.toggle(f"{TXT['dark_mode']}", value=False, help="Optional dark theme")
inject_css(dark_mode)

# =========================
# ---- Title & Summary -----
# =========================
st.title(TXT["title"])

data = migrate_or_create(DATA_FILE)

# ======== Date controls (dnevno razdvajanje) ========
with st.sidebar:
    st.markdown(f"<span class='date-badge'>{TXT['service_date']}: {st.session_state.service_date.strftime('%Y-%m-%d')}</span>", unsafe_allow_html=True)
    dc1, dc2, dc3 = st.columns([1,1,1])
    if dc1.button(TXT["prev_day"]):
        st.session_state.service_date = st.session_state.service_date - timedelta(days=1)
        st.rerun()
    if dc2.button(TXT["today"]):
        st.session_state.service_date = date.today()
        st.rerun()
    if dc3.button(TXT["next_day"]):
        st.session_state.service_date = st.session_state.service_date + timedelta(days=1)
        st.rerun()
    picked = st.date_input(TXT["service_date"], value=st.session_state.service_date)
    if picked != st.session_state.service_date:
        st.session_state.service_date = picked
        st.rerun()

# Samo današnji (ili odabrani) dan u prikazu
day_str = st.session_state.service_date.strftime("%Y-%m-%d")
day_data = data[data["Service Date"] == day_str].reset_index(drop=True)

# Sažetak (po danu)
total = len(day_data)
train_cnt = (day_data["Transport Type"] == "Train").sum()
car_cnt = (day_data["Transport Type"] == "Car").sum()

with st.sidebar:
    st.subheader(TXT["count_title"])
    c1, c2, c3 = st.columns(3)
    c1.metric(TXT["total"], total)
    c2.metric(TXT["train_count"], int(train_cnt))
    c3.metric(TXT["car_count"], int(car_cnt))

# Dinamičke poznate jedinice (uči iz povijesti)
known_units = sorted(set(BASE_KNOWN_UNITS) | set(map(str, data["Unit Number"].dropna().unique())))

# =========================
# ---- Registration Form ---
# =========================
st.markdown('<div class="app-card">', unsafe_allow_html=True)
st.subheader(TXT["register"])

with st.form("register_form", clear_on_submit=True):
    # --- Unit Number s autocomplete prijedlozima ---
    unit_number = st.text_input(f"{TXT['unit']} *", key="unit_number_new")
    # Prijedlozi (na osnovu prefiksa)
    if st.session_state.unit_number_new:
        prefix = st.session_state.unit_number_new.upper()
        suggestions = [u for u in known_units if u.startswith(prefix)]
        if suggestions:
            st.caption(TXT["suggestions"])
            cols = st.columns(min(6, len(suggestions)))
            for i, sug in enumerate(suggestions[:12]):
                if cols[i % 6].button(sug, key=f"sug_new_{sug}"):
                    st.session_state.unit_number_new = sug
                    st.rerun()

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
    if not st.session_state.unit_number_new or not gate.strip() or not departure_time_val or not destination or not st.session_state.get("transport_type"):
        st.warning(TXT["validation"])
    else:
        dep_str = departure_time_val.strftime("%H:%M")
        # Duplikat u okviru istog dana
        dup_mask = (data["Service Date"] == day_str) & \
                   (data["Unit Number"].astype(str).str.strip() == st.session_state.unit_number_new.strip()) & \
                   (data["Departure Time"].astype(str).str.strip() == dep_str) & \
                   (data["Destination"].astype(str).str.strip() == destination.strip())
        if dup_mask.any():
            st.warning(TXT["duplicate"])
        else:
            new_row = pd.DataFrame([{
                "ID": str(uuid.uuid4()),
                "Service Date": day_str,
                "Unit Number": st.session_state.unit_number_new.strip().upper(),
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
# ---- Filter & Sort + View -----
# =========================
st.markdown('<div class="app-card">', unsafe_allow_html=True)
top_l, top_m, top_r = st.columns([2, 1, 1])

search = top_l.selectbox(
    TXT["filter"],
    options=["All"] + [d for d in DESTINATIONS if d],
    index=0,
)

sort_choice = top_m.selectbox(TXT["sort"], [TXT["sort_time"], TXT["sort_dest"]])

view_mode = top_r.selectbox(TXT["view_mode"], [TXT["view_list"], TXT["view_table"]], index=0)
st.markdown('</div>', unsafe_allow_html=True)

# Dodatno: brzo pretraživanje po Unit Number (na odabranom danu)
st.markdown('<div class="app-card">', unsafe_allow_html=True)
qs = st.text_input(TXT["search_unit"], key="quick_search_unit")
st.markdown('</div>', unsafe_allow_html=True)

# Primijeni filtere na day_data
filtered = day_data.copy()
if search != "All":
    filtered = filtered[filtered["Destination"] == search]
if qs.strip():
    filtered = filtered[filtered["Unit Number"].astype(str).str.contains(qs.strip(), case=False, na=False)]

# Sort
if sort_choice == TXT["sort_dest"]:
    filtered = filtered.sort_values(by=["Destination", "Departure Time"], kind="mergesort", na_position="last")
else:
    filtered = filtered.assign(_sortkey=filtered["Departure Time"].apply(lambda t: upcoming_sort_key(t, st.session_state.service_date))) \
                       .sort_values(by=["_sortkey", "Destination"], kind="mergesort") \
                       .drop(columns=["_sortkey"])

# =========================
# ---- List View ----------
# =========================
def render_list_view(df: pd.DataFrame):
    st.subheader(f"{TXT['list']} — {day_str}")
    if df.empty:
        st.info(TXT["none"])
        return

    for _, row in df.iterrows():
        real_id = row["ID"]
        st.markdown('<div class="app-card">', unsafe_allow_html=True)
        wrap = st.container()
        with wrap:
            st.markdown('<div class="row-line">', unsafe_allow_html=True)
            c = st.columns([1.1, 0.9, 0.9, 1.0, 1.1, 1.8, 0.6, 0.6])
            c[0].markdown(f"**{TXT['unit']}:** {row['Unit Number']}")
            c[1].markdown(f"**{TXT['gate']}:** {row['Gate']}")
            c[2].markdown(f"**{TXT['time']}:** {row['Departure Time']}")
            pill_class = "pill-train" if row["Transport Type"] == "Train" else "pill-car"
            c[3].markdown(f"**{TXT['transport']}:** <span class='transport-pill {pill_class}'>{row['Transport Type']}</span>", unsafe_allow_html=True)
            c[4].markdown(f"**{TXT['destination']}:** {row['Destination']}")
            c[5].markdown(f"**{TXT['comment']}:** {row['Comment'] if str(row['Comment']).strip() else '<span class=\"muted\">—</span>'}", unsafe_allow_html=True)

            edit_pressed = c[6].button(TXT["edit"], key=f"edit_{real_id}", use_container_width=True)
            del_pressed = c[7].button(TXT["delete"], key=f"del_{real_id}", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if edit_pressed:
                st.session_state.edit_id = real_id
            if del_pressed:
                st.session_state.confirm_delete = real_id
        st.markdown('</div>', unsafe_allow_html=True)

        # Delete confirmation
        if st.session_state.confirm_delete == real_id:
            with st.warning(TXT["confirm_title"]):
                dc1, dc2 = st.columns(2)
                if dc1.button(TXT["yes"], key=f"yes_{real_id}"):
                    df2 = st.session_state.get("_data_df", data).copy()
                    df2 = df2[df2["ID"] != real_id].reset_index(drop=True)
                    save_data(df2)
                    st.session_state["_data_df"] = df2
                    st.session_state.confirm_delete = None
                    st.success(TXT["toast_deleted"])
                    st.rerun()
                if dc2.button(TXT["no"], key=f"no_{real_id}"):
                    st.session_state.confirm_delete = None
                    st.rerun()

# =========================
# ---- Table View ----------
# =========================
def render_table_view(df: pd.DataFrame):
    st.subheader(f"{TXT['list']} — {day_str}")
    if df.empty:
        st.info(TXT["none"])
        return

    # Header
    st.markdown('<div class="table-header">', unsafe_allow_html=True)
    h = st.columns([1.0, 0.9, 0.9, 1.0, 1.0, 2.0, 0.9])
    h[0].markdown(TXT["unit"])
    h[1].markdown(TXT["gate"])
    h[2].markdown(TXT["time"])
    h[3].markdown(TXT["transport"])
    h[4].markdown(TXT["destination"])
    h[5].markdown(TXT["comment"])
    h[6].markdown(TXT["actions"])
    st.markdown('</div>', unsafe_allow_html=True)

    # Rows
    for _, row in df.iterrows():
        real_id = row["ID"]
        st.markdown('<div class="table-row app-card" style="padding-top:0.6rem;padding-bottom:0.6rem;">', unsafe_allow_html=True)
        c = st.columns([1.0, 0.9, 0.9, 1.0, 1.0, 2.0, 0.9])
        c[0].write(row["Unit Number"])
        c[1].write(row["Gate"])
        c[2].write(row["Departure Time"])
        pill_class = "pill-train" if row["Transport Type"] == "Train" else "pill-car"
        c[3].markdown(f"<span class='transport-pill {pill_class}'>{row['Transport Type']}</span>", unsafe_allow_html=True)
        c[4].write(row["Destination"])
        c[5].markdown(row["Comment"] if str(row["Comment"]).strip() else '<span class="muted">—</span>', unsafe_allow_html=True)

        with c[6]:
            col_a, col_b = st.columns(2)
            edit_pressed = col_a.button(TXT["edit"], key=f"t_edit_{real_id}", use_container_width=True)
            del_pressed = col_b.button(TXT["delete"], key=f"t_del_{real_id}", use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

        if edit_pressed:
            st.session_state.edit_id = real_id
        if del_pressed:
            st.session_state.confirm_delete = real_id

        if st.session_state.confirm_delete == real_id:
            with st.warning(TXT["confirm_title"]):
                dc1, dc2 = st.columns(2)
                if dc1.button(TXT["yes"], key=f"t_yes_{real_id}"):
                    df2 = st.session_state.get("_data_df", data).copy()
                    df2 = df2[df2["ID"] != real_id].reset_index(drop=True)
                    save_data(df2)
                    st.session_state["_data_df"] = df2
                    st.session_state.confirm_delete = None
                    st.success(TXT["toast_deleted"])
                    st.rerun()
                if dc2.button(TXT["no"], key=f"t_no_{real_id}"):
                    st.session_state.confirm_delete = None
                    st.rerun()

# =========================
# ---- Render chosen view --
# =========================
st.session_state["_data_df"] = data
if view_mode == TXT["view_list"]:
    render_list_view(filtered)
else:
    render_table_view(filtered)

# =========================
# ---- Edit Form -----------
# =========================
if st.session_state.edit_id is not None and (data["ID"] == st.session_state.edit_id).any():
    idx = data.index[data["ID"] == st.session_state.edit_id][0]
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.subheader(TXT["edit_title"])
    with st.form("edit_form"):
        e0, e1, e2, e3, e4 = st.columns([1,1,1,1,1])
        # Dopuštamo promjenu Service Date (npr. ako je krivo upisano)
        current_service_date = datetime.strptime(str(data.loc[idx, "Service Date"]), "%Y-%m-%d").date() \
                               if str(data.loc[idx, "Service Date"]) else st.session_state.service_date
        service_date_val = e0.date_input(TXT["service_date"], value=current_service_date)

        # Unit Number s prijedlozima
        unit_number = e1.text_input(f"{TXT['unit']} *", value=str(data.loc[idx, "Unit Number"]), key="unit_number_edit")
        if st.session_state.unit_number_edit:
            prefix = st.session_state.unit_number_edit.upper()
            suggestions = [u for u in known_units if u.startswith(prefix)]
            if suggestions:
                e1.caption(TXT["suggestions"])
                s_cols = e1.columns(min(4, len(suggestions)))
                for i, sug in enumerate(suggestions[:8]):
                    if s_cols[i % 4].button(sug, key=f"sug_edit_{sug}"):
                        st.session_state.unit_number_edit = sug
                        st.rerun()

        gate = e2.text_input(f"{TXT['gate']} *", value=str(data.loc[idx, "Gate"]))
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
            if not st.session_state.unit_number_edit or not gate.strip() or not departure_time_val or not destination or not st.session_state.edit_transport:
                st.warning(TXT["validation"])
            else:
                dep_str = departure_time_val.strftime("%H:%M")
                new_day = service_date_val.strftime("%Y-%m-%d")
                # Duplikat provjera u okviru *novog* Service Date-a
                dup_mask = (data["ID"] != data.loc[idx, "ID"]) & \
                           (data["Service Date"] == new_day) & \
                           (data["Unit Number"].astype(str).str.strip() == st.session_state.unit_number_edit.strip()) & \
                           (data["Departure Time"].astype(str).str.strip() == dep_str) & \
                           (data["Destination"].astype(str).str.strip() == str(destination).strip())
                if dup_mask.any():
                    st.warning(TXT["duplicate"])
                else:
                    data.loc[idx, "Service Date"]   = new_day
                    data.loc[idx, "Unit Number"]    = st.session_state.unit_number_edit.strip().upper()
                    data.loc[idx, "Gate"]           = gate.strip()
                    data.loc[idx, "Departure Time"] = dep_str
                    data.loc[idx, "Transport Type"] = st.session_state.edit_transport
                    data.loc[idx, "Destination"]    = str(destination).strip()
                    data.loc[idx, "Comment"]        = comment.strip()
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

# Izvoz SAMO filtriranog (trenutno vidljivog) skupa:
export_df = filtered.copy()

ec1.download_button(TXT["export_csv"], export_df.to_csv(index=False).encode("utf-8"), file_name=f"departures_{day_str}.csv")
xlsx_bytes = export_excel(export_df)
ec2.download_button(TXT["export_xlsx"], xlsx_bytes, file_name=f"departures_{day_str}.xlsx")
pdf_bytes = export_pdf(export_df)
if pdf_bytes:
    ec3.download_button(TXT["export_pdf"], pdf_bytes, file_name=f"departures_{day_str}.pdf")
else:
    ec3.write(f'<span class="muted">{TXT["install_reportlab"]}</span>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ---- Notes ---------------
# =========================
st.caption("Daily view by 'Service Date'. Data is persisted to CSV with a file lock. Use the date controls in the sidebar to browse previous days.")