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
st.set_page_config(page_title="Departures Manager", page_icon="🚉", layout="wide")

# =========================
# Const & Schema
# =========================
DATA_FILE = "departures.csv"

COLS = [
    "ID", "Service Date", "Unit Number", "Gate",
    "Departure Time", "Transport Type", "Destination",
    "Comment", "Has Box", "Box Confirmed", "Created At"
]

DESTINATIONS = ["", "Førde", "Molde", "Haugesund", "Ålesund", "Trondheim", "Stavanger"]
BASE_KNOWN_UNITS = ["PTRU", "BGLU"]

# =========================
# Lang (EN/NO)
# =========================
LANG = st.sidebar.selectbox("Language / Språk", ["English", "Norsk"], index=0)
TXT = {
    "English": {
        "title":"🚉 Departures",
        "register":"➕ Add",
        "unit":"Unit Number", "gate":"Gate", "time":"Time",
        "transport":"Transport", "train":"Train", "car":"Car",
        "destination":"Destination", "comment":"Comment",
        "saved":"✅ Added", "updated":"✅ Updated",
        "list":"Registered Departures", "none":"Nothing yet.",
        "edit":"Edit", "delete":"Delete", "actions":"Actions",
        "confirm_title":"Delete this row?",
        "yes":"Yes", "no":"Cancel",
        "filter":"Filter", "sort":"Sort by",
        "sort_time":"Time (upcoming first)", "sort_dest":"Destination (A–Z)",
        "validation":"⚠️ Fill all required fields.",
        "duplicate":"⚠️ Same Unit + Time + Destination already exists for this day.",
        "export_csv":"Export CSV", "export_xlsx":"Export Excel", "export_pdf":"Export PDF",
        "count_title":"Summary", "total":"Total", "train_count":"Train", "car_count":"Car",
        "save_changes":"Save",
        "toast_deleted":"Deleted.",
        "service_date":"Service date", "today":"Today", "prev_day":"◀ Yesterday",
        "search_unit":"Quick search",
        "theme":"Theme", "theme_auto":"Auto", "theme_light":"Light", "theme_dark":"Dark",
        "empty_export":"Nothing to export.",
        "gate_digits_live":"⚠️ Gate must contain digits only.",
        "gate_digits_block":"⚠️ Gate must be a number.",
        "menu_more":"⋯",
        "box":"Box", "has_box":"Has Box", "confirm_box":"Confirm Box", "unconfirm_box":"Undo Box",
        "bulk_confirm":"Confirm all boxes for this day",
        "filter_title":"Filters",
        "clear_filters":"Clear",
    },
    "Norsk": {
        "title":"🚉 Avganger",
        "register":"➕ Legg til",
        "unit":"Enhetnummer", "gate":"Luke", "time":"Tid",
        "transport":"Transport", "train":"Tog", "car":"Bil",
        "destination":"Destinasjon", "comment":"Kommentar",
        "saved":"✅ Lagt til", "updated":"✅ Oppdatert",
        "list":"Registrerte avganger", "none":"Ingen enda.",
        "edit":"Rediger", "delete":"Slett", "actions":"Handlinger",
        "confirm_title":"Slette denne raden?",
        "yes":"Ja", "no":"Avbryt",
        "filter":"Filter", "sort":"Sorter",
        "sort_time":"Tid (kommende først)", "sort_dest":"Destinasjon (A–Å)",
        "validation":"⚠️ Fyll ut alle påkrevde felt.",
        "duplicate":"⚠️ Samme enhet + tid + destinasjon finnes allerede for denne dagen.",
        "export_csv":"Eksporter CSV", "export_xlsx":"Eksporter Excel", "export_pdf":"Eksporter PDF",
        "count_title":"Oppsummering", "total":"Totalt", "train_count":"Tog", "car_count":"Bil",
        "save_changes":"Lagre",
        "toast_deleted":"Slettet.",
        "service_date":"Dato", "today":"I dag", "prev_day":"◀ I går",
        "search_unit":"Hurtigsøk",
        "theme":"Tema", "theme_auto":"Auto", "theme_light":"Lys", "theme_dark":"Mørk",
        "empty_export":"Ingenting å eksportere.",
        "gate_digits_live":"⚠️ Luke må kun inneholde tall.",
        "gate_digits_block":"⚠️ Luke må være et tall.",
        "menu_more":"⋯",
        "box":"Boks", "has_box":"Har boks", "confirm_box":"Bekreft boks", "unconfirm_box":"Angre boks",
        "bulk_confirm":"Bekreft alle bokser for dagen",
        "filter_title":"Filtere",
        "clear_filters":"Očisti",
    },
}[LANG]

# =========================
# CSS / JS (modern & simple)
# =========================
def inject_css(theme: str):
    green="#16a34a"; green_bg="#eaf7ef"
    red="#ef4444"; red_bg="#fdecec"
    blue="#2563eb"; blue_soft="#e8f0ff"
    slate="#0f172a"; gray_border="#e8e8e8"

    dark = (theme=="Dark")
    light = (theme=="Light")

    if dark:
        base_bg="#0e1116"; base_fg="#eaeaea"; card_bg="#12161d"; border="#26303a"
        chip_bg="rgba(255,255,255,.06)"; chip_fg="#e9eef6"
        glow="0 8px 30px rgba(0,0,0,.45)"
    else:
        base_bg="#ffffff"; base_fg="#222"; card_bg="#ffffff"; border=gray_border
        chip_bg="rgba(2,6,23,.04)"; chip_fg="#16202a"
        glow="0 10px 26px rgba(0,0,0,.12)"

    st.markdown(
        f"""
        <style>
        body, .block-container {{ background:{base_bg} !important; color:{base_fg} !important; }}

        /* header */
        .block-container > div:first-child h1 {{
            padding:10px 14px; border-radius:12px;
            border:1px solid {border};
            background:linear-gradient(90deg, rgba(37,99,235,0.08), rgba(22,163,74,0.08));
        }}

        /* modern simple row card (tile) */
        .tile {{
            border:1px solid {border}; border-radius:14px; background:{card_bg};
            padding:12px 12px; margin-bottom:10px; box-shadow:{glow};
        }}
        .tile-header {{
            display:flex; align-items:center; gap:10px; justify-content:space-between; margin-bottom:8px;
        }}
        .tile-chips {{ display:flex; flex-wrap:wrap; gap:8px; }}
        .chip {{
            display:inline-flex; align-items:center; gap:6px;
            background:{chip_bg}; color:{chip_fg};
            padding:6px 10px; border-radius:10px; font-weight:700; border:1px solid {border};
            white-space:nowrap;
        }}
        .chip-strong {{ background:{blue_soft}; color:{blue}; border-color:rgba(37,99,235,.25); }}
        .chip-success {{ background:{green_bg}; color:{green}; border-color:rgba(22,163,74,.25); }}
        .chip-danger {{ background:{red_bg}; color:{red}; border-color:rgba(239,68,68,.25); }}

        .tile-footer {{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-top:6px; }}
        .muted {{ opacity:.65; }}

        .soft-divider {{ height:1px; background:linear-gradient(90deg, rgba(0,0,0,.08), rgba(0,0,0,0)); margin:.8rem 0; }}

        /* buttons */
        .stButton > button {{ border-radius:10px; font-weight:800; }}
        .more-btn > button {{ padding:.35rem .6rem; font-weight:900; border-radius:10px; }}

        /* inputs */
        .stTextInput input, .stTextArea textarea, .stTimeInput input {{ border-radius:10px !important; }}

        /* popover for filters */
        div[data-testid="stPopoverBody"] {{ min-width:320px; }}

        /* mobile layout tweaks */
        @media (max-width: 900px) {{
            .tile-chips {{ gap:6px; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # JS: close select drop-downs click-out/ESC (smanjuje lag)
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
# Cache helpers (brže)
# =========================
@st.cache_data(show_spinner=False)
def load_csv(path:str)->pd.DataFrame:
    if not os.path.exists(path):
        df=pd.DataFrame(columns=COLS)
        df.to_csv(path, index=False)
        return df
    df=pd.read_csv(path)
    # ensure cols (and migrate)
    if "Has Box" not in df.columns: df["Has Box"]=False
    if "Box Confirmed" not in df.columns: df["Box Confirmed"]=False
    for c in COLS:
        if c not in df.columns:
            if c=="ID": df[c]=[str(uuid.uuid4()) for _ in range(len(df))] if len(df) else []
            elif c=="Created At": df[c]=pd.NaT
            elif c in ("Has Box","Box Confirmed"): df[c]=False
            elif c=="Service Date": df[c]=date.today().strftime("%Y-%m-%d")
            else: df[c]=""
    # normalize
    def _fix_time(t):
        t=str(t).strip()
        if not t or t.lower()=="nan": return ""
        try:
            hh,mm=t.split(":")[:2]; return f"{int(hh):02d}:{int(mm):02d}"
        except: return ""
    df["Departure Time"]=df["Departure Time"].astype(str).map(_fix_time)
    try:
        df["Service Date"]=pd.to_datetime(df["Service Date"], errors="coerce").dt.date.astype(str)
    except:
        df["Service Date"]=df["Service Date"].astype(str)
    df["Has Box"]=df["Has Box"].fillna(False).astype(bool)
    df["Box Confirmed"]=df["Box Confirmed"].fillna(False).astype(bool)
    return df[COLS]

def save_csv(df:pd.DataFrame):
    df.to_csv(DATA_FILE, index=False)
    load_csv.clear()  # invalidiraj cache

@st.cache_data(show_spinner=False)
def compute_known_units(df:pd.DataFrame):
    return sorted(set(u.upper() for u in BASE_KNOWN_UNITS) | set(map(lambda x:str(x).upper(), df["Unit Number"].dropna().unique())))

# =========================
# State / Theme
# =========================
if "service_date" not in st.session_state: st.session_state.service_date=date.today()
if "inline_edit_id" not in st.session_state: st.session_state.inline_edit_id=None
if "confirm_delete" not in st.session_state: st.session_state.confirm_delete=None

with st.sidebar:
    st.markdown(f"**{TXT['theme']}**")
    theme_pick = st.radio("", options=[TXT["theme_light"], TXT["theme_dark"], TXT["theme_auto"]], horizontal=True, index=0, label_visibility="collapsed")
theme_map={TXT["theme_auto"]:"Dark" if st.get_option('theme.base')=="dark" else "Light", TXT["theme_light"]:"Light", TXT["theme_dark"]:"Dark"}
inject_css(theme_map.get(theme_pick,"Light"))

# =========================
# Data & title
# =========================
st.title(TXT["title"])
data = load_csv(DATA_FILE)

# Date controls (jednostavno)
with st.sidebar:
    c1,c2=st.columns(2)
    if c1.button(TXT["prev_day"]): st.session_state.service_date-=timedelta(days=1); st.rerun()
    if c2.button(TXT["today"]): st.session_state.service_date=date.today(); st.rerun()
    picked=st.date_input(TXT["service_date"], value=st.session_state.service_date)
    if picked!=st.session_state.service_date: st.session_state.service_date=picked; st.rerun()

day_str = st.session_state.service_date.strftime("%Y-%m-%d")
day_data = data[data["Service Date"]==day_str].reset_index(drop=True)
known_units = compute_known_units(data)

# Summary (sidebar)
with st.sidebar:
    st.subheader(TXT["count_title"])
    c1,c2,c3=st.columns(3)
    c1.metric(TXT["total"], len(day_data))
    c2.metric(TXT["train_count"], int((day_data["Transport Type"]=="Train").sum()))
    c3.metric(TXT["car_count"], int((day_data["Transport Type"]=="Car").sum()))

# =========================
# Register (brže, minimalno)
# =========================
st.subheader(TXT["register"])
with st.form("register_form", clear_on_submit=False):
    c1,c2,c3,c4=st.columns([1.3,1,1,1.2])
    unit_new = c1.text_input(TXT["unit"]+" *", key="unit_number_new")
    gate_new = c2.text_input(TXT["gate"]+" *")
    if gate_new and not gate_new.isdigit():
        st.warning(TXT["gate_digits_live"])
    time_new = c3.time_input(TXT["time"]+" *", step=timedelta(minutes=5))
    dest_new = c4.selectbox(TXT["destination"]+" *", DESTINATIONS, index=0)
    c5,c6 = st.columns([1,3])
    transport_new = c5.radio(TXT["transport"]+" *", ["Train","Car"], horizontal=True)
    has_box_new = c6.checkbox(TXT["has_box"], value=False)
    comment_new = st.text_area(TXT["comment"], height=64)
    submit_add = st.form_submit_button(TXT["register"])

# suggestions (izvan forme)
if st.session_state.get("unit_number_new"):
    pref = st.session_state.unit_number_new.upper()
    sugs = [u for u in known_units if u.startswith(pref)]
    if sugs:
        sc = st.columns(min(6, len(sugs)))
        for i,s in enumerate(sugs[:12]):
            if sc[i%6].button(s, key=f"sug_{s}"):
                st.session_state.unit_number_new = s
                st.rerun()
st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)

if submit_add:
    if not st.session_state.unit_number_new or not gate_new.strip() or not time_new or not dest_new:
        st.warning(TXT["validation"])
    elif not gate_new.isdigit():
        st.warning(TXT["gate_digits_block"])
    else:
        tstr = time_new.strftime("%H:%M")
        dup = (data["Service Date"]==day_str) & \
              (data["Unit Number"].astype(str).str.upper()==st.session_state.unit_number_new.strip().upper()) & \
              (data["Departure Time"]==tstr) & \
              (data["Destination"].astype(str).str.strip()==dest_new.strip())
        if dup.any():
            st.warning(TXT["duplicate"])
        else:
            row = pd.DataFrame([{
                "ID": str(uuid.uuid4()),
                "Service Date": day_str,
                "Unit Number": st.session_state.unit_number_new.strip().upper(),
                "Gate": gate_new.strip(),
                "Departure Time": tstr,
                "Transport Type": transport_new,
                "Destination": dest_new.strip(),
                "Comment": comment_new.strip(),
                "Has Box": bool(has_box_new),
                "Box Confirmed": False,
                "Created At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
            data = pd.concat([data, row], ignore_index=True)
            save_csv(data)
            st.success(TXT["saved"])

# =========================
# Filter (u malom popoveru)
# =========================
st.markdown(" ")
fcol1, fcol2 = st.columns([1,8])
with fcol1.popover(TXT["filter"]):
    # sve “skriveno” u mali prozorčić – jednostavnije za ekran
    dest_filter = st.selectbox(TXT["destination"], ["All"]+[d for d in DESTINATIONS if d], index=0, key="flt_dest")
    sort_choice = st.selectbox(TXT["sort"], [TXT["sort_time"], TXT["sort_dest"]], key="flt_sort")
    quick = st.text_input(TXT["search_unit"], key="flt_q")
    if st.button(TXT["clear_filters"]):
        st.session_state.flt_dest="All"; st.session_state.flt_sort=TXT["sort_time"]; st.session_state.flt_q=""
        st.rerun()

# primijeni filter (brzo, bez dodatnih rerunova)
filtered = day_data.copy()
if st.session_state.get("flt_dest","All") != "All":
    filtered = filtered[filtered["Destination"]==st.session_state.flt_dest]
q = st.session_state.get("flt_q","").strip()
if q:
    filtered = filtered[filtered["Unit Number"].astype(str).str.contains(q, case=False, na=False)]

if st.session_state.get("flt_sort", TXT["sort_time"]) == TXT["sort_dest"]:
    filtered = filtered.sort_values(["Destination","Departure Time"], kind="mergesort", na_position="last")
else:
    def _k(t):
        try:
            h,m = map(int,str(t).split(":")[:2])
            base = st.session_state.service_date
            dt = datetime.combine(base, time(h,m))
            if base == date.today() and dt < datetime.now():
                dt += timedelta(days=1)
            return dt
        except:
            return datetime.max
    filtered = filtered.assign(_k=filtered["Departure Time"].apply(_k)) \
                       .sort_values(["_k","Destination"], kind="mergesort") \
                       .drop(columns=["_k"])

# =========================
# Bulk: Confirm all boxes for the day
# =========================
if not filtered.empty and (filtered["Has Box"] & ~filtered["Box Confirmed"]).any():
    if st.button("✅ " + TXT["bulk_confirm"]):
        ids = filtered.loc[(filtered["Has Box"]) & (~filtered["Box Confirmed"]), "ID"]
        if not ids.empty:
            ix = data["ID"].isin(ids)
            data.loc[ix,"Box Confirmed"] = True
            save_csv(data)
            st.success("OK")
            st.rerun()

# =========================
# Modern simple TILE + inline edit
# =========================
def render_row(row: pd.Series):
    rid = row["ID"]
    has_box = bool(row.get("Has Box", False))
    box_ok = bool(row.get("Box Confirmed", False))

    # header (chips)
    st.markdown('<div class="tile">', unsafe_allow_html=True)
    h1, h2 = st.columns([8,1])
    with h1:
        st.markdown(
            f"""
            <div class="tile-header">
              <div class="tile-chips">
                 <span class="chip chip-strong">{row['Unit Number']}</span>
                 <span class="chip">{TXT['gate']}: {row['Gate']}</span>
                 <span class="chip">{TXT['time']}: <b>{row['Departure Time']}</b></span>
                 <span class="chip {'chip-danger' if row['Transport Type']=='Train' else 'chip-success'}">{row['Transport Type']}</span>
                 <span class="chip">{row['Destination'] or '—'}</span>
                 <span class="chip">{TXT['box']}: {('✅' if has_box else '—')}</span>
                 <span class="chip">{'Confirmed ✅' if box_ok else 'Pending ⏳'}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with h2:
        # mali meni
        with st.popover(TXT["menu_more"]):
            cA,cB = st.columns(2)
            if cA.button(TXT["edit"], key=f"ed_{rid}"):
                st.session_state.inline_edit_id = rid
            if cB.button(TXT["delete"], key=f"dl_{rid}"):
                st.session_state.confirm_delete = rid

    # comment & actions line
    st.markdown(
        f"""<div class="tile-footer">
              <div class="muted">{(row['Comment'] or '—')}</div>
              <div></div>
            </div>""",
        unsafe_allow_html=True
    )

    # inline edit (u istom tile-u, bez novog prozorčića)
    if st.session_state.inline_edit_id == rid:
        with st.form(f"edit_{rid}", clear_on_submit=False):
            c1,c2,c3,c4,c5 = st.columns([1.2,0.9,0.9,1.2,1.2])
            # date
            try:
                cur_day = datetime.strptime(str(row["Service Date"]), "%Y-%m-%d").date()
            except:
                cur_day = st.session_state.service_date
            dval = c1.date_input(TXT["service_date"], value=cur_day, key=f"d_{rid}")
            # unit
            uval = c2.text_input(TXT["unit"], value=str(row["Unit Number"]), key=f"u_{rid}")
            # gate
            gval = c3.text_input(TXT["gate"], value=str(row["Gate"]), key=f"g_{rid}")
            if gval and not gval.isdigit():
                st.warning(TXT["gate_digits_live"])
            # time
            try:
                hh,mm = str(row["Departure Time"]).split(":")
                t_default = time(int(hh), int(mm))
            except:
                t_default = None
            tval = c4.time_input(TXT["time"], value=t_default, step=timedelta(minutes=5), key=f"t_{rid}")
            # dest
            dsel = c5.selectbox(TXT["destination"], DESTINATIONS,
                                index=max(0, DESTINATIONS.index(str(row["Destination"])) if str(row["Destination"]) in DESTINATIONS else 0),
                                key=f"ds_{rid}")

            c6,c7,c8 = st.columns([1,1,3])
            trval = c6.radio(TXT["transport"], ["Train","Car"], horizontal=True,
                             index=0 if row["Transport Type"]=="Train" else 1, key=f"tr_{rid}")
            hbval = c7.checkbox(TXT["has_box"], value=has_box, key=f"hb_{rid}")
            cb_btn = c8.button(("✅ "+TXT["confirm_box"]) if not box_ok else ("↩ "+TXT["unconfirm_box"]), key=f"cb_{rid}")

            com = st.text_area(TXT["comment"], value=str(row["Comment"]), height=64, key=f"c_{rid}")
            sbtn = st.form_submit_button(TXT["save_changes"])

        # potvrda box-a (bez submit-a)
        if cb_btn:
            idx = data.index[data["ID"]==rid][0]
            if hbval:
                data.loc[idx,"Has Box"]=True
                data.loc[idx,"Box Confirmed"]=not box_ok
                save_csv(data); st.success("OK"); st.rerun()
            else:
                st.info(TXT["has_box"]+"?")

        # inline spremanje
        if sbtn:
            if not uval or not gval.strip() or not tval or not dsel:
                st.warning(TXT["validation"])
            elif not gval.isdigit():
                st.warning(TXT["gate_digits_block"])
            else:
                dep_str = tval.strftime("%H:%M")
                new_day = dval.strftime("%Y-%m-%d")
                dup = (data["ID"]!=rid) & \
                      (data["Service Date"]==new_day) & \
                      (data["Unit Number"].astype(str).str.upper()==uval.strip().upper()) & \
                      (data["Departure Time"]==dep_str) & \
                      (data["Destination"].astype(str).str.strip()==str(dsel).strip())
                if dup.any():
                    st.warning(TXT["duplicate"])
                else:
                    idx = data.index[data["ID"]==rid][0]
                    data.loc[idx, ["Service Date","Unit Number","Gate","Departure Time","Transport Type",
                                   "Destination","Comment","Has Box"]] = [
                        new_day, uval.strip().upper(), gval.strip(), dep_str, trval, str(dsel).strip(), com.strip(), bool(hbval)
                    ]
                    save_csv(data); st.success(TXT["updated"])
                    st.session_state.inline_edit_id=None
                    st.rerun()

    # delete potvrda
    if st.session_state.confirm_delete == rid:
        st.warning(TXT["confirm_title"])
        cx1,cx2 = st.columns(2)
        if cx1.button(TXT["yes"], key=f"yy_{rid}"):
            df2=data.copy(); df2=df2[df2["ID"]!=rid].reset_index(drop=True)
            save_csv(df2); st.session_state.confirm_delete=None; st.success(TXT["toast_deleted"]); st.rerun()
        if cx2.button(TXT["no"], key=f"nn_{rid}"):
            st.session_state.confirm_delete=None; st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# render lista
st.subheader(TXT["list"])
if filtered.empty:
    st.info(TXT["none"])
else:
    for _, r in filtered.iterrows():
        render_row(r)

# =========================
# Export (disabled kad prazno)
# =========================
st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
ec1,ec2,ec3=st.columns([1,1,1])
is_empty = filtered.empty
ec1.download_button(TXT["export_csv"], filtered.to_csv(index=False).encode("utf-8") if not is_empty else b"",
                    file_name=f"departures_{day_str}.csv", disabled=is_empty, help=TXT["empty_export"] if is_empty else None)

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
        for _,rr in df.iterrows():
            line=" | ".join(str(rr.get(h,"")) for h in df.columns)
            if y<yM+lh: c.showPage(); y=H-yM; c.setFont("Helvetica",9)
            c.drawString(xM,y,line[:240]); y-=lh
        c.showPage(); c.save(); pdf=buf.getvalue(); buf.close(); return pdf
    except:
        return None

xlsx = export_excel(filtered) if not is_empty else None
ec2.download_button(TXT["export_xlsx"], xlsx if xlsx else b"", file_name=f"departures_{day_str}.xlsx",
                    disabled=is_empty, help=TXT["empty_export"] if is_empty else None)

pdf = export_pdf(filtered) if not is_empty else None
ec3.download_button(TXT["export_pdf"], pdf if pdf else b"", file_name=f"departures_{day_str}.pdf",
                    disabled=is_empty, help=TXT["empty_export"] if is_empty else None)