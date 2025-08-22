import streamlit as st
import pandas as pd
import os
import uuid
from datetime import datetime, date, time, timedelta
from io import BytesIO
import streamlit.components.v1 as components

# =========================
# App Config
# =========================
st.set_page_config(page_title="Departures Manager", page_icon="🚉", layout="wide", initial_sidebar_state="expanded")

# =========================
# Const & Schema
# =========================
DATA_FILE = "departures.csv"

COLS = [
    "ID", "Service Date", "Unit Number", "Gate",
    "Departure Time", "Transport Type", "Destination",
    "Comment", "Finished", "Created At"
]

DESTINATIONS = ["", "Førde", "Molde", "Haugesund", "Ålesund", "Trondheim", "Stavanger"]
BASE_KNOWN_UNITS = ["PTRU", "BGLU"]

# =========================
# Lang (EN/NO)
# =========================
LANG = st.sidebar.selectbox("Language / Språk", ["English", "Norsk"], index=0)
TXT = {
    "English": {
        "title":"🚉 Departures Registration System",
        "register":"➕ Register Departure",
        "unit":"Unit Number", "gate":"Gate", "time":"Departure Time",
        "transport":"Transport Type", "train":"Train", "car":"Car",
        "destination":"Destination", "comment":"Comment",
        "saved":"✅ Departure added!", "updated":"✅ Departure updated!",
        "list":"📋 Registered Departures", "none":"No departures yet.",
        "edit":"Edit", "delete":"Delete", "actions":"Actions",
        "confirm_title":"Are you sure you want to delete this departure?",
        "yes":"Yes, delete", "no":"Cancel",
        "filter":"Filter by destination", "sort":"Sort by",
        "sort_time":"Departure time (upcoming first)", "sort_dest":"Destination (A–Z)",
        "validation":"⚠️ Please fill in all required fields.",
        "duplicate":"⚠️ A departure with the same Unit, Time and Destination already exists for the selected day.",
        "export_csv":"Export CSV", "export_xlsx":"Export Excel", "export_pdf":"Export PDF",
        "count_title":"Summary", "total":"Total", "train_count":"Train", "car_count":"Car",
        "edit_title":"Edit Departure", "save_changes":"Save",
        "toast_deleted":"Departure deleted.",
        "install_reportlab":'Install reportlab for PDF export: pip install reportlab',
        "view_mode":"View mode", "view_list":"List", "view_table":"Table",
        "service_date":"Service date", "today":"Today", "prev_day":"◀ Yesterday",
        "search_unit":"Quick search by Unit Number",
        "theme":"Theme", "theme_auto":"Auto", "theme_light":"Light", "theme_dark":"Dark",
        "empty_export":"Nothing to export for this day.",
        "gate_digits_live":"⚠️ Gate must contain digits only.",
        "gate_digits_block":"⚠️ Gate must be a number.",
        "menu_more":"⋯",
        "finished":"Finished", "finish_btn":"Finish", "undo_btn":"Undo",
    },
    "Norsk": {
        "title":"🚉 Avgangsregistreringssystem",
        "register":"➕ Registrer avgang",
        "unit":"Enhetnummer", "gate":"Luke", "time":"Avgangstid",
        "transport":"Transporttype", "train":"Tog", "car":"Bil",
        "destination":"Destinasjon", "comment":"Kommentar",
        "saved":"✅ Avgang registrert!", "updated":"✅ Avgang oppdatert!",
        "list":"📋 Registrerte avganger", "none":"Ingen avganger ennå.",
        "edit":"Rediger", "delete":"Slett", "actions":"Handlinger",
        "confirm_title":"Er du sikker på at du vil slette denne avgangen?",
        "yes":"Ja, slett", "no":"Avbryt",
        "filter":"Filtrer etter destinasjon", "sort":"Sorter etter",
        "sort_time":"Avgangstid (kommende først)", "sort_dest":"Destinasjon (A–Å)",
        "validation":"⚠️ Vennligst fyll ut alle påkrevde felt.",
        "duplicate":"⚠️ Det finnes allerede en avgang med samme enhet, tid og destinasjon for valgt dag.",
        "export_csv":"Eksporter CSV", "export_xlsx":"Eksporter Excel", "export_pdf":"Eksporter PDF",
        "count_title":"Oppsummering", "total":"Totalt", "train_count":"Tog", "car_count":"Bil",
        "edit_title":"Rediger avgang", "save_changes":"Lagre",
        "toast_deleted":"Avgang slettet.",
        "install_reportlab":'Installer reportlab for PDF: pip install reportlab',
        "view_mode":"Visning", "view_list":"Liste", "view_table":"Tabell",
        "service_date":"Dato", "today":"I dag", "prev_day":"◀ I går",
        "search_unit":"Hurtigsøk etter enhet",
        "theme":"Tema", "theme_auto":"Auto", "theme_light":"Lys", "theme_dark":"Mørk",
        "empty_export":"Ingenting å eksportere for denne dagen.",
        "gate_digits_live":"⚠️ Luke må kun inneholde tall.",
        "gate_digits_block":"⚠️ Luke må være et tall.",
        "menu_more":"⋯",
        "finished":"Ferdig", "finish_btn":"Fullfør", "undo_btn":"Angre",
    },
}[LANG]

# =========================
# CSS / JS
# =========================
def inject_css(theme: str):
    green="#16a34a"; green_bg="#eaf7ef"
    red="#ef4444"; red_bg="#fdecec"
    blue="#2563eb"; blue_soft="#e8f0ff"
    purple="#7c3aed"; teal="#0d9488"; amber="#b45309"
    gray_border="#e8e8e8"

    dark = (theme=="Dark")
    light = (theme=="Light")

    if dark:
        base_bg="#0e1116"; base_fg="#eaeaea"; card_bg="#14181f"; border="#2a2f33"
        list_bg="rgba(20,24,31,0.92)"; list_border="#2c3237"; list_fg="#f1f1f1"
        shadow="0 14px 40px rgba(0,0,0,0.45)"
        header_grad="linear-gradient(90deg, rgba(37,99,235,0.22), rgba(22,163,74,0.22))"
        section_strip="#2a9249"
    else:
        base_bg="transparent" if theme=="Auto" else "#ffffff"
        base_fg="inherit"; card_bg="#ffffff"; border=gray_border
        list_bg="rgba(255,255,255,0.92)"; list_border="#e6e6e6"; list_fg="#222222"
        shadow="0 16px 40px rgba(0,0,0,0.12)"
        header_grad="linear-gradient(90deg, rgba(37,99,235,0.10), rgba(22,163,74,0.10))"
        section_strip="#20b15a"

    st.markdown(
        f"""
        <style>
        {"body, .block-container {{ background-color: %s !important; color: %s !important; }}" % (base_bg, base_fg) if dark or light else ""}

        .block-container > div:first-child h1 {{
            background: {header_grad}; border: 1px solid {border};
            padding: 12px 16px; border-radius: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        }}

        /* ROW CARD – label/value grid (sprječava ružno prelamanje) */
        .rowcard {{
            position:relative; background:{card_bg}; border:1px solid {border};
            border-radius:14px; padding:12px 14px; margin-bottom:10px;
        }}
        .rowcard:before {{
            content:""; position:absolute; left:0; top:0; bottom:0; width:6px; background:{section_strip}; opacity:.85; border-top-left-radius:14px; border-bottom-left-radius:14px;
        }}
        .kv {{
            display:grid; grid-template-columns: repeat(6, minmax(90px, 1fr)); gap:10px; align-items:start;
        }}
        .kv .cell {{ background:rgba(0,0,0,0.03); border:1px solid {border}; border-radius:12px; padding:6px 10px; }}
        .kv .lab {{ display:block; font-size:12px; opacity:.7; margin-bottom:2px; text-transform:uppercase; letter-spacing:.02em; }}
        .kv .val {{ font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
        .kv .val.time {{ min-width:64px; text-align:center; }}
        .kv .val.badge-train {{ color:{red}; background:{red_bg}; border-radius:999px; padding:2px 8px; display:inline-block; }}
        .kv .val.badge-car   {{ color:{green}; background:{green_bg}; border-radius:999px; padding:2px 8px; display:inline-block; }}
        .kv .val.badge-done  {{ color:{green}; background:{green_bg}; border-radius:999px; padding:2px 8px; display:inline-block; }}
        .kv .val.badge-pend  {{ color:{amber}; background:#fff6e7; border-radius:999px; padding:2px 8px; display:inline-block; }}

        .actions {{
            display:flex; justify-content:flex-end; gap:8px; align-items:center;
        }}
        .more-btn > button {{ border-radius:12px; padding:.35rem .6rem; font-weight:900; }}

        /* Segmented theme toggle */
        .segmented .stRadio > div {{ display:flex; gap:6px }}
        .segmented .stRadio label {{ flex:1 }}
        .segmented .stRadio div[role="radiogroup"] > div {{ flex:1 }}
        .segmented .stRadio input {{ display:none }}
        .segmented .stRadio div[role="radio"] {{ border:1px solid {border}; border-radius:10px; padding:.4rem .6rem; text-align:center; cursor:pointer }}
        .segmented .stRadio div[aria-checked="true"] {{ background:{blue_soft}; color:{blue}; border-color:rgba(37,99,235,.35) }}

        /* Dropdown blur */
        div[role="listbox"]{{ background:{list_bg} !important; -webkit-backdrop-filter:blur(6px); backdrop-filter:blur(6px);
            color:{list_fg}; border:1px solid {list_border}; box-shadow:{shadow}; border-radius:10px; }}

        .soft-divider {{ height:1px; background: linear-gradient(90deg, rgba(0,0,0,.08), rgba(0,0,0,0)); margin:.8rem 0; }}
        .date-badge {{ display:inline-block; padding:4px 10px; border-radius:999px; background:{blue_soft}; color:{blue}; font-weight:800; border:1px solid {border}; }}
        .muted {{ opacity:.6 }}

        /* Mobile */
        @media (max-width: 900px) {{
            .kv {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # JS: close dropdown klikom vani/ESC
    components.html("""
        <script>
        (function(){
            const closeOpenSelects = () => {
                document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape'}));
                document.querySelectorAll('div[data-baseweb="select"] input').forEach(i => i.blur());
            };
            document.addEventListener('click', function(e){
                const inside = e.target.closest('div[role="listbox"], div[data-baseweb="select"]');
                if(!inside){ closeOpenSelects(); }
            }, true);
            document.addEventListener('keydown', function(e){
                if(e.key === 'Escape'){ closeOpenSelects(); }
            });
        })();
        </script>
    """, height=0)

# =========================
# Utils
# =========================
def migrate_or_create(path:str)->pd.DataFrame:
    if not os.path.exists(path):
        df=pd.DataFrame(columns=COLS); df.to_csv(path, index=False); return df
    df=pd.read_csv(path)
    # map NO->EN if needed
    map_no_to_en={"Enhetnummer":"Unit Number","Luke":"Gate","Avgangstid":"Departure Time",
                  "Transporttype":"Transport Type","Destinasjon":"Destination","Kommentar":"Comment","Dato":"Service Date"}
    if any(c in map_no_to_en for c in df.columns):
        df=df.rename(columns={c:map_no_to_en[c] for c in df.columns if c in map_no_to_en})
    # ensure cols
    for c in COLS:
        if c not in df.columns:
            if c=="ID": df[c]=[str(uuid.uuid4()) for _ in range(len(df))] if len(df) else []
            elif c=="Created At": df[c]=pd.NaT
            elif c=="Service Date": df[c]=date.today().strftime("%Y-%m-%d")
            elif c=="Finished": df[c]=False
            else: df[c]=""
    # normalize time
    def _fix_time(t):
        t=str(t).strip()
        if not t or t.lower()=="nan": return ""
        try:
            hh,mm=t.split(":")[:2]; return f"{int(hh):02d}:{int(mm):02d}"
        except: return ""
    df["Departure Time"]=df["Departure Time"].astype(str).map(_fix_time)
    # normalize date
    try:
        df["Service Date"]=pd.to_datetime(df["Service Date"], errors="coerce").dt.date.astype(str)
    except:
        df["Service Date"]=df["Service Date"].astype(str)
    df["ID"]=df["ID"].apply(lambda x: str(x).strip() if str(x).strip() else str(uuid.uuid4()))
    df["Destination"]=df["Destination"].astype(str).str.strip()
    if "Finished" in df.columns:
        df["Finished"]=df["Finished"].fillna(False).astype(bool)
    return df[COLS]

def save_data(df:pd.DataFrame):
    df.to_csv(DATA_FILE, index=False)

def upcoming_sort_key(t:str, base:date)->datetime:
    try:
        h,m=map(int,str(t).split(":")[:2]); dt=datetime.combine(base, time(h,m))
        if base==date.today() and dt<datetime.now(): dt+=timedelta(days=1)
        return dt
    except:
        from datetime import datetime as _dt
        return _dt.max

def export_excel(df:pd.DataFrame)->bytes:
    out=BytesIO()
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
        title="Departures - "+(df["Service Date"].iloc[0] if not df.empty else date.today().strftime("%Y-%m-%d"))
        c.drawString(xM,y,title); y-=1.0*cm
        c.setFont("Helvetica-Bold",10); hdr=" | ".join(df.columns); c.drawString(xM,y,hdr[:200]); y-=0.5*cm
        c.setFont("Helvetica",9); lh=0.55*cm
        for _,r in df.iterrows():
            line=" | ".join(str(r.get(h,"")) for h in df.columns)
            if y<yM+lh: c.showPage(); y=H-yM; c.setFont("Helvetica",9)
            c.drawString(xM,y,line[:240]); y-=lh
        c.showPage(); c.save(); pdf=buf.getvalue(); buf.close(); return pdf
    except:
        return None

# =========================
# State / Theme
# =========================
if "service_date" not in st.session_state: st.session_state.service_date=date.today()
if "transport_type" not in st.session_state: st.session_state.transport_type=None
if "edit_id" not in st.session_state: st.session_state.edit_id=None
if "inline_open" not in st.session_state: st.session_state.inline_open=None  # koji red je otvoren za inline edit
if "confirm_delete" not in st.session_state: st.session_state.confirm_delete=None

# Segmented theme toggle
with st.sidebar:
    st.markdown(f"**{TXT['theme']}**")
    st.markdown('<div class="segmented">', unsafe_allow_html=True)
    theme_pick = st.radio("", options=[TXT["theme_light"], TXT["theme_dark"], TXT["theme_auto"]], horizontal=True, index=0)
    st.markdown("</div>", unsafe_allow_html=True)

theme_map={TXT["theme_auto"]:"Auto", TXT["theme_light"]:"Light", TXT["theme_dark"]:"Dark"}
inject_css(theme_map[theme_pick])

# =========================
# Title & Data
# =========================
st.title(TXT["title"])
data=migrate_or_create(DATA_FILE)

# Date controls (bez Tomorrow)
with st.sidebar:
    st.markdown(f"<span class='date-badge'>{TXT['service_date']}: {st.session_state.service_date.strftime('%Y-%m-%d')}</span>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    if c1.button(TXT["prev_day"]): st.session_state.service_date-=timedelta(days=1); st.rerun()
    if c2.button(TXT["today"]): st.session_state.service_date=date.today(); st.rerun()
    picked=st.date_input(TXT["service_date"], value=st.session_state.service_date)
    if picked!=st.session_state.service_date: st.session_state.service_date=picked; st.rerun()

day_str=st.session_state.service_date.strftime("%Y-%m-%d")
day_data=data[data["Service Date"]==day_str].reset_index(drop=True)

# Summary
total=len(day_data); trains=(day_data["Transport Type"]=="Train").sum(); cars=(day_data["Transport Type"]=="Car").sum()
with st.sidebar:
    st.subheader(TXT["count_title"])
    c1,c2,c3=st.columns(3)
    c1.metric(TXT["total"], total); c2.metric(TXT["train_count"], int(trains)); c3.metric(TXT["car_count"], int(cars))

# Known units
known_units=sorted(set(u.upper() for u in BASE_KNOWN_UNITS)|set(map(lambda x:str(x).upper(), data["Unit Number"].dropna().unique())))

# =========================
# Register form (bez hintova, ne resetira)
# =========================
st.subheader(TXT["register"])
with st.form("register_form", clear_on_submit=False):
    c1,c2,c3,c4=st.columns([1.3,1,1,1.2])

    unit_number=c1.text_input(f"{TXT['unit']} *", key="unit_number_new")
    gate=c2.text_input(f"{TXT['gate']} *")
    if gate and not gate.isdigit(): st.warning(TXT["gate_digits_live"])

    departure_time_val=c3.time_input(f"{TXT['time']} *", step=timedelta(minutes=5))
    destination=c4.selectbox(f"{TXT['destination']} *", DESTINATIONS)

    comment=st.text_area(TXT["comment"], placeholder="", height=80)

    transport_type=st.radio(f"{TXT['transport']} *", options=["Train","Car"], horizontal=True,
                            index=0 if st.session_state.get("transport_type")=="Train" else 1 if st.session_state.get("transport_type")=="Car" else 0)
    st.session_state.transport_type=transport_type

    submitted=st.form_submit_button(TXT["register"])

# Autocomplete (IZVAN forme)
if st.session_state.get("unit_number_new"):
    prefix=st.session_state.unit_number_new.upper()
    suggestions=[u for u in known_units if u.startswith(prefix)]
    if suggestions:
        cols=st.columns(min(6,len(suggestions)))
        for i,sug in enumerate(suggestions[:12]):
            if cols[i%6].button(sug, key=f"sug_new_{sug}"):
                st.session_state.unit_number_new=sug
                st.rerun()
st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)

if submitted:
    if (not st.session_state.unit_number_new or not gate.strip() or not departure_time_val or
        not destination or not st.session_state.get("transport_type")):
        st.warning(TXT["validation"])
    elif not gate.isdigit():
        st.warning(TXT["gate_digits_block"])
    else:
        dep_str=departure_time_val.strftime("%H:%M")
        dup_mask=(data["Service Date"]==day_str) & \
                 (data["Unit Number"].astype(str).str.strip().str.upper()==st.session_state.unit_number_new.strip().upper()) & \
                 (data["Departure Time"].astype(str).str.strip()==dep_str) & \
                 (data["Destination"].astype(str).str.strip()==destination.strip())
        if dup_mask.any():
            st.warning(TXT["duplicate"])
        else:
            row=pd.DataFrame([{
                "ID":str(uuid.uuid4()), "Service Date":day_str,
                "Unit Number":st.session_state.unit_number_new.strip().upper(),
                "Gate":gate.strip(), "Departure Time":dep_str,
                "Transport Type":st.session_state.transport_type, "Destination":destination.strip(),
                "Comment":comment.strip(), "Finished":False,
                "Created At":datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
            data=pd.concat([data,row], ignore_index=True); save_data(data); st.success(TXT["saved"])

# =========================
# Filter / Sort / View
# =========================
fc1,fc2,fc3=st.columns([2,1,1])
search=fc1.selectbox(TXT["filter"], options=["All"]+[d for d in DESTINATIONS if d], index=0)
sort_choice=fc2.selectbox(TXT["sort"], [TXT["sort_time"], TXT["sort_dest"]])
view_mode=fc3.selectbox(TXT["view_mode"], [TXT["view_list"], TXT["view_table"]], index=0)
st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)

qs=st.text_input(TXT["search_unit"], key="quick_search_unit")
st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)

filtered=day_data.copy()
if search!="All": filtered=filtered[filtered["Destination"]==search]
if qs.strip(): filtered=filtered[filtered["Unit Number"].astype(str).str.contains(qs.strip(), case=False, na=False)]

if sort_choice==TXT["sort_dest"]:
    filtered=filtered.sort_values(by=["Destination","Departure Time"], kind="mergesort", na_position="last")
else:
    filtered=filtered.assign(_k=filtered["Departure Time"].apply(lambda t: upcoming_sort_key(t, st.session_state.service_date))) \
                     .sort_values(by=["_k","Destination"], kind="mergesort").drop(columns=["_k"])

# =========================
# Helpers
# =========================
def toggle_finished(row_id:str):
    global data
    idx=data.index[data["ID"]==row_id][0]
    data.loc[idx,"Finished"]=not bool(data.loc[idx,"Finished"])
    save_data(data)

def action_menu(col, label:str):
    with col.popover(label=label, help=TXT["actions"]):
        a1,a2=st.columns(2)
        do_edit=a1.button(TXT["edit"], use_container_width=True)
        do_del =a2.button(TXT["delete"], use_container_width=True)
        return do_edit, do_del

# =========================
# List/Table + inline edit
# =========================
def render_row(row:pd.Series):
    rid=row["ID"]
    finished = bool(row.get("Finished", False))

    # GRID prikaz
    st.markdown('<div class="rowcard">', unsafe_allow_html=True)
    c_top = st.columns([7,1.2])
    with c_top[1]:
        do_edit=False; do_del=False
        de, dd = action_menu(st, TXT["menu_more"])
        do_edit, do_del = de, dd
    st.markdown(
        f"""
        <div class="kv">
          <div class="cell"><span class="lab">{TXT['unit']}</span><span class="val">{row['Unit Number']}</span></div>
          <div class="cell"><span class="lab">{TXT['gate']}</span><span class="val">{row['Gate']}</span></div>
          <div class="cell"><span class="lab">{TXT['time']}</span><span class="val time">{row['Departure Time']}</span></div>
          <div class="cell"><span class="lab">{TXT['transport']}</span>
            <span class="val {'badge-train' if row['Transport Type']=='Train' else 'badge-car'}">{row['Transport Type']}</span></div>
          <div class="cell"><span class="lab">{TXT['destination']}</span><span class="val">{row['Destination']}</span></div>
          <div class="cell"><span class="lab">{TXT['finished']}</span>
            <span class="val {'badge-done' if finished else 'badge-pend'}">{'✅' if finished else '⏳'}</span></div>
          <div class="cell" style="grid-column: 1 / -1;"><span class="lab">{TXT['comment']}</span>
            <span class="val">{row['Comment'] if str(row['Comment']).strip() else '—'}</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # završetak / undo dugme odmah ispod grida
    ft_c1, ft_c2, ft_c3 = st.columns([1,1,6])
    if ft_c1.button(TXT["finish_btn"] if not finished else TXT["undo_btn"], key=f"fin_{rid}"):
        toggle_finished(rid); st.experimental_rerun()

    # Inline EDIT (mini forma u istom dokumentu)
    if do_edit or st.session_state.inline_open == rid:
        st.session_state.inline_open = rid  # označi otvorenim
        with st.form(f"edit_inline_{rid}", clear_on_submit=False):
            r1c1,r1c2,r1c3,r1c4,r1c5=st.columns([1,1,1,1,1])

            # Service date
            try:
                cur_day = datetime.strptime(str(row["Service Date"]), "%Y-%m-%d").date()
            except:
                cur_day = st.session_state.service_date
            service_date_val=r1c1.date_input(TXT["service_date"], value=cur_day)

            unit_number=r1c2.text_input(f"{TXT['unit']} *", value=str(row["Unit Number"]), key=f"unit_edit_{rid}")
            gate=r1c3.text_input(f"{TXT['gate']} *", value=str(row["Gate"]))
            if gate and not gate.isdigit(): st.warning(TXT["gate_digits_live"])

            try:
                hh,mm=str(row["Departure Time"]).split(":")
                default_t=time(int(hh), int(mm))
            except: default_t=None
            departure_time_val=r1c4.time_input(f"{TXT['time']} *", value=default_t, step=timedelta(minutes=5))

            destination=r1c5.selectbox(TXT["destination"], DESTINATIONS,
                                        index=max(0, DESTINATIONS.index(str(row["Destination"])) if str(row["Destination"]) in DESTINATIONS else 0))

            transport_type_edit=st.radio(f"{TXT['transport']} *", options=["Train","Car"], horizontal=True,
                                         index=0 if row["Transport Type"]=="Train" else 1)
            comment=st.text_area(TXT["comment"], value=str(row["Comment"]), height=80)

            save_changes=st.form_submit_button(TXT["save_changes"])

        # Autocomplete (izvan inline forme)
        if st.session_state.get(f"unit_edit_{rid}"):
            prefix=st.session_state[f"unit_edit_{rid}"].upper()
            suggestions=[u for u in known_units if u.startswith(prefix)]
            if suggestions:
                cc=st.columns(min(6,len(suggestions)))
                for i,sug in enumerate(suggestions[:12]):
                    if cc[i%6].button(sug, key=f"sug_inline_{rid}_{sug}"):
                        st.session_state[f"unit_edit_{rid}"]=sug
                        st.experimental_rerun()

        if save_changes:
            if (not st.session_state[f"unit_edit_{rid}"] or not gate.strip() or not departure_time_val or not destination or not transport_type_edit):
                st.warning(TXT["validation"])
            elif not gate.isdigit():
                st.warning(TXT["gate_digits_block"])
            else:
                # spremi
                didx=data.index[data["ID"]==rid][0]
                dep_str=departure_time_val.strftime("%H:%M"); new_day=service_date_val.strftime("%Y-%m-%d")
                dup=(data["ID"]!=rid) & \
                    (data["Service Date"]==new_day) & \
                    (data["Unit Number"].astype(str).str.strip().str.upper()==st.session_state[f"unit_edit_{rid}"].strip().upper()) & \
                    (data["Departure Time"].astype(str).str.strip()==dep_str) & \
                    (data["Destination"].astype(str).str.strip()==str(destination).strip())
                if dup.any():
                    st.warning(TXT["duplicate"])
                else:
                    data.loc[didx,"Service Date"]=new_day
                    data.loc[didx,"Unit Number"]=st.session_state[f"unit_edit_{rid}"].strip().upper()
                    data.loc[didx,"Gate"]=gate.strip()
                    data.loc[didx,"Departure Time"]=dep_str
                    data.loc[didx,"Transport Type"]=transport_type_edit
                    data.loc[didx,"Destination"]=str(destination).strip()
                    data.loc[didx,"Comment"]=comment.strip()
                    if pd.isna(data.loc[didx,"Created At"]) or str(data.loc[didx,"Created At"]).strip()=="":
                        data.loc[didx,"Created At"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    save_data(data); st.success(TXT["updated"])
                    st.session_state.inline_open=None
                    st.experimental_rerun()

    # Delete potvrda
    if do_del:
        st.session_state.confirm_delete = rid
    if st.session_state.confirm_delete == rid:
        st.warning(TXT["confirm_title"])
        cA,cB = st.columns(2)
        if cA.button(TXT["yes"], key=f"yes_{rid}"):
            df2=data.copy(); df2=df2[df2["ID"]!=rid].reset_index(drop=True); save_data(df2)
            st.session_state.confirm_delete=None; st.success(TXT["toast_deleted"]); st.experimental_rerun()
        if cB.button(TXT["no"], key=f"no_{rid}"):
            st.session_state.confirm_delete=None; st.experimental_rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # /rowcard

def render_list(df:pd.DataFrame):
    st.subheader(TXT["list"])
    if df.empty: st.info(TXT["none"]); return
    for _,row in df.iterrows():
        render_row(row)

def render_table(df:pd.DataFrame):
    # i u "table" modu prikaz je isti kartični grid – zbog responsive konzistentnosti
    render_list(df)

if view_mode==TXT["view_list"]: render_list(filtered)
else: render_table(filtered)

# =========================
# Export (disabled kad je prazno)
# =========================
st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
ec1,ec2,ec3=st.columns([1,1,1])
export_df=filtered.copy(); is_empty=export_df.empty
ec1.download_button(TXT["export_csv"], export_df.to_csv(index=False).encode("utf-8") if not is_empty else b"",
                    file_name=f"departures_{day_str}.csv", disabled=is_empty, help=TXT["empty_export"] if is_empty else None)
def _xlsx_or_none(d): return export_excel(d) if not d.empty else None
def _pdf_or_none(d):  return export_pdf(d) if not d.empty else None
xlsx_bytes=_xlsx_or_none(export_df)
ec2.download_button(TXT["export_xlsx"], xlsx_bytes if xlsx_bytes else b"", file_name=f"departures_{day_str}.xlsx",
                    disabled=is_empty, help=TXT["empty_export"] if is_empty else None)
pdf_bytes=_pdf_or_none(export_df)
ec3.download_button(TXT["export_pdf"], pdf_bytes if pdf_bytes else b"", file_name=f"departures_{day_str}.pdf",
                    disabled=is_empty, help=TXT["empty_export"] if is_empty else None)
if is_empty: st.caption(TXT["empty_export"])