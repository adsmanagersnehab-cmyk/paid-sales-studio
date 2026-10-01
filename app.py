import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json, os, re, io, base64
from datetime import datetime
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from google.genai import types

# --- 1. PAGE SETUP & AUTO-COLLAPSED SIDEBAR ---
st.set_page_config(
    page_title="PAID SALES ANALYSER & PRIDICTOR STUDIO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

components.html(
    """<script>
    setTimeout(() => {
        const sb = window.parent.document.querySelector('[data-testid="stSidebar"]');
        const btn = window.parent.document.querySelector('[data-testid="stSidebarCollapseButton"] button');
        if (sb && sb.getAttribute("aria-expanded") === "true" && btn) btn.click();
    }, 250);
    </script>""", height=0, width=0
)

# --- 2. LOCAL CONFIG & AUTO-SAVED CREDENTIALS ---
CFG_FILE = "config.json"
def get_cfg():
    if os.path.exists(CFG_FILE):
        try:
            with open(CFG_FILE, "r") as f: return json.load(f)
        except Exception: return {}
    return {}

def set_cfg(k, v):
    c = get_cfg(); c[k] = v
    try:
        with open(CFG_FILE, "w") as f: json.dump(c, f, indent=2)
    except Exception: pass

cfg = get_cfg()

# --- 3. D2C BENCHMARKS (INDIAN MARKET PRESETS) ---
D2C_CATEGORIES = {
    "👗 Women's Western & Contemporary Wear": {"aov": 2800, "cpm": 220, "ctr": 2.4, "cvr": 2.2, "cpc": 9.16, "rto": 22, "target_roas": 3.8, "usp": "Pure cotton, flattering fits, deep pockets."},
    "🥻 Ethnic Wear, Kurtis & Sarees": {"aov": 1850, "cpm": 180, "ctr": 2.6, "cvr": 2.8, "cpc": 6.92, "rto": 28, "target_roas": 3.5, "usp": "Festive elegance, authentic weaves, rich drape."},
    "👕 Men's Casual & Streetwear": {"aov": 1650, "cpm": 190, "ctr": 1.9, "cvr": 2.0, "cpc": 10.0, "rto": 26, "target_roas": 3.2, "usp": "Heavyweight cotton, oversized fit, durable."},
    "💍 Jewellery & Fashion Accessories": {"aov": 1400, "cpm": 160, "ctr": 2.8, "cvr": 3.0, "cpc": 5.71, "rto": 16, "target_roas": 3.8, "usp": "Anti-tarnish, waterproof, hypoallergenic."},
    "👠 Footwear & Shoes": {"aov": 2200, "cpm": 240, "ctr": 1.8, "cvr": 1.9, "cpc": 13.3, "rto": 32, "target_roas": 3.4, "usp": "Orthopedic arch support, lightweight comfort."},
    "💄 Beauty & Skincare": {"aov": 1150, "cpm": 260, "ctr": 2.1, "cvr": 3.2, "cpc": 12.3, "rto": 14, "target_roas": 3.0, "usp": "Clean toxin-free, dermatologically tested."},
    "🌿 Health & Nutrition": {"aov": 1500, "cpm": 320, "ctr": 1.6, "cvr": 2.6, "cpc": 20.0, "rto": 12, "target_roas": 2.8, "usp": "Certified organic, zero sugar, clinically proven."},
    "🏡 Home Decor & Living": {"aov": 2400, "cpm": 210, "ctr": 1.7, "cvr": 1.8, "cpc": 12.3, "rto": 20, "target_roas": 3.2, "usp": "Artisanal handcrafted, modern aesthetic."},
    "🍫 Gourmet Food & Snacks": {"aov": 950, "cpm": 180, "ctr": 2.5, "cvr": 3.5, "cpc": 7.2, "rto": 10, "target_roas": 2.6, "usp": "Zero preservatives, small-batch roasted."},
    "🎧 Consumer Tech & Gadgets": {"aov": 2600, "cpm": 280, "ctr": 1.5, "cvr": 1.7, "cpc": 18.6, "rto": 24, "target_roas": 3.5, "usp": "Fast charging, active noise isolation."}
}

# --- 4. ULTRA SAAS CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    h1, h2, h3, h4, h5, .kpi-val, th { font-family: 'Outfit', sans-serif !important; letter-spacing: -0.025em !important; }
    .stApp { background: radial-gradient(circle at 15% 15%, #0f172a 0%, #06090f 90%); color: #f8fafc; }
    [data-testid="stSidebar"] { background: #080c14 !important; border-right: 1px solid rgba(255,255,255,0.08); }
    
    /* Top Navbar */
    .top-navbar {
        background: linear-gradient(135deg, rgba(30,41,59,0.5) 0%, rgba(15,23,42,0.8) 100%);
        border: 1px solid rgba(255,255,255,0.09); border-radius: 16px; padding: 16px 22px;
        margin-bottom: 22px; backdrop-filter: blur(16px); display: flex; justify-content: space-between; align-items: center;
    }
    
    /* Button Pill Tabs */
    div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
        gap: 8px !important; background: rgba(15,23,42,0.85) !important;
        border: 1px solid rgba(255,255,255,0.1) !important; padding: 5px 8px !important;
        border-radius: 9999px !important; margin-bottom: 22px !important; display: inline-flex !important;
    }
    div[data-testid="stTabs"] button[role="tab"] {
        border-radius: 9999px !important; padding: 9px 24px !important;
        font-family: 'Outfit', sans-serif !important; font-weight: 700 !important; font-size: 13px !important;
        color: #94a3b8 !important; border: none !important; background: transparent !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important; color: #ffffff !important;
        box-shadow: 0 4px 18px rgba(99,102,241,0.5) !important;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"], div[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }
    
    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, rgba(30,41,59,0.35) 0%, rgba(15,23,42,0.6) 100%);
        border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 18px;
    }
    .kpi-lbl { font-size: 10px; letter-spacing: 0.09em; text-transform: uppercase; color: #94a3b8; font-weight: 700; }
    .kpi-val { font-size: 26px; font-weight: 900; color: #ffffff; margin: 4px 0; }
    .kpi-pill { font-size: 11px; padding: 3px 8px; border-radius: 6px; font-weight: 700; }
    .pill-green { background: rgba(16,185,129,0.15); color: #34d399; }
    .pill-red { background: rgba(244,63,94,0.15); color: #fb7185; }
    .pill-blue { background: rgba(99,102,241,0.15); color: #818cf8; }
    
    /* Centered Glowing Action Buttons */
    div[data-testid="stButton"] { display: flex !important; justify-content: center !important; margin: 8px auto !important; width: 100% !important; }
    div[data-testid="stButton"] > button {
        border-radius: 9999px !important; font-family: 'Outfit', sans-serif !important; font-weight: 700 !important;
        font-size: 13px !important; padding: 9px 28px !important; background: rgba(99,102,241,0.14) !important;
        color: #a5b4fc !important; border: 1.5px solid #6366f1 !important; box-shadow: 0 4px 18px rgba(99,102,241,0.25) !important;
    }
    div[data-testid="stButton"] > button:hover {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important; color: #ffffff !important;
    }
    
    /* Anchored Top-Right Download Buttons */
    div[data-testid="stDownloadButton"] { display: flex !important; justify-content: flex-end !important; margin: 0 !important; }
    div[data-testid="stDownloadButton"] > button {
        border-radius: 9999px !important; font-family: 'Outfit', sans-serif !important; font-weight: 700 !important;
        font-size: 12px !important; padding: 8px 18px !important; background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        color: #ffffff !important; border: 1px solid rgba(255,255,255,0.2) !important; white-space: nowrap !important;
    }
    
    /* MATCHING THICKNESS FOR MULTI-FILE COMPARISON CONTAINER */
    div[data-testid="column"]:nth-of-type(3) div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        padding: 8px 10px !important;
        min-height: 125px !important;
        max-height: 130px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        gap: 3px !important;
    }
    
    /* SMALL THIN CLICKABLE CHIPS */
    div[data-testid="column"]:nth-of-type(3) div[data-testid="stButton"] {
        margin: 2px 0 !important;
    }
    div[data-testid="column"]:nth-of-type(3) div[data-testid="stButton"] > button {
        border-radius: 20px !important;
        padding: 4px 12px !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em !important;
        background: rgba(99, 102, 241, 0.08) !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        color: #cbd5e1 !important;
        width: 100% !important;
        height: 28px !important;
        min-height: 28px !important;
        box-shadow: none !important;
        display: flex !important;
        justify-content: flex-start !important;
        text-align: left !important;
        transition: all 0.15s ease !important;
    }
    div[data-testid="column"]:nth-of-type(3) div[data-testid="stButton"] > button:hover {
        background: rgba(99, 102, 241, 0.22) !important;
        border-color: #818cf8 !important;
        color: #ffffff !important;
        transform: none !important;
    }
    
    /* Text Deck Formatting */
    .deck-card {
        background: #0d131f; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        padding: 20px 24px; margin: 10px 0; font-size: 14px; line-height: 1.55;
    }
    .radar-box { background: rgba(15,23,42,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px 16px; margin-bottom: 10px; }
    .radar-zone { padding: 7px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .zone-red { background: rgba(244,63,94,0.12); color: #fb7185; border-left: 3px solid #f43f5e; }
    .zone-green { background: rgba(16,185,129,0.12); color: #34d399; border-left: 3px solid #10b981; }
</style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("<p style='font-size:11px; font-weight:800; color:#818cf8; letter-spacing:0.06em; margin-bottom:4px;'>STUDIO CONTROLS</p>", unsafe_allow_html=True)
    uploaded_logo = st.file_uploader("Upload Brand Logo (PNG/SVG):", type=["png", "jpg", "jpeg", "svg"])
    if uploaded_logo:
        b64 = base64.b64encode(uploaded_logo.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:36px; border-radius:8px; object-fit:contain;">'
    else:
        logo_html = '<div style="background:linear-gradient(135deg, #6366f1 0%, #a855f7 100%); width:38px; height:38px; border-radius:10px; display:flex; align-items:center; justify-content:center;"><span style="font-size:20px;">📈</span></div>'
    
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:15px;">
        {logo_html}
        <div>
            <h4 style="margin:0; font-size:12px; font-weight:800; color:#ffffff; line-height:1.2;">PAID SALES ANALYSER & PRIDICTOR STUDIO</h4>
            <span style="font-size:9px; color:#10b981; font-weight:700;">● FAST FLASH ENGINE</span>
        </div>
    </div>""", unsafe_allow_html=True)
    
    saved_key = cfg.get("gemini_api_key", "")
    key_input = st.text_input("🔑 Google Gemini API Key:", value=saved_key, type="password")
    if key_input and key_input != saved_key: set_cfg("gemini_api_key", key_input)
    api_keys = [k.strip() for k in key_input.split(",") if k.strip()]
    active_key = api_keys[0] if api_keys else ""
    
    selected_category = st.selectbox("Select E-commerce Category:", list(D2C_CATEGORIES.keys()))
    cat_benchmarks = D2C_CATEGORIES[selected_category]
    
    st.markdown(f"""
    <div class="radar-box" style="font-size:11px; line-height:1.6;">
        <b style="color:#a5b4fc;">🇮🇳 Pre-Loaded Indian Benchmarks:</b><br>
        • Avg. CPM: <b>₹{cat_benchmarks['cpm']}</b> | CTR: <b>{cat_benchmarks['ctr']}%</b><br>
        • Web CVR: <b>{cat_benchmarks['cvr']}%</b> | CPC: <b>₹{cat_benchmarks['cpc']}</b><br>
        • Target ROAS: <b>{cat_benchmarks['target_roas']}x</b> | RTO: <b>{cat_benchmarks['rto']}%</b>
    </div>""", unsafe_allow_html=True)
    
    target_aov = st.number_input("Target AOV (Average Order Value ₹):", value=int(cat_benchmarks['aov']), step=100)

# --- 6. PARSER & BULLETPROOF API CALLER ---
def read_spreadsheet_robust(uploaded_file):
    uploaded_file.seek(0)
    name = uploaded_file.name.lower()
    if name.endswith(('.xlsx', '.xls')): return pd.read_excel(uploaded_file)
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    text = None
    for enc in ['utf-8-sig', 'utf-16', 'utf-16-le', 'utf-8', 'latin1', 'cp1252']:
        try: text = raw.decode(enc); break
        except Exception: continue
    if not text: text = raw.decode('utf-8', errors='ignore')
    lines = text.splitlines(); h_idx = 0
    for i, line in enumerate(lines[:10]):
        if any(col in line.lower() for col in ['campaign', 'ad name', 'ad set', 'impressions', 'clicks', 'cost', 'spend', 'conversions']):
            h_idx = i; break
    try: return pd.read_csv(io.StringIO("\n".join(lines[h_idx:])), on_bad_lines='skip')
    except Exception: return pd.read_csv(io.StringIO(text), on_bad_lines='skip', engine='python')

def call_gemini(prompt, parts=[]):
    if not active_key: raise ValueError("Please enter your Gemini API Key in the left sidebar.")
    for k in api_keys:
        client = genai.Client(api_key=k)
        for model in ["gemini-3.8-flash", "gemini-3.5-flash"]:
            try:
                res = client.models.generate_content(model=model, contents=parts + [prompt])
                return res.text
            except Exception as e:
                err = str(e)
                if "429" in err: break
                continue
    raise RuntimeError("API Error. Please check your Gemini API Key / Quota.")

def get_json(text):
    m = re.search(r'\{.*\}', text, re.DOTALL)
    return m.group(0) if m else text

# --- 7. A4 HTML REPORT GENERATOR ---
def html_deck(summary, ads, verdict, period, plat):
    rows = "".join([f"<tr style='border-bottom:1px solid #e2e8f0; font-size:11px;'><td style='padding:8px;'>{a.get('ad_name','')}</td><td style='text-align:center;'>Rs. {a.get('spend',0):,.0f}</td><td style='text-align:center;'><b>{a.get('purchases',0)}</b></td><td style='text-align:center;'>Rs. {a.get('cpa',0):,.0f}</td><td style='text-align:center;'>{a.get('roas',0):.2f}x</td><td style='text-align:center; font-weight:bold; color:{'#e11d48' if 'KILL' in a.get('decision','') else '#059669'};'>{a.get('decision','')}</td></tr>" for a in ads])
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Audit</title><style>@page{{size:A4;margin:12mm;}}body{{font-family:Arial,sans-serif;padding:15px;color:#0f172a;}}.banner{{background:#0f172a;color:white;padding:20px;border-radius:10px;}}.grid{{display:flex;justify-content:space-between;background:#f8fafc;padding:15px;margin:15px 0;border-radius:8px;border:1px solid #e2e8f0;}}table{{width:100%;border-collapse:collapse;margin-top:15px;}}th{{background:#0f172a;color:white;padding:8px;font-size:11px;text-align:left;}}button{{background:#4f46e5;color:white;border:none;padding:10px 20px;border-radius:50px;font-weight:bold;cursor:pointer;margin-bottom:15px;}}@media print{{button{{display:none;}}}}</style></head><body><button onclick='window.print()'>🖨️ Print / Save as PDF (A4)</button><div class='banner'><h2 style='margin:0;'>PAID SALES ANALYSER & PRIDICTOR STUDIO</h2><p style='margin:4px 0 0 0;font-size:11px;opacity:0.8;'>Platform: {plat} | Horizon: {period} | Date: {datetime.now().strftime('%d-%b-%Y')}</p></div><div class='grid'><div>Spend: <b>Rs. {summary.get('total_spend',0):,.0f}</b></div><div>Orders: <b>{summary.get('total_purchases',0)}</b></div><div>CPA: <b>Rs. {summary.get('blended_cpa',0):,.0f}</b></div><div>Sales: <b>Rs. {summary.get('total_revenue',0):,.0f}</b></div><div>ROAS: <b>{summary.get('blended_roas',0):.2f}x</b></div></div><table><thead><tr><th>Ad Name</th><th>Spend</th><th>Orders</th><th>CPA</th><th>ROAS</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table><div style='margin-top:20px;font-size:12px;line-height:1.6;'><b>[+] Winner:</b> {verdict.get('winner','')}<br><br><b>[-] Bleeder:</b> {verdict.get('bleeder','')}<br><br><b>[*] Tonight Action:</b> {verdict.get('scaling_advice','')}<br><br><b>[>] Roadmap:</b> {verdict.get('next_action','')}</div></body></html>"""

# --- 8. TOP NAVBAR ---
st.markdown(f"""
<div class="top-navbar">
    <div style="display:flex; align-items:center; gap:16px;">
        {logo_html}
        <div>
            <h2 style="margin:0; font-size:21px; font-weight:900; color:#ffffff;">
                PAID SALES <span style="background:linear-gradient(135deg, #818cf8 0%, #c084fc 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">ANALYSER</span> & PRIDICTOR STUDIO
            </h2>
            <p style="margin:2px 0 0 0; font-size:11px; color:#94a3b8; font-weight:600;">HYBRID META & GOOGLE ADVERTISING INTELLIGENCE • AUTOMATIC DATE SENSING • A4 DECK SUITE</p>
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:12px;">
        <span style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); color:#34d399; padding:6px 14px; border-radius:20px; font-size:11px; font-weight:800;">🟢 LIVE DETECTOR</span>
        <span style="background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.3); color:#a5b4fc; padding:6px 14px; border-radius:20px; font-size:11px; font-weight:800;">GEMINI 3.8 FLASH</span>
    </div>
</div>""", unsafe_allow_html=True)

# --- 9. WORKSPACE TABS ---
nav_tab1, nav_tab2, nav_tab3 = st.tabs([
    "📸 Vision & Report Auditor (Meta + Google Auto-Detect)",
    "🎯 Ad Copy Studio & Financial Simulator (Manual + A4 PDF)",
    "🎨 Creative Scoring & Safe-Zone Studio (Meta & Google Rules)"
])

# ==============================================================================
# TAB 1: VISION & REPORT AUDITOR
# ==============================================================================
with nav_tab1:
    st.markdown("#### 📥 Hybrid Ingestion & Comparison Suite")
    st.caption("Upload screenshots or CSV/Excel reports from Meta or Google Ads:")

    in_col1, in_col2, in_col3 = st.columns([1.1, 1.1, 1.2])
    with in_col1:
        up_imgs = st.file_uploader("🖼️ Meta / Google Screenshots", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    with in_col2:
        up_csvs = st.file_uploader("📊 Exported CSV or Excel Files", type=["csv", "xlsx", "xls"], accept_multiple_files=True)
    with in_col3:
        st.markdown("<p style='font-size:14px; font-weight:600; margin-bottom:8px;'>⚡ Multi-File Comparison</p>", unsafe_allow_html=True)
        # NATIVE CONTAINER MATCHING DROPZONE THICKNESS WITH SLIM CLICKABLE CHIPS
        with st.container(border=True):
            btn_cmp_dates = st.button("📅 Date Horizon (1D vs 7D vs 30D)", key="cmp1")
            btn_cmp_platforms = st.button("⚔️ Meta vs Google Cross-Audit", key="cmp2")
            btn_cmp_fatigue = st.button("📈 Creative Fatigue & Delta", key="cmp3")

    if up_imgs or up_csvs:
        _, c_btn1, _ = st.columns([1, 2, 1])
        with c_btn1:
            btn_audit = st.button("🚀 EXECUTE AUTO-DETECTION & AUDIT")

        if btn_audit:
            with st.spinner("🤖 Analyzing metrics and detecting horizon with live Gemini Flash..."):
                try:
                    payload = []
                    if up_imgs:
                        for f in up_imgs:
                            buf = io.BytesIO(); Image.open(f).convert('RGB').save(buf, format='JPEG')
                            payload.append(types.Part.from_bytes(data=buf.getvalue(), mime_type='image/jpeg'))
                    sheet_txt = ""
                    if up_csvs:
                        for c in up_csvs:
                            sheet_txt += f"\nData from {c.name}:\n{read_spreadsheet_robust(c).head(80).to_csv(index=False)}"

                    prompt = f"""
                    You are an Elite Senior Performance Marketer for D2C Brand in category: '{selected_category}' (AOV: ₹{target_aov}).
                    Analyze advertising inputs (Screenshots / Spreadsheets). {sheet_txt}
                    Return STRICT JSON:
                    {{
                        "detected_platform": "Meta Ads / Google Ads / Hybrid",
                        "detected_timeframe": "1D / 7D / 15D / 30D / 90D",
                        "summary": {{"total_spend": 0.0, "total_purchases": 0, "total_revenue": 0.0, "blended_cpa": 0.0, "blended_roas": 0.0}},
                        "ads": [{{"ad_name": "Name", "spend": 0.0, "purchases": 0, "revenue": 0.0, "cpa": 0.0, "roas": 0.0, "cpc": 0.0, "ctr": 0.0, "decision": "KILL or SCALE or WATCH", "reason": "short reason in small letters"}}],
                        "audit_verdict": {{"winner": "winner summary", "bleeder": "bleeder summary", "scaling_advice": "scaling advice", "next_action": "roadmap"}}
                    }}
                    """
                    st.session_state["auto_data"] = json.loads(get_json(call_gemini(prompt, payload)))
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

        # COMPARISON BUTTONS HANDLER (AUTO-SYNCED TO DIRECTIVES)
        if btn_cmp_dates or btn_cmp_platforms or btn_cmp_fatigue:
            c_label = "Date Horizon Compare" if btn_cmp_dates else ("Meta vs Google" if btn_cmp_platforms else "Fatigue & Delta")
            with st.spinner(f"Running {c_label} across files..."):
                try:
                    payload = []
                    if up_imgs:
                        for f in up_imgs:
                            buf = io.BytesIO(); Image.open(f).convert('RGB').save(buf, format='JPEG')
                            payload.append(types.Part.from_bytes(data=buf.getvalue(), mime_type='image/jpeg'))
                    sheet_txt = ""
                    if up_csvs:
                        for c in up_csvs: sheet_txt += f"\nFile {c.name}:\n{read_spreadsheet_robust(c).head(80).to_csv(index=False)}"

                    cmp_prompt = f"""
                    You are an Elite Media Buyer for Sneha B. Compare these advertising inputs.
                    Comparison Mode: {c_label}. Data: {sheet_txt}.
                    Write a concise, decisive comparative audit in small letters (sentence case):
                    - Date/Channel delta analysis (spend and CPA trajectory)
                    - What to kill immediately vs what to scale.
                    """
                    st.session_state["cmp_report"] = call_gemini(cmp_prompt, payload)
                    st.session_state["cmp_type"] = c_label
                    st.success(f"✓ {c_label} synced to Senior Media Buyer Directives!")
                    st.rerun()
                except Exception as ce: st.error(f"Error: {ce}")

    # Display Dashboard
    if "auto_data" in st.session_state:
        d = st.session_state["auto_data"]
        summ, ads, verd = d.get("summary", {}), d.get("ads", []), d.get("audit_verdict", {})
        plat, period = d.get("detected_platform", "Meta Ads"), d.get("detected_timeframe", "Auto")

        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        t_c1, t_c2 = st.columns([1.6, 1.4])
        with t_c1:
            st.markdown(f"<span class='pill-blue'>{plat}</span> <span class='pill-green'>📅 Period: {period}</span>", unsafe_allow_html=True)
        with t_c2:
            st.download_button("📄 Export A4 Audit Deck", html_deck(summ, ads, verd, period, plat), f"Audit_{datetime.now().strftime('%d_%b')}.html", "text/html")

        # KPI Metrics
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.markdown(f"<div class='kpi-card'><div class='kpi-lbl'>Total Spend</div><div class='kpi-val'>₹{summ.get('total_spend',0):,.0f}</div></div>", unsafe_allow_html=True)
        k2.markdown(f"<div class='kpi-card'><div class='kpi-lbl'>Orders</div><div class='kpi-val'>{int(summ.get('total_purchases',0))}</div></div>", unsafe_allow_html=True)
        k3.markdown(f"<div class='kpi-card'><div class='kpi-lbl'>Blended CPA</div><div class='kpi-val'>₹{summ.get('blended_cpa',0):,.0f}</div></div>", unsafe_allow_html=True)
        k4.markdown(f"<div class='kpi-card'><div class='kpi-lbl'>Revenue</div><div class='kpi-val'>₹{summ.get('total_revenue',0):,.0f}</div></div>", unsafe_allow_html=True)
        k5.markdown(f"<div class='kpi-card'><div class='kpi-lbl'>ROAS</div><div class='kpi-val' style='color:#34d399;'>{summ.get('blended_roas',0):.2f}x</div></div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        sub1, sub2, sub3, sub4, sub5 = st.tabs(["📋 Action Matrix", "📈 Spend vs Revenue Chart", "🔮 Horizon Forecast", "🧠 Senior Media Buyer Directives", "🚀 ROAS Scaling Blueprint (3X-7X)"])

        with sub1:
            if ads: st.dataframe(pd.DataFrame(ads), use_container_width=True)
        with sub2:
            if ads:
                st.plotly_chart(px.bar(pd.DataFrame(ads), x="ad_name", y=["spend", "revenue"], barmode="group", color_discrete_map={"spend":"#f43f5e","revenue":"#10b981"}, template="plotly_dark"), use_container_width=True)
        with sub3:
            st.markdown("#### 🔮 Horizon Forecast (1D, 3D, 7D, 15D, 30D, 90D)")
            b_spend = max(float(summ.get('total_spend', 4500)), 1500.0)
            b_cpa = max(float(summ.get('blended_cpa', 650)), 400.0)
            f_rows = []
            for d_cnt, lbl in [(1, "1D Tonight"), (3, "3D Short-Term"), (7, "7D Weekly"), (15, "15D Run"), (30, "30D Month"), (90, "90D Scale")]:
                tot_sp = b_spend * d_cnt; ords = int(tot_sp / b_cpa); rev = ords * target_aov
                f_rows.append({"Period": lbl, "Spend": f"₹{tot_sp:,.0f}", "Orders": f"{ords} Orders", "GMV": f"₹{rev:,.0f}", "ROAS": f"{round(rev/tot_sp, 2)}x", "Stock Buffer": f"{int(ords*1.1)} Units"})
            st.dataframe(pd.DataFrame(f_rows), use_container_width=True)
        with sub4:
            if "cmp_report" in st.session_state:
                st.markdown(f"<div style='background:#0d1527; padding:16px; border-radius:12px; border-left:4px solid #818cf8; margin-bottom:14px;'><b style='color:#a5b4fc;'>📊 Auto-Synced Comparative Directive ({st.session_state.get('cmp_type')}):</b><br><span style='font-size:13px; color:#cbd5e1;'>{st.session_state['cmp_report']}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='deck-card'><b>[+] Top Winner:</b><br>{verd.get('winner','')}<br><br><b>[-] Bleeder:</b><br>{verd.get('bleeder','')}<br><br><b>[*] Tonight Action:</b><br>{verd.get('scaling_advice','')}<br><br><b>[>] Roadmap:</b><br>{verd.get('next_action','')}</div>", unsafe_allow_html=True)
        with sub5:
            st.markdown("#### 🚀 Target ROAS Multiplier Engine (3X, 4X, 5X, 7X)")
            tier = st.radio("Select Milestone:", ["3X ROAS", "4X ROAS", "5X ROAS", "7X ROAS"], horizontal=True)
            r_target = float(tier.split("X")[0]); r_cpa = round(target_aov / r_target, 0)
            st.markdown(f"<div class='deck-card'>Active Channel: <b>{plat}</b> | Target ROAS: <b>{r_target}x</b> | Max CPA Target: <b>₹{r_cpa:,.0f}</b><br><br>• <b>1D Action:</b> Stop ads spending >1x AOV with 0 sales. Set URL expansion OFF.<br>• <b>3D Action:</b> Apply negative keyword shield & isolate top winning creatives into dedicated CBO.<br>• <b>7D Action:</b> Lock Target ROAS constraint at {r_target*100:.0f}% with budget scaling of +20% every 48h.</div>", unsafe_allow_html=True)

# ==============================================================================
# TAB 2: AD COPY STUDIO & ARCHITECTURE
# ==============================================================================
with nav_tab2:
    st.markdown("#### 🎯 Financial Plan & Ad Copy Studio")
    c1, c2, c3 = st.columns(3)
    with c1:
        c_bud = st.number_input("💵 Daily Budget (₹):", value=5000, step=500)
        c_rev = st.number_input("🎯 Target Revenue (₹):", value=20000, step=1000)
        c_aov = st.number_input("📦 Product AOV (₹):", value=int(target_aov), step=100)
    with c2:
        c_loc = st.selectbox("📍 Target Geography:", ["🌴 South India Tier-1 & Tier-2", "🇮🇳 Pan-India (All India Broad)", "🏙️ Tier-1 Metros", "📈 Top 25 Tier-2 Hubs"])
        c_off = st.selectbox("⚡ Active Offer:", ["🛍️ Buy Any 2 & Get 10% OFF + Flat 10% on UPI", "🎁 Buy 1 Get 1 FREE (BOGO)", "⚡ Flat 15% Instant OFF", "🏷️ Buy Any 2 for ₹1,999"])
    with c3:
        b_name = st.text_input("🏷️ Brand Title:", value="Sneha B")
        p_choice = st.selectbox("🎯 Target Platform:", ["📱 Meta Ads (Instagram & Facebook 3:2:2)", "🔍 Google Ads (Search & Performance Max)", "🚀 Omnichannel Suite"])

    # Calculations
    t_roas = c_rev / c_bud if c_bud > 0 else 0
    t_ords = int(c_rev / c_aov) if c_aov > 0 else 0
    t_cpa = c_bud / t_ords if t_ords > 0 else 0
    req_clk = int(t_ords / (cat_benchmarks['cvr'] / 100))
    req_view = int(req_clk / (cat_benchmarks['ctr'] / 100))

    f1, f2, f3, f4, f5 = st.columns(5)
    f1.metric("Target ROAS", f"{t_roas:.2f}x")
    f2.metric("Target Orders", f"{t_ords} / day")
    f3.metric("Max CPA", f"₹{t_cpa:,.0f}")
    f4.metric("Clicks Needed", f"{req_clk:,}")
    f5.metric("Views Needed", f"{req_view:,}")

    _, c_btn2, _ = st.columns([1, 2, 1])
    with c_btn2:
        btn_gen_copy = st.button(f"⚡ GENERATE ASSETS FOR {p_choice.split(' ')[1].upper()}")

    if btn_gen_copy:
        with st.spinner("Generating step-by-step settings and direct-response copy..."):
            try:
                p_text = f"""
                You are an Elite Media Buyer for {selected_category}. Brand: {b_name}, Geo: {c_loc}, AOV: ₹{c_aov}, Offer: {c_off}.
                Target: {t_ords} orders/day at ₹{c_bud} budget (ROAS: {t_roas:.2f}x, Max CPA: ₹{t_cpa:.0f}). Platform: {p_choice}.
                
                Produce distinct sections:
                ### 🏗️ SECTION 1: STEP-BY-STEP CAMPAIGN ARCHITECTURE
                - Exact Campaign & Ad Set settings (Bidding, Budget split, Audiences, Placements, Kill/Scale rules).
                
                ### 📝 SECTION 2: AD COPY & HEADLINES SUITE
                - If Meta: 3 Viral Video Hooks, 2 Primary Texts, 2 Headlines (<30 chars), 1 Description, CTA.
                - If Google: 15 RSA Headlines (<30 chars with count), 5 Long Headlines (<90 chars), 4 Descriptions (<90 chars), Search Themes, Negative Keywords.
                """
                st.session_state["ad_copy_out"] = call_gemini(p_text)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

    if "ad_copy_out" in st.session_state:
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        st.download_button("📄 Export A4 Media Plan (PDF)", f"<html><body><pre>{st.session_state['ad_copy_out']}</pre></body></html>", f"{b_name}_Plan.html", "text/html")
        st.markdown(f"<div class='deck-card'>{st.session_state['ad_copy_out']}</div>", unsafe_allow_html=True)

# ==============================================================================
# TAB 3: CREATIVE SCORING & SAFE-ZONE STUDIO
# ==============================================================================
with nav_tab3:
    st.markdown("#### 🎨 Creative Scoring & Safe-Zone Studio")
    cr_c1, cr_c2 = st.columns([2, 1])
    with cr_c1:
        cr_file = st.file_uploader("📤 Upload Creative (Photo or Video):", type=["png", "jpg", "jpeg", "webp", "mp4", "mov"])
    with cr_c2:
        placement = st.selectbox("🎯 Target Placement:", ["📱 9:16 Reels & Stories", "🖼️ 4:5 Feed Portrait", "⏹️ 1:1 Square Feed", "🔍 Google PMax Asset"])

    if cr_file:
        is_vid = cr_file.name.split('.')[-1].lower() in ['mp4', 'mov']
        p_col, i_col = st.columns([1, 1.3])
        with p_col:
            st.markdown("##### 👁️ Preview")
            if is_vid: st.video(cr_file)
            else: st.image(Image.open(cr_file), use_container_width=True)
        with i_col:
            st.markdown("##### 📐 Technical Specs & Safe-Zone Radar")
            st.markdown(f"""
            <div class="radar-box">
                <span class="kpi-lbl">Asset Identifier: {cr_file.name[:25]}</span><br>
                • <b>Safe-Zone Rule:</b> Keep top 14% and bottom 20% clear of critical text/offers.<br>
                • <b>Mute Readability:</b> 70%+ users watch without sound; bold text overlay required.
            </div>
            <div class="radar-box" style="margin-bottom:12px;">
                <span class="kpi-lbl">⚡ D2C Conversion Pre-Check</span><br>
                • <b>Thumbstop Window:</b> First 2s must interrupt scroll.<br>
                • <b>Contrast Rule:</b> Text must have high-contrast background pill.
            </div>""", unsafe_allow_html=True)

            btn_audit_cr = st.button("🚀 AUDIT CREATIVE COMPLIANCE & SCORE PERFORMANCE")

        if btn_audit_cr:
            with st.spinner("Analyzing creative composition and safe-zone clearance..."):
                try:
                    payload = []
                    if is_vid:
                        cr_file.seek(0)
                        payload.append(types.Part.from_bytes(data=cr_file.read(), mime_type=f"video/{cr_file.name.split('.')[-1].lower()}"))
                    else:
                        buf = io.BytesIO(); Image.open(cr_file).convert('RGB').save(buf, format='JPEG')
                        payload.append(types.Part.from_bytes(data=buf.getvalue(), mime_type='image/jpeg'))

                    prompt = f"""
                    Evaluate this creative for D2C {selected_category}. Placement: {placement}, AOV: ₹{target_aov}.
                    Score 1-10 (compress toward 5-7). Keep explanations concise in small letters.
                    Return STRICT JSON:
                    {{
                        "overall_score": 6.8, "redesigned_score": 8.4, "safe_zone_verdict": "pass",
                        "scores": {{"hook_strength": 6.5, "safe_zone_clearance": 7.0, "visual_clarity": 7.2, "roas_potential": 6.8}},
                        "safe_zone_critique": "brief critique in small letters",
                        "roas_improvements": ["lever 1", "lever 2", "lever 3"]
                    }}
                    """
                    st.session_state["cr_eval"] = json.loads(get_json(call_gemini(prompt, payload)))
                    st.session_state["cr_name"] = cr_file.name
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

    if "cr_eval" in st.session_state:
        ev = st.session_state["cr_eval"]
        sc = ev.get("scores", {})
        st.markdown(f"##### 📊 Grade: `{st.session_state.get('cr_name')}` | Score: **{ev.get('overall_score')} / 10**")
        st.markdown(f"<div class='deck-card'><b>Safe-Zone Critique:</b> {ev.get('safe_zone_critique','')}<br><br><b>Key ROAS Improvements:</b><br>• " + "<br>• ".join(ev.get("roas_improvements", [])) + "</div>", unsafe_allow_html=True)

        _, c_btn3, _ = st.columns([1, 2, 1])
        with c_btn3:
            btn_redesign = st.button("✨ REDESIGN TEXT & OPTIMIZE FOR MAXIMUM SCORE")

        if btn_redesign:
            with st.spinner("Re-engineering on-screen text and hooks..."):
                try:
                    rd_prompt = f"Redesign on-screen text, viral hooks, and copy for this {selected_category} creative. Keep directives concise in small letters."
                    st.session_state["cr_redesign"] = call_gemini(rd_prompt)
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

        if "cr_redesign" in st.session_state:
            st.markdown(f"<div class='deck-card' style='border-left:4px solid #10b981;'>{st.session_state['cr_redesign']}</div>", unsafe_allow_html=True)
