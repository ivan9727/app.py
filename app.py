import streamlit as st
import sqlite3, os
import pandas as pd
from datetime import datetime, date, time, timedelta
from io import BytesIO

# =======================
# App config
# =======================
st.set_page_config(page_title="Departures", page_icon="🚉", layout="wide")
DB_PATH = "data.db"

# --- Auto-refresh svake 3 sekunde (3000 ms) ---
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=3000, key="live_sync_3s")
except Exception:
    pass

# =======================
# i18n (EN / NO)
# =======================
LANG = st.sidebar.selectbox("Language / Språk", ["English", "Norsk"], index=0)
TXT = {
    "English": {
        "title": "🚉 Departures",
        "register": "➕ Add",
        "unit": "Unit", "gate": "Gate", "time": "Time",
        "transport": "Transport", "train": "Train", "car": "Car",
        "destination": "Destination", "comment": "Comment",
        "saved": "✅ Added", "updated": "✅ Updated", "deleted": "🗑️ Deleted",
        "list": "Registered Departures", "none": "Nothing yet.",
        "edit": "Edit", "delete": "Delete", "confirm_del": "Delete this row?",
        "yes": "Yes", "no": "Cancel",
        "filter": "Filter", "filters": "Filters", "clear": "Clear",
        "sort": "Sort by", "sort_time": "Time (upcoming first)", "sort_dest": "Destination (A–Z)",
        "validation": "⚠️ Fill all required fields.",
        "duplicate": "⚠️ Same Unit+Time+Destination already exists for this day.",
        "export_csv":"Export CSV", "export_xlsx":"Export Excel", "export_pdf":"Export PDF",
        "count_title":"Summary", "total":"Total", "train_count":"Train", "car_count":"Car",
        "save_changes":"Save Edit",
        "service_date":"Service date", "today":"Today", "prev_day":"◀ Yesterday",
        "search_unit":"Quick search",
        "empty_export":"Nothing to export.",
        "gate_digits_live":"⚠️ Gate must contain digits only.",
        "gate_digits_block":"⚠️ Gate must be a number.",
        "menu_more":"⋯",
        "auto_refresh_note":"Auto-refresh every 3s enabled.",
    },
    "Norsk": {
        "title": "🚉 Avganger",
        "register": "➕ Legg til",
        "unit": "Enhet", "gate": "Luke", "time": "Tid",
        "transport": "Transport", "train": "Tog", "car": "Bil",
        "destination": "Destinasjon", "comment": "Kommentar",
        "saved": "✅ Lagt til", "updated": "✅ Oppdatert", "deleted":"🗑️ Slettet",
        "list": "Registrerte avganger", "none": "Ingen enda.",
        "edit": "Rediger", "delete": "Slett", "confirm_del": "Slette denne raden?",
        "yes": "Ja", "no": "Avbryt",
        "filter": "Filter", "filters":"Filtere", "clear":"Nullstill",
        "sort": "Sorter", "sort_time": "Tid (kommende først)", "sort_dest": "Destinasjon (A–Å)",
        "validation": "⚠️ Fyll ut alle påkrevde felt.",
        "duplicate": "⚠️ Samme enhet+tid+destinasjon finnes allerede for dagen.",
        "export_csv":"Eksporter CSV", "export_xlsx":"Eksporter Excel", "export_pdf":"Eksporter PDF",
        "count_title":"Oppsummering", "total":"Totalt", "train_count":"Tog", "car_count":"Bil",
        "save_changes":"Lagre endring",
        "service_date":"Dato", "today":"I dag", "prev_day":"◀ I går",
        "search_unit":"Hurtigsøk",
        "empty_export":"Ingenting å eksportere.",
        "gate_digits_live":"⚠️ Luke må kun inneholde tall.",
        "gate_digits_block":"⚠️ Luke må være et tall.",
        "menu_more":"⋯",
        "auto_refresh_note":"Auto-oppdatering hvert 3s er aktiv.",
    }
}[LANG]

DESTINATIONS = ["", "Førde", "Molde", "Haugesund", "Ålesund", "Trondheim", "Stavanger"]

# =======================
# CSS – dark & kompaktni chip red + BOJE GUMBOVA
# =======================
def inject_css():
    st.markdown("""
    <style>
    :root {
      --bg:#0e1116; --card:#12161d; --txt:#eaeaea; --bd:#26303a;
      --chip-bg: rgba(255,255,255,.06); --chip-bd:#2b3642; --muted:.68;
      --green:#16a34a; --green-bg:#eaf7ef; --red:#ef4444; --red-bg:#fdecec; --blue:#2563eb; --blue-dark:#1e40af; --blue-bg:#e8f0ff;
    }
    body, .block-container { background:var(--bg)!important; color:var(--txt)!important; }
    .stApp [data-testid="stHeader"]{ background:transparent; }

    /* opći izgled */
    .stButton > button, .stDownloadButton > button { border-radius:10px; font-weight:800; }

    .tile{ border:1px solid var(--bd); background:var(--card); border-radius:14px;
           padding:12px; margin-bottom:12px; box-shadow:0 6px 20px rgba(0,0,0,.25); }

    /* jedan vodoravni red, s vodoravnim scrollom na uskim ekranima */
    .chips-wrap{ overflow-x:auto; white-space:nowrap; padding-bottom:2px; }
    .chip{ display:inline-flex; gap:6px; align-items:center; margin-right:8px;
           padding:6px 10px; border-radius:10px; background:var(--chip-bg);
           border:1px solid var(--chip-bd); font-weight:800; font-size:.95rem; }
    .chip-strong{ background:var(--blue-bg); color:var(--blue); border-color:rgba(37,99,235,.25); }
    .chip-green{ background:var(--green-bg); color:var(--green); border-color:rgba(22,163,74,.25); }
    .chip-red{ background:var(--red-bg); color:var(--red); border-color:rgba(239,68,68,.25); }

    .muted{ opacity:var(--muted); }
    .stTextInput input, .stTextArea textarea, .stTimeInput input { border-radius:10px!important; }
    div[data-testid="stPopoverBody"]{ min-width:320px; }

    /* BOJE GUMBOVA */
    /* Add (submit) – plav: cilja submit gumb unutar add forme po redoslijedu */
    form[data-testid="stForm"] button[type="submit"]{
        background: var(--blue) !important;
        border-color: var(--blue-dark) !important;
        color: white !important;
    }
    form[data-testid="stForm"] button[type="submit"]:hover{
        filter: brightness(1.05);
    }

    /* Popover: 1. gumb (Edit) zelen, 2. gumb (Delete) crven */
    div[data-testid="stPopoverBody"] button:nth-of-type(1){
        background: var(--green) !important; border-color:#0f7a2a !important; color:white !important;
    }
    div[data-testid="stPopoverBody"] button:nth-of-type(2){
        background: var(--red) !important; border-color:#b91c1c !important; color:white !important;
    }
    div[data-testid="stPopoverBody"] button:hover{ filter:brightness(1.05); }
    </style>
    """, unsafe_allow_html=True)

inject_css()

# =======================
# DB
# =======================
def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS departures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_date TEXT NOT NULL,
            unit_number TEXT NOT NULL,
            gate INTEGER NOT NULL,
            departure_time TEXT NOT NULL,
            transport_type TEXT NOT NULL,
            destination TEXT NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL
        )
        """)
init_db()

# =======================
# Cache helpers (TTL=2s → svježe za multi-device)
# =======================
@st.cache_data(show_spinner=False, ttl=2)
def count_summary(day: str):
    with db() as con:
        total = con.execute("SELECT COUNT(*) FROM departures WHERE service_date=?", (day,)).fetchone()[0]
        trains = con.execute("SELECT COUNT(*) FROM departures WHERE service_date=? AND transport_type='Train'", (day,)).fetchone()[0]
        cars   = con.execute("SELECT COUNT(*) FROM departures WHERE service_date=? AND transport_type='Car'", (day,)).fetchone()[0]
    return total, trains, cars

@st.cache_data(show_spinner=False, ttl=2)
def get_rows(day: str, where_sql: str, where_args: tuple, order_sql: str):
    sql = f"SELECT * FROM departures WHERE service_date=? {where_sql} {order_sql}"
    with db() as con:
        cur = con.execute(sql, (day, *where_args))
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)

@st.cache_data(show_spinner=False, ttl=2)
def export_day(day: str):
    with db() as con:
        cur = con.execute("SELECT * FROM departures WHERE service_date=? ORDER BY departure_time, destination", (day,))
        cols = [c[0] for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)

def invalidate_caches():
    count_summary.clear(); get_rows.clear(); export_day.clear()

# =======================
# CRUD
# =======================
def insert_row(day, unit, gate, tstr, transport, dest, comment):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db() as con:
        dup = con.execute("""SELECT 1 FROM departures
                             WHERE service_date=? AND UPPER(unit_number)=UPPER(?)
                               AND departure_time=? AND destination=?""",
                          (day, unit.strip(), tstr, dest.strip())).fetchone()
        if dup: return False, "dup"
        con.execute("""INSERT INTO departures(service_date, unit_number, gate, departure_time,
                                             transport_type, destination, comment, created_at)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (day, unit.strip().upper(), int(gate), tstr, transport, dest.strip(), comment.strip(), now))
    invalidate_caches()
    return True, None

def update_row(row_id, day, unit, gate, tstr, transport, dest, comment):
    with db() as con:
        dup = con.execute("""SELECT 1 FROM departures
                             WHERE id<>? AND service_date=? AND UPPER(unit_number)=UPPER(?)
                               AND departure_time=? AND destination=?""",
                          (row_id, day, unit.strip(), tstr, dest.strip())).fetchone()
        if dup: return False, "dup"
        con.execute("""UPDATE departures
                       SET service_date=?, unit_number=?, gate=?, departure_time=?, transport_type=?, destination=?, comment=?
                       WHERE id=?""",
                    (day, unit.strip().upper(), int(gate), tstr, transport, dest.strip(), comment.strip(), row_id))
    invalidate_caches()
    return True, None

def delete_row(row_id):
    with db() as con:
        con.execute("DELETE FROM departures WHERE id=?", (row_id,))
    invalidate_caches()

# =======================
# State
# =======================
if "service_date" not in st.session_state: st.session_state.service_date = date.today()
if "edit_id" not in st.session_state: st.session_state.edit_id = None

# =======================
# Sidebar: date & summary
# =======================
c1, c2 = st.sidebar.columns(2)
if c1.button(TXT["prev_day"]): st.session_state.service_date -= timedelta(days=1)
if c2.button(TXT["today"]): st.session_state.service_date = date.today()
picked = st.sidebar.date_input(TXT["service_date"], value=st.session_state.service_date)
if picked != st.session_state.service_date:
    st.session_state.service_date = picked

day_str = st.session_state.service_date.strftime("%Y-%m-%d")
total, trains, cars = count_summary(day_str)
st.sidebar.subheader(TXT["count_title"])
m1, m2, m3 = st.sidebar.columns(3)
m1.metric(TXT["total"], total); m2.metric(TXT["train_count"], trains); m3.metric(TXT["car_count"], cars)
st.sidebar.caption(TXT["auto_refresh_note"])

# =======================
# Title
# =======================
st.title(TXT["title"])

# =======================
# AUTO-CLEAR nakon dodavanja (reset prije forme)
# =======================
from datetime import time as _t
if st.session_state.get("add_clear_pending"):
    st.session_state["add_unit"] = ""
    st.session_state["add_gate"] = ""
    st.session_state["add_time"] = _t(0, 0)   # makni ako želiš zadržati zadnje vrijeme
    st.session_state["add_dest"] = ""
    st.session_state["add_transport"] = "Train"
    st.session_state["add_comment"] = ""
    st.session_state["add_clear_pending"] = False

# =======================
# Register (Add)
# =======================
st.subheader(TXT["register"])
with st.form("add_form", clear_on_submit=False):
    a1, a2, a3, a4 = st.columns([1.2, 1, 1, 1.2])
    unit_new = a1.text_input(TXT["unit"] + " *", key="add_unit")
    gate_new = a2.text_input(TXT["gate"] + " *", key="add_gate")
    if gate_new and not gate_new.isdigit(): st.warning(TXT["gate_digits_live"])
    time_new = a3.time_input(TXT["time"] + " *", step=timedelta(minutes=5), key="add_time")
    dest_new = a4.selectbox(TXT["destination"] + " *", DESTINATIONS, index=0, key="add_dest")
    b1, b2 = st.columns([1, 3])
    transport_new = b1.radio(TXT["transport"] + " *", ["Train", "Car"], horizontal=True, key="add_transport")
    comment_new = b2.text_area(TXT["comment"], height=58, key="add_comment")
    submit_add = st.form_submit_button(TXT["register"])

if submit_add:
    if (not st.session_state.add_unit or
        not st.session_state.add_gate or
        not st.session_state.add_time or
        st.session_state.add_dest is None):
        st.warning(TXT["validation"])
    elif not st.session_state.add_gate.isdigit():
        st.warning(TXT["gate_digits_block"])
    else:
        ok, err = insert_row(
            day_str,
            st.session_state.add_unit,
            st.session_state.add_gate,
            st.session_state.add_time.strftime("%H:%M"),
            st.session_state.add_transport,
            st.session_state.add_dest,
            st.session_state.add_comment or ""
        )
        if not ok and err == "dup":
            st.warning(TXT["duplicate"])
        else:
            st.success(TXT["saved"])
            st.session_state["add_clear_pending"] = True
            st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# =======================
# Filter (popover)
# =======================
fc, _ = st.columns([1, 8])
with fc.popover(TXT["filter"]):
    dest_filter = st.selectbox(TXT["destination"], ["All"] + [d for d in DESTINATIONS if d], index=0, key="flt_dest")
    sort_choice = st.selectbox(TXT["sort"], [TXT["sort_time"], TXT["sort_dest"]], key="flt_sort")
    quick = st.text_input(TXT["search_unit"], key="flt_q")
    if st.button(TXT["clear"]):
        st.session_state.flt_dest="All"; st.session_state.flt_sort=TXT["sort_time"]; st.session_state.flt_q=""

# SQL filter/order
where_sql, where_args = "", ()
if st.session_state.get("flt_dest","All") != "All":
    where_sql += " AND destination=?"; where_args += (st.session_state.flt_dest,)
if st.session_state.get("flt_q","").strip():
    where_sql += " AND UPPER(unit_number) LIKE ?"; where_args += (f"%{st.session_state.flt_q.strip().upper()}%",)
order_sql = " ORDER BY destination, departure_time" if st.session_state.get("flt_sort",TXT["sort_time"])==TXT["sort_dest"] else " ORDER BY departure_time, destination"

# =======================
# Dohvati sve (bez paginacije)
# =======================
df = get_rows(day_str, where_sql, where_args, order_sql)

# =======================
# Tile renderer – kompaktan red + 3 točke (Edit/Delete)
# =======================
def render_tile(row):
    rid = int(row["id"])
    editing = (st.session_state.edit_id == rid)

    st.markdown('<div class="tile">', unsafe_allow_html=True)

    if not editing:
        st.markdown(
            f"""
            <div class="chips-wrap">
              <span class="chip chip-strong">{TXT['unit']}: {row['unit_number']}</span>
              <span class="chip">{TXT['gate']}: {row['gate']}</span>
              <span class="chip">{TXT['time']}: <b>{row['departure_time']}</b></span>
              <span class="chip {{'chip-red' if row['transport_type']=='Train' else 'chip-green'}}">{row['transport_type']}</span>
              <span class="chip">{TXT['destination']}: {row['destination']}</span>
            </div>
            """, unsafe_allow_html=True
        )
        st.markdown(f"<div class='muted' style='margin-top:6px'>{row['comment'] or '—'}</div>", unsafe_allow_html=True)

        # 3 točke – popover s obojenim gumbima (Edit zelen, Delete crven)
        c1, _, _ = st.columns([0.2, 0.2, 6])
        with c1:
            with st.popover(TXT["menu_more"]):
                a1, a2 = st.columns(2)
                if a1.button(TXT["edit"], key=f"ed_{rid}"):
                    st.session_state.edit_id = rid
                if a2.button(TXT["delete"], key=f"dl_{rid}"):
                    st.session_state[f"askdel_{rid}"] = True

        if st.session_state.get(f"askdel_{rid}"):
            st.warning(TXT["confirm_del"])
            d1, d2 = st.columns(2)
            if d1.button(TXT["yes"], key=f"yes_{rid}"):
                delete_row(rid); st.session_state[f"askdel_{rid}"] = False; st.success(TXT["deleted"])
            if d2.button(TXT["no"], key=f"no_{rid}"):
                st.session_state[f"askdel_{rid}"] = False

    else:
        # INLINE EDIT unutar istog tile-a (jedan submit → Save Edit)
        with st.form(f"edit_{rid}", clear_on_submit=False):
            e1, e2, e3, e4, e5 = st.columns([1.2,1,1,1.2,1.2])
            try:
                cur_day = datetime.strptime(str(row["service_date"]), "%Y-%m-%d").date()
            except: cur_day = date.today()
            dval = e1.date_input(TXT["service_date"], value=cur_day, key=f"d_{rid}")
            uval = e2.text_input(TXT["unit"], value=str(row["unit_number"]), key=f"u_{rid}")
            gval = e3.text_input(TXT["gate"], value=str(row["gate"]), key=f"g_{rid}")
            if gval and not gval.isdigit(): st.warning(TXT["gate_digits_live"])
            try:
                hh,mm = str(row["departure_time"]).split(":"); t_default=time(int(hh),int(mm))
            except: t_default=None
            tval = e4.time_input(TXT["time"], value=t_default, step=timedelta(minutes=5), key=f"t_{rid}")
            dsel = e5.selectbox(TXT["destination"], DESTINATIONS,
                                index=max(0, DESTINATIONS.index(str(row["destination"])) if str(row["destination"]) in DESTINATIONS else 0),
                                key=f"ds_{rid}")
            e6, e7 = st.columns([1,5])
            trval = e6.radio(TXT["transport"], ["Train","Car"], horizontal=True,
                             index=0 if row["transport_type"]=="Train" else 1, key=f"tr_{rid}")
            com = st.text_area(TXT["comment"], value=str(row["comment"]) if str(row["comment"]) not in ("nan","None") else "", height=58, key=f"c_{rid}")

            sbtn = st.form_submit_button(TXT["save_changes"])

        if sbtn:
            if not uval or not gval.strip() or not tval or not dsel:
                st.warning(TXT["validation"])
            elif not gval.isdigit():
                st.warning(TXT["gate_digits_block"])
            else:
                ok, err = update_row(
                    rid,
                    dval.strftime("%Y-%m-%d"),
                    uval, gval, tval.strftime("%H:%M"),
                    trval, str(dsel), com
                )
                if not ok and err=="dup":
                    st.warning(TXT["duplicate"])
                else:
                    st.session_state.edit_id = None
                    st.success(TXT["updated"])

    st.markdown("</div>", unsafe_allow_html=True)

# =======================
# Lista
# =======================
st.subheader(TXT["list"])
if df.empty:
    st.info(TXT["none"])
else:
    for _, r in df.iterrows():
        render_tile(r)

# =======================
# Export
# =======================
st.markdown("<hr>", unsafe_allow_html=True)
exp = export_day(day_str); empty = exp.empty
c1, c2, c3 = st.columns([1,1,1])
c1.download_button(TXT["export_csv"], exp.to_csv(index=False).encode("utf-8") if not empty else b"",
                   file_name=f"departures_{day_str}.csv", disabled=empty, help=TXT["empty_export"] if empty else None)

def export_excel(df:pd.DataFrame)->bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name="Departures")
        w.sheets["Departures"].set_column(0, len(df.columns)-1, 20)
    return out.getvalue()

def export_pdf(df:pd.DataFrame)->bytes|None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
        buf=BytesIO(); c=canvas.Canvas(buf, pagesize=A4)
        W,H=A4; xM,yM=2*cm,2*cm; y=H-yM
        c.setFont("Helvetica-Bold",14)
        c.drawString(xM,y,"Departures - "+(df["service_date"].iloc[0] if not df.empty else day_str)); y-=1.0*cm
        c.setFont("Helvetica-Bold",10); hdr=" | ".join(df.columns); c.drawString(xM,y,hdr[:200]); y-=0.5*cm
        c.setFont("Helvetica",9); lh=0.55*cm
        for _, rr in df.iterrows():
            line=" | ".join(str(rr.get(h,"")) for h in df.columns)
            if y<yM+lh: c.showPage(); y=H-yM; c.setFont("Helvetica",9)
            c.drawString(xM,y,line[:240]); y-=lh
        c.showPage(); c.save(); pdf=buf.getvalue(); buf.close(); return pdf
    except:
        return None

xlsx = export_excel(exp) if not empty else None
c2.download_button(TXT["export_xlsx"], xlsx if xlsx else b"", file_name=f"departures_{day_str}.xlsx",
                   disabled=empty, help=TXT["empty_export"] if empty else None)
pdf = export_pdf(exp) if not empty else None
c3.download_button(TXT["export_pdf"], pdf if pdf else b"", file_name=f"departures_{day_str}.pdf",
                   disabled=empty, help=TXT["empty_export"] if empty else None)