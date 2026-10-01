import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import os
import re
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import io
import base64
from datetime import datetime
from google import genai
from google.genai import types

# --- PAGE CONFIGURATION (START COLLAPSED) ---
st.set_page_config(
    page_title="PAID SALES ANALYSER & PRIDICTOR STUDIO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- JAVASCRIPT: FORCE AUTO-COLLAPSE ON INITIAL LOAD ---
components.html(
    """
    <script>
    const forceCollapse = () => {
        const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
        const collapseBtn = window.parent.document.querySelector('[data-testid="stSidebarCollapseButton"] button');
        if (sidebar && sidebar.getAttribute("aria-expanded") === "true" && collapseBtn) {
            collapseBtn.click();
        }
    };
    setTimeout(forceCollapse, 250);
    </script>
    """,
    height=0,
    width=0
)

# --- LOCAL CONFIG PERSISTENCE ---
CONFIG_FILE = "config.json"

def load_local_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_local_config(key, val):
    cfg = load_local_config()
    cfg[key] = val
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

persisted_config = load_local_config()

# Clean deprecated models from local config
if persisted_config.get("cached_models"):
    cleaned_m = [m for m in persisted_config["cached_models"] if not any(x in m for x in ["2.0", "1.5", "tts", "audio"])]
    if cleaned_m:
        persisted_config["cached_models"] = cleaned_m
        save_local_config("cached_models", cleaned_m)

# --- D2C CATEGORY BENCHMARKS (INDIAN MARKET PRESETS) ---
D2C_CATEGORIES = {
    "👗 Women's Western & Contemporary Wear": {
        "aov": 2800, "cpm": 220, "ctr": 2.4, "cvr": 2.2, "cpc": 9.16, "rto": 22, "target_roas": 3.8,
        "usp_prompt": "Breathable pure cotton, flattering inclusive fits, functional deep pockets, everyday luxury."
    },
    "🥻 Ethnic Wear, Kurtis & Sarees": {
        "aov": 1850, "cpm": 180, "ctr": 2.6, "cvr": 2.8, "cpc": 6.92, "rto": 28, "target_roas": 3.5,
        "usp_prompt": "Festive elegance, authentic weaves, rich drape, premium stitching."
    },
    "👕 Men's Casual Wear & Streetwear": {
        "aov": 1650, "cpm": 190, "ctr": 1.9, "cvr": 2.0, "cpc": 10.0, "rto": 26, "target_roas": 3.2,
        "usp_prompt": "Heavyweight cotton, minimalist oversized fit, durable stitch."
    },
    "💍 Jewellery & Fashion Accessories": {
        "aov": 1400, "cpm": 160, "ctr": 2.8, "cvr": 3.0, "cpc": 5.71, "rto": 16, "target_roas": 3.8,
        "usp_prompt": "Anti-tarnish, waterproof, hypoallergenic, luxury aesthetic."
    },
    "👠 Footwear & Shoes": {
        "aov": 2200, "cpm": 240, "ctr": 1.8, "cvr": 1.9, "cpc": 13.3, "rto": 32, "target_roas": 3.4,
        "usp_prompt": "Orthopedic arch support, feather-light comfort, all-day wear."
    },
    "💄 Beauty, Skincare & Cosmetics": {
        "aov": 1150, "cpm": 260, "ctr": 2.1, "cvr": 3.2, "cpc": 12.3, "rto": 14, "target_roas": 3.0,
        "usp_prompt": "Clean toxin-free formulation, dermatologically tested, visible glow."
    },
    "🌿 Health, Wellness & Nutrition": {
        "aov": 1500, "cpm": 320, "ctr": 1.6, "cvr": 2.6, "cpc": 20.0, "rto": 12, "target_roas": 2.8,
        "usp_prompt": "Certified organic, clinically proven ingredients, zero sugar."
    },
    "🏡 Home Decor, Furnishing & Kitchen": {
        "aov": 2400, "cpm": 210, "ctr": 1.7, "cvr": 1.8, "cpc": 12.3, "rto": 20, "target_roas": 3.2,
        "usp_prompt": "Artisanal handcrafted, modern aesthetic, durable craftsmanship."
    },
    "🍫 Gourmet Food & Healthy Snacks": {
        "aov": 950, "cpm": 180, "ctr": 2.5, "cvr": 3.5, "cpc": 7.2, "rto": 10, "target_roas": 2.6,
        "usp_prompt": "Zero preservatives, fresh small-batch roasting, 100% natural."
    },
    "🎧 Consumer Tech & Gadgets": {
        "aov": 2600, "cpm": 280, "ctr": 1.5, "cvr": 1.7, "cpc": 18.6, "rto": 24, "target_roas": 3.5,
        "usp_prompt": "Fast charging, premium noise isolation, 1-year replacement warranty."
    }
}

# --- ULTRA SAAS DESIGN SYSTEM WITH FLAWLESS CENTERED BUTTONS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, h4, h5, .kpi-val, .top-navbar h2, .top-navbar h3, th {
        font-family: 'Outfit', sans-serif !important;
        letter-spacing: -0.025em !important;
    }
    
    .stApp {
        background: radial-gradient(circle at 15% 15%, #0f172a 0%, #06090f 90%);
        color: #f8fafc;
    }
    
    [data-testid="stSidebar"] {
        background: #080c14 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%) !important;
        border: 1px solid rgba(99, 102, 241, 0.4) !important;
        border-radius: 10px !important;
        padding: 6px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4) !important;
        transition: all 0.25s ease !important;
    }
    [data-testid="stSidebarCollapsedControl"]:hover {
        transform: scale(1.12);
        border-color: #818cf8 !important;
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.6) !important;
    }
    
    .top-navbar {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.5) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 16px;
        padding: 16px 22px;
        margin-bottom: 22px;
        backdrop-filter: blur(16px);
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }
    
    /* BUTTON PILL TABS */
    div[data-testid="stTabs"] {
        margin-top: 5px !important;
    }
    div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
        gap: 8px !important;
        background: rgba(15, 23, 42, 0.85) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 5px 8px !important;
        border-radius: 9999px !important;
        margin-bottom: 24px !important;
        display: inline-flex !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35) !important;
    }
    div[data-testid="stTabs"] button[role="tab"] {
        border-radius: 9999px !important;
        padding: 9px 24px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        color: #94a3b8 !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        background: transparent !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div[data-testid="stTabs"] button[role="tab"]:hover {
        color: #ffffff !important;
        background: rgba(255, 255, 255, 0.06) !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: #ffffff !important;
        border: none !important;
        outline: none !important;
        box-shadow: 0 4px 18px rgba(99, 102, 241, 0.5) !important;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
    div[data-testid="stTabs"] [data-baseweb="tab-border"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0px !important;
    }
    
    .kpi-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.35) 0%, rgba(15, 23, 42, 0.6) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 8px 20px -4px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
        transition: all 0.2s ease;
        height: 100%;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .kpi-lbl {
        font-size: 10px;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: #94a3b8;
        font-weight: 700;
    }
    .kpi-val {
        font-size: 26px;
        font-weight: 900;
        color: #ffffff;
        margin: 5px 0;
        letter-spacing: -0.02em;
    }
    .kpi-pill {
        font-size: 11px;
        display: inline-block;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 700;
    }
    .pill-green { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .pill-red { background: rgba(244, 63, 94, 0.15); color: #fb7185; }
    .pill-blue { background: rgba(99, 102, 241, 0.15); color: #818cf8; }
    
    .bench-card {
        background: rgba(15, 23, 42, 0.4);
        border: 1px dashed rgba(255, 255, 255, 0.12);
        border-radius: 10px;
        padding: 12px 14px;
        font-size: 11px;
        line-height: 1.6;
    }
    
    /* 100% BULLETPROOF CENTER ALIGNMENT FOR ALL ACTION BUTTONS */
    div[data-testid="stButton"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        text-align: center !important;
        margin: 12px auto !important;
    }
    div[data-testid="stButton"] > button {
        display: inline-flex !important;
        justify-content: center !important;
        align-items: center !important;
        margin: 0 auto !important;
        border-radius: 9999px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        letter-spacing: 0.03em !important;
        padding: 10px 30px !important;
        background: rgba(99, 102, 241, 0.14) !important;
        color: #a5b4fc !important;
        border: 1.5px solid #6366f1 !important;
        box-shadow: 0 4px 18px rgba(99, 102, 241, 0.25) !important;
        transition: all 0.25s ease !important;
        width: auto !important;
    }
    div[data-testid="stButton"] > button:hover {
        transform: translateY(-1px) !important;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: #ffffff !important;
        border-color: #818cf8 !important;
        box-shadow: 0 6px 24px rgba(99, 102, 241, 0.55) !important;
    }
    
    /* ANCHOR DOWNLOAD BUTTONS TO TOP-RIGHT ONLY */
    div[data-testid="stDownloadButton"] {
        display: flex !important;
        justify-content: flex-end !important;
        align-items: center !important;
        width: 100% !important;
        margin: 0 !important;
    }
    div[data-testid="stDownloadButton"] > button {
        border-radius: 9999px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        letter-spacing: 0.02em !important;
        padding: 8px 18px !important;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.35) !important;
        white-space: nowrap !important;
        width: auto !important;
        margin: 0 !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.55) !important;
    }
    
    /* COMPACT, CLEAN TYPOGRAPHY */
    .deck-card {
        background: #0d131f;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px 24px;
        margin-top: 10px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .deck-card h2, .deck-card h3, .deck-card h4 {
        margin-top: 16px !important;
        margin-bottom: 8px !important;
        color: #818cf8 !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 800 !important;
        line-height: 1.3 !important;
    }
    .deck-card p {
        margin-top: 2px !important;
        margin-bottom: 8px !important;
        line-height: 1.5 !important;
    }
    .deck-card ul, .deck-card ol {
        margin-top: 4px !important;
        margin-bottom: 10px !important;
        padding-left: 20px !important;
    }
    .deck-card li {
        margin-top: 3px !important;
        margin-bottom: 5px !important;
        line-height: 1.5 !important;
    }
    
    .roas-milestone-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.5) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
    }
    
    .roas-inactive-card {
        background: rgba(15, 23, 42, 0.3);
        border: 1px dashed rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        opacity: 0.5;
    }
    
    /* RADAR & SPEC WIDGET STYLING */
    .radar-box {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .radar-zone {
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 600;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .zone-red { background: rgba(244, 63, 94, 0.12); color: #fb7185; border-left: 3px solid #f43f5e; }
    .zone-green { background: rgba(16, 185, 129, 0.12); color: #34d399; border-left: 3px solid #10b981; }
    
    @media (max-width: 768px) {
        .top-navbar {
            flex-direction: column;
            gap: 12px;
            align-items: flex-start;
            padding: 14px;
        }
        div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
            border-radius: 16px !important;
            flex-wrap: wrap !important;
        }
        div[data-testid="stTabs"] button[role="tab"] {
            padding: 7px 16px !important;
            font-size: 11px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("<p style='font-size:11px; font-weight:800; color:#818cf8; letter-spacing:0.06em; margin-bottom:4px;'>STUDIO CONTROLS</p>", unsafe_allow_html=True)
    
    uploaded_logo = st.file_uploader("Upload Brand Logo (PNG/SVG):", type=["png", "jpg", "jpeg", "svg"])
    
    if uploaded_logo is not None:
        logo_bytes = uploaded_logo.read()
        logo_b64 = base64.b64encode(logo_bytes).decode()
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:36px; width:auto; border-radius:8px; object-fit:contain;">'
    else:
        logo_html = '<div style="background:linear-gradient(135deg, #6366f1 0%, #a855f7 100%); width:38px; height:38px; border-radius:10px; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 15px rgba(99,102,241,0.4);"><span style="font-size:20px;">📈</span></div>'
    
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin-top:5px; margin-bottom:15px;">
        {logo_html}
        <div>
            <h4 style="margin:0; font-size:12px; font-weight:800; color:#ffffff; line-height:1.2;">PAID SALES ANALYSER & PRIDICTOR STUDIO</h4>
            <span style="font-size:9px; color:#10b981; font-weight:700;">● FAST FLASH ENGINE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    saved_key = persisted_config.get("gemini_api_key", "")
    raw_api_key_input = st.text_input("🔑 Google Gemini API Key:", value=saved_key, type="password")
    
    if raw_api_key_input and raw_api_key_input != saved_key:
        save_local_config("gemini_api_key", raw_api_key_input)
    
    api_key_pool = [k.strip() for k in raw_api_key_input.split(",") if k.strip()]
    active_api_key = api_key_pool[0] if api_key_pool else ""
    
    selected_gemini_model = "gemini-3.8-flash"
    
    st.markdown("---")
    st.markdown("<p style='font-size:11px; font-weight:800; color:#94a3b8; letter-spacing:0.05em; text-transform:uppercase;'>D2C Category & Benchmarks</p>", unsafe_allow_html=True)
    selected_category = st.selectbox("Select E-commerce Category:", list(D2C_CATEGORIES.keys()))
    
    cat_benchmarks = D2C_CATEGORIES[selected_category]
    
    st.markdown(f"""
    <div class="bench-card">
        <b style="color:#a5b4fc;">🇮🇳 Pre-Loaded Indian Benchmarks:</b><br>
        • Avg. CPM: <b>₹{cat_benchmarks['cpm']}</b><br>
        • Link CTR: <b>{cat_benchmarks['ctr']}%</b> | CPC: <b>₹{cat_benchmarks['cpc']}</b><br>
        • Web CVR: <b>{cat_benchmarks['cvr']}%</b> | RTO: <b>{cat_benchmarks['rto']}%</b><br>
        • Target ROAS: <b>{cat_benchmarks['target_roas']}x</b>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    target_aov = st.number_input("Target AOV (Average Order Value ₹):", value=int(cat_benchmarks['aov']), step=100)
    kill_threshold = st.number_input("Kill Threshold (Max Zero-Sale Spend ₹):", value=int(target_aov * 0.5), step=100)

def extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group(0) if match else text

# --- ROBUST CSV & EXCEL PARSER ---
def read_spreadsheet_robust(uploaded_file):
    uploaded_file.seek(0)
    file_name = uploaded_file.name.lower()
    
    if file_name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(uploaded_file)
    
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    
    text = None
    for enc in ['utf-8-sig', 'utf-16', 'utf-16-le', 'utf-8', 'latin1', 'cp1252']:
        try:
            text = raw_bytes.decode(enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
            
    if text is None:
        text = raw_bytes.decode('utf-8', errors='ignore')
        
    lines = text.splitlines()
    header_idx = 0
    for idx, line in enumerate(lines[:10]):
        lower_line = line.lower()
        if any(col in lower_line for col in ['campaign', 'ad name', 'ad set', 'impressions', 'clicks', 'cost', 'spend', 'conversions']):
            header_idx = idx
            break
            
    clean_csv_str = "\n".join(lines[header_idx:])
    
    try:
        df = pd.read_csv(io.StringIO(clean_csv_str), on_bad_lines='skip')
    except Exception:
        df = pd.read_csv(io.StringIO(text), on_bad_lines='skip', engine='python')
        
    return df

# --- PERMANENT BULLETPROOF CALLER (NO 1.5, NO 2.0, NO TTS) ---
def call_gemini_dynamic(prompt, parts_payload=[]):
    if not api_key_pool:
        raise ValueError("Please enter your Gemini API Key in the left sidebar.")
    
    last_err = None
    for k in api_key_pool:
        client = genai.Client(api_key=k)
        
        live_models = []
        try:
            for m in client.models.list():
                actions = getattr(m, 'supported_actions', []) or []
                if 'generateContent' in actions:
                    c_name = m.name.replace('models/', '')
                    if not any(bad in c_name for bad in ['tts', 'audio', 'image', 'embed', 'realtime', '2.0', '1.5']):
                        live_models.append(c_name)
        except Exception:
            pass
        
        candidate_models = list(dict.fromkeys(["gemini-3.8-flash"] + live_models + ["gemini-3.5-flash"]))
        
        for model_id in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=parts_payload + [prompt]
                )
                return response.text
            except Exception as e:
                err_str = str(e)
                last_err = e
                if "404" in err_str:
                    continue
                elif "429" in err_str:
                    break
                else:
                    continue
                    
    raise last_err if last_err else RuntimeError("Could not connect to Gemini. Please check your API Key.")

# --- A4 AUDIT DECK GENERATOR ---
def generate_audit_html_report(summary, ads_list, verdict, detected_period, detected_plat):
    ads_rows_html = ""
    for ad in ads_list:
        dec = ad.get('decision', 'STABLE')
        dec_color = "#e11d48" if "KILL" in dec.upper() else ("#059669" if "SCALE" in dec.upper() else "#475569")
        ads_rows_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0; font-size: 11px;">
            <td style="padding: 10px 8px; font-weight:600;">{ad.get('ad_name', '')}</td>
            <td style="padding: 10px 8px; text-align: center;">Rs. {ad.get('spend', 0):,.0f}</td>
            <td style="padding: 10px 8px; text-align: center; font-weight: bold;">{ad.get('purchases', 0)}</td>
            <td style="padding: 10px 8px; text-align: center;">Rs. {ad.get('cpa', 0):,.0f}</td>
            <td style="padding: 10px 8px; text-align: center; font-weight:600;">{ad.get('roas', 0):.2f}x</td>
            <td style="padding: 10px 8px; text-align: center; color: {dec_color}; font-weight: 800;">{dec}</td>
        </tr>
        """
        
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>PAID SALES ANALYSER & PRIDICTOR STUDIO -- Growth Audit</title>
        <style>
            @page {{ size: A4; margin: 12mm; }}
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #0f172a; margin: 0; padding: 15px; }}
            .banner {{ background: #0f172a; color: white; padding: 22px; border-radius: 10px; }}
            .kpi-row {{ display: flex; justify-content: space-between; margin: 18px 0; background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; }}
            .kpi-c {{ text-align: center; }}
            .kpi-c .t {{ font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; }}
            .kpi-c .v {{ font-size: 22px; font-weight: 800; margin-top: 4px; color: #0f172a; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th {{ background: #0f172a; color: white; padding: 9px 8px; font-size: 11px; text-align: left; text-transform: uppercase; }}
            .sec {{ font-size: 13px; font-weight: 800; margin-top: 22px; border-bottom: 2px solid #0f172a; padding-bottom: 4px; }}
            .v-box {{ margin-top: 8px; padding: 12px 16px; border-left: 4px solid #6366f1; background: #f8fafc; font-size: 12px; line-height: 1.5; }}
            .p-btn {{ background: #4f46e5; color: white; border: none; padding: 10px 20px; border-radius: 50px; font-size: 13px; font-weight: 700; cursor: pointer; margin-bottom: 15px; }}
            @media print {{ .p-btn {{ display: none; }} }}
        </style>
    </head>
    <body>
        <button class="p-btn" onclick="window.print()">🖨️ Print / Save as PDF (A4)</button>
        <div class="banner">
            <h2 style="margin:0; font-size:20px; font-weight:800;">PAID SALES ANALYSER & PRIDICTOR STUDIO</h2>
            <p style="margin:5px 0 0 0; font-size:11px; opacity:0.8;">Platform: {detected_plat} | Detected Horizon: {detected_period} | Date: {datetime.now().strftime('%d-%b-%Y %H:%M')}</p>
        </div>
        <div class="kpi-row">
            <div class="kpi-c"><div class="t">Total Spend</div><div class="v">Rs. {summary.get('total_spend', 0):,.0f}</div></div>
            <div class="kpi-c"><div class="t">Orders</div><div class="v">{summary.get('total_purchases', 0)}</div></div>
            <div class="kpi-c"><div class="t">Blended CPA</div><div class="v">Rs. {summary.get('blended_cpa', 0):,.0f}</div></div>
            <div class="kpi-c"><div class="t">Gross Sales</div><div class="v">Rs. {summary.get('total_revenue', 0):,.0f}</div></div>
            <div class="kpi-c"><div class="t">ROAS</div><div class="v" style="color: {'#059669' if summary.get('blended_roas', 0) >= 2.5 else '#e11d48'};">{summary.get('blended_roas', 0):.2f}x</div></div>
        </div>
        <div class="sec">CAMPAIGN & AD METRICS</div>
        <table>
            <thead><tr><th>Ad / Creative Name</th><th style="text-align:center;">Spend</th><th style="text-align:center;">Orders</th><th style="text-align:center;">CPA</th><th style="text-align:center;">ROAS</th><th style="text-align:center;">Action</th></tr></thead>
            <tbody>{ads_rows_html}</tbody>
        </table>
        <div class="sec">EXECUTIVE DIRECTIVES</div>
        <div class="v-box" style="border-left-color:#059669;"><b>[+] TOP WINNER:</b><br>{verdict.get('winner', 'N/A')}</div>
        <div class="v-box" style="border-left-color:#e11d48;"><b>[-] IMMEDIATE BLEEDER (KILL):</b><br>{verdict.get('bleeder', 'N/A')}</div>
        <div class="v-box" style="border-left-color:#4f46e5;"><b>[*] TONIGHT'S SCALING ACTION:</b><br>{verdict.get('scaling_advice', 'N/A')}</div>
        <div class="v-box" style="border-left-color:#64748b;"><b>[>] TACTICAL ROADMAP:</b><br>{verdict.get('next_action', 'N/A')}</div>
    </body>
    </html>
    """

# --- A4 ROAS SCALING STRATEGY PRINT GENERATOR ---
def generate_roas_strategy_html(roas_tier, req_roas, req_cpa, current_aov, det_plat, strategy_content):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>PAID SALES ANALYSER & PRIDICTOR STUDIO -- {req_roas}X ROAS Blueprint</title>
        <style>
            @page {{ size: A4; margin: 12mm; }}
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #0f172a; margin: 0; padding: 15px; }}
            .header {{ background: #0f172a; color: white; padding: 22px; border-radius: 10px; }}
            .kpi-grid {{ display: flex; justify-content: space-between; margin: 18px 0; background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; }}
            .cell {{ text-align: center; }}
            .lbl {{ font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; }}
            .val {{ font-size: 22px; font-weight: 800; margin-top: 4px; color: #0f172a; }}
            .sec {{ font-size: 13px; font-weight: 800; margin-top: 22px; border-bottom: 2px solid #0f172a; padding-bottom: 4px; }}
            .box {{ margin-top: 8px; padding: 14px 18px; border-left: 4px solid #4f46e5; background: #f8fafc; font-size: 12px; line-height: 1.6; white-space: pre-wrap; }}
            .btn {{ background: #4f46e5; color: white; border: none; padding: 10px 20px; border-radius: 50px; font-size: 13px; font-weight: 700; cursor: pointer; margin-bottom: 15px; }}
            @media print {{ .btn {{ display: none; }} }}
        </style>
    </head>
    <body>
        <button class="btn" onclick="window.print()">🖨️ Print / Save as PDF (A4 Scaling Strategy)</button>
        <div class="header">
            <h2 style="margin:0; font-size:20px; font-weight:800;">{req_roas}X ROAS SCALING STRATEGY BLUEPRINT</h2>
            <p style="margin:5px 0 0 0; font-size:11px; opacity:0.8;">Target Milestone: {roas_tier} | Active Platform: {det_plat} | Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}</p>
        </div>
        
        <div class="kpi-grid">
            <div class="cell"><div class="lbl">Target ROAS</div><div class="val" style="color:#059669;">{req_roas:.1f}x</div></div>
            <div class="cell"><div class="lbl">Max Target CPA</div><div class="val">Rs. {req_cpa:,.0f}</div></div>
            <div class="cell"><div class="lbl">Product AOV</div><div class="val">Rs. {current_aov:,.0f}</div></div>
            <div class="cell"><div class="lbl">Platform Detected</div><div class="val" style="color:#4f46e5;">{det_plat}</div></div>
        </div>

        <div class="sec">STEP-BY-STEP TECHNICAL EXECUTION BLUEPRINT (1D, 3D, 5D, 7D)</div>
        <div class="box">{strategy_content}</div>
    </body>
    </html>
    """

# --- A4 MEDIA PLAN & AD ASSET PRINT DECK GENERATOR ---
def generate_copy_media_plan_html(calc, copy_text, brand_name, offer, location, cat_name, platform_name):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>PAID SALES ANALYSER & PRIDICTOR STUDIO -- Creative Brief & Settings</title>
        <style>
            @page {{ size: A4; margin: 12mm; }}
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #0f172a; margin: 0; padding: 15px; }}
            .header {{ background: #0f172a; color: white; padding: 22px; border-radius: 10px; }}
            .plan-grid {{ display: flex; justify-content: space-between; margin: 18px 0; background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; }}
            .cell {{ text-align: center; }}
            .lbl {{ font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; }}
            .val {{ font-size: 20px; font-weight: 800; margin-top: 4px; color: #0f172a; }}
            .sec {{ font-size: 13px; font-weight: 800; margin-top: 22px; border-bottom: 2px solid #0f172a; padding-bottom: 4px; }}
            .box {{ margin-top: 8px; padding: 14px 18px; border-left: 4px solid #4f46e5; background: #f8fafc; font-size: 12px; line-height: 1.6; white-space: pre-wrap; }}
            .btn {{ background: #4f46e5; color: white; border: none; padding: 10px 20px; border-radius: 50px; font-size: 13px; font-weight: 700; cursor: pointer; margin-bottom: 15px; }}
            @media print {{ .btn {{ display: none; }} }}
        </style>
    </head>
    <body>
        <button class="btn" onclick="window.print()">🖨️ Print / Save as PDF (A4 Media Plan & Settings)</button>
        <div class="header">
            <h2 style="margin:0; font-size:20px; font-weight:800;">PAID SALES ANALYSER & PRIDICTOR STUDIO</h2>
            <p style="margin:5px 0 0 0; font-size:11px; opacity:0.8;">Brand: {brand_name} | Platform: {platform_name} | Category: {cat_name} | Target: {location} | Date: {datetime.now().strftime('%d-%b-%Y')}</p>
        </div>
        
        <div class="plan-grid">
            <div class="cell"><div class="lbl">Daily Budget</div><div class="val">Rs. {calc['daily_budget']:,.0f}</div></div>
            <div class="cell"><div class="lbl">Target Revenue</div><div class="val">Rs. {calc['target_rev']:,.0f}</div></div>
            <div class="cell"><div class="lbl">Target Orders</div><div class="val">{calc['target_orders']} / day</div></div>
            <div class="cell"><div class="lbl">Max Target CPA</div><div class="val">Rs. {calc['target_cpa']:,.0f}</div></div>
            <div class="cell"><div class="lbl">Target ROAS</div><div class="val" style="color:#059669;">{calc['target_roas']:.2f}x</div></div>
        </div>

        <div class="sec">TRAFFIC & FUNNEL PROJECTIONS (INDIAN BENCHMARKS)</div>
        <div style="background:#f1f5f9; padding:12px; border-radius:6px; font-size:12px; line-height:1.6; margin-top:8px;">
            • <b>Est. Daily Clicks Required:</b> {calc['est_clicks']:,} clicks (at {calc['cvr']}% CVR)<br>
            • <b>Est. Impressions / Views Needed:</b> {calc['est_impressions']:,} views (at {calc['ctr']}% CTR & Rs. {calc['cpm']} CPM)<br>
            • <b>Promotional Hook / Offer:</b> {offer}
        </div>

        <div class="sec">CAMPAIGN ARCHITECTURE & DIRECT RESPONSE ASSETS</div>
        <div class="box">{copy_text}</div>
    </body>
    </html>
    """

# --- A4 CREATIVE REDESIGN BRIEF GENERATOR ---
def generate_creative_redesign_html(score_data, redesign_text, file_name):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Creative Safe-Zone & Copy Optimization Brief</title>
        <style>
            @page {{ size: A4; margin: 12mm; }}
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #0f172a; margin: 0; padding: 15px; }}
            .header {{ background: #0f172a; color: white; padding: 22px; border-radius: 10px; }}
            .grid {{ display: flex; justify-content: space-between; margin: 18px 0; background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; }}
            .cell {{ text-align: center; }}
            .lbl {{ font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; }}
            .val {{ font-size: 22px; font-weight: 800; margin-top: 4px; color: #0f172a; }}
            .sec {{ font-size: 13px; font-weight: 800; margin-top: 22px; border-bottom: 2px solid #0f172a; padding-bottom: 4px; }}
            .box {{ margin-top: 8px; padding: 14px 18px; border-left: 4px solid #10b981; background: #f8fafc; font-size: 12px; line-height: 1.5; white-space: pre-wrap; }}
            .btn {{ background: #10b981; color: white; border: none; padding: 10px 20px; border-radius: 50px; font-size: 13px; font-weight: 700; cursor: pointer; margin-bottom: 15px; }}
            @media print {{ .btn {{ display: none; }} }}
        </style>
    </head>
    <body>
        <button class="btn" onclick="window.print()">🖨️ Print / Save as PDF (A4 Redesign Brief)</button>
        <div class="header">
            <h2 style="margin:0; font-size:20px; font-weight:800;">CREATIVE COMPLIANCE & REDESIGN BRIEF</h2>
            <p style="margin:5px 0 0 0; font-size:11px; opacity:0.8;">Asset: {file_name} | Target: 9:16 / 4:5 Safe-Zone Optimization | Date: {datetime.now().strftime('%d-%b-%Y')}</p>
        </div>
        <div class="grid">
            <div class="cell"><div class="lbl">Baseline Score</div><div class="val" style="color:#f43f5e;">{score_data.get('overall_score', 6.8)} / 10</div></div>
            <div class="cell"><div class="lbl">Optimized Target</div><div class="val" style="color:#059669;">{score_data.get('redesigned_score', 8.4)} / 10</div></div>
            <div class="cell"><div class="lbl">Aspect Ratio</div><div class="val">{score_data.get('aspect_ratio', '9:16')}</div></div>
            <div class="cell"><div class="lbl">Safe-Zone Status</div><div class="val" style="color:#4f46e5;">Optimized</div></div>
        </div>
        <div class="sec">OPTIMIZED ON-SCREEN COPY & STAGING DIRECTIVES</div>
        <div class="box">{redesign_text}</div>
    </body>
    </html>
    """

# --- LUXURY TOP NAVBAR ---
st.markdown(f"""
<div class="top-navbar">
    <div style="display:flex; align-items:center; gap:16px;">
        {logo_html}
        <div>
            <h2 style="margin:0; font-size:21px; font-weight:900; letter-spacing:-0.03em; color:#ffffff;">
                PAID SALES <span style="background:linear-gradient(135deg, #818cf8 0%, #c084fc 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">ANALYSER</span> & PRIDICTOR STUDIO
            </h2>
            <p style="margin:2px 0 0 0; font-size:11px; color:#94a3b8; font-weight:600; letter-spacing:0.04em;">
                HYBRID META & GOOGLE ADVERTISING INTELLIGENCE • AUTOMATIC DATE HORIZON SENSING • A4 DECK SUITE
            </p>
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:12px;">
        <span style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); color:#34d399; padding:6px 14px; border-radius:20px; font-size:11px; font-weight:800; letter-spacing:0.04em;">
            🟢 LIVE HORIZON DETECTOR
        </span>
        <span style="background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.3); color:#a5b4fc; padding:6px 14px; border-radius:20px; font-size:11px; font-weight:800;">
            1-CLICK AUTO ENGINE
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- WORKSPACE TABS WITH SMOOTH BUTTON PILL DESIGN ---
nav_tab1, nav_tab2, nav_tab3 = st.tabs([
    "📸 Vision & Report Auditor (Meta + Google Auto-Detect)",
    "🎯 Ad Copy Studio & Financial Simulator (Manual + A4 PDF)",
    "🎨 Creative Scoring & Safe-Zone Studio (Meta & Google Rules)"
])

# ==============================================================================
# TAB 1: VISION & REPORT AUDITOR
# ==============================================================================
with nav_tab1:
    st.markdown("#### 📥 Hybrid Data Ingestion (Meta Ads / Google Ads)")
    st.caption("Upload screenshots or CSV/Excel reports from Meta Ads Manager or Google Ads. The AI will automatically detect the platform and reporting horizon (1D, 7D, 15D, 30D, 90D):")

    in_col1, in_col2 = st.columns(2)
    with in_col1:
        uploaded_imgs = st.file_uploader(
            "🖼️ Meta / Google Ads Screenshots (Multiple Images Supported)",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True
        )
    with in_col2:
        uploaded_csv = st.file_uploader(
            "📊 Ads Manager / Google Ads Exported CSV or Excel File",
            type=["csv", "xlsx", "xls"]
        )

    if uploaded_imgs or uploaded_csv:
        _, c_btn1, _ = st.columns([1, 2, 1])
        with c_btn1:
            btn_audit = st.button("🚀 EXECUTE AUTO-DETECTION & AUDIT")
        
        if btn_audit:
            if not active_api_key:
                st.error("Please enter your 'Google Gemini API Key' in the left sidebar!")
            else:
                with st.spinner("🤖 Analyzing metrics and verifying date horizon with live Gemini Flash engine..."):
                    try:
                        payload = []
                        
                        if uploaded_imgs:
                            for img_f in uploaded_imgs:
                                img = Image.open(img_f)
                                b_arr = io.BytesIO()
                                rgb_img = img.convert('RGB')
                                rgb_img.save(b_arr, format='JPEG')
                                payload.append(types.Part.from_bytes(data=b_arr.getvalue(), mime_type='image/jpeg'))
                        
                        sheet_text = ""
                        if uploaded_csv:
                            d_p = read_spreadsheet_robust(uploaded_csv)
                            sheet_text = f"\nRaw data from spreadsheet:\n{d_p.head(80).to_csv(index=False)}"

                        prompt = f"""
                        You are an Elite Senior Performance Marketer for D2C Brand in category: '{selected_category}'.
                        Target AOV is ₹{target_aov}.
                        Analyze the advertising input (Screenshots from Meta Ads / Google Ads or Spreadsheet).
                        {sheet_text}
                        
                        AUTOMATICALLY DETECT:
                        1. Advertising Platform: "Meta Ads", "Google Ads", or "Hybrid Meta + Google"
                        2. Timeframe / Date Horizon: e.g., "1D (Today)", "1D (Yesterday)", "7D (Last 7 Days)", "14/15D (Two Weeks)", "30D (Last Month)", or "90D / Lifetime".
                        
                        Extract all metrics accurately and return a STRICT JSON object in this exact schema:
                        {{
                            "detected_platform": "Meta Ads / Google Ads / Hybrid",
                            "detected_timeframe": "1D / 7D / 15D / 30D / 90D",
                            "summary": {{
                                "total_spend": 0.0,
                                "total_purchases": 0,
                                "total_revenue": 0.0,
                                "blended_cpa": 0.0,
                                "blended_roas": 0.0
                            }},
                            "ads": [
                                {{
                                    "ad_name": "Campaign or Ad Name",
                                    "spend": 0.0,
                                    "purchases": 0,
                                    "revenue": 0.0,
                                    "cpa": 0.0,
                                    "roas": 0.0,
                                    "cpc": 0.0,
                                    "ctr": 0.0,
                                    "decision": "KILL or SCALE or WATCH",
                                    "reason": "Short decisive rationale in English"
                                }}
                            ],
                            "audit_verdict": {{
                                "winner": "Which ad/campaign is winning and why",
                                "bleeder": "Which ad/campaign is bleeding money and must be stopped",
                                "scaling_advice": "Budget scaling advice for tonight",
                                "next_action": "Tactical roadmap for tomorrow"
                            }}
                        }}
                        Ensure numbers are mathematically sound. Calculate missing values if required. Return ONLY the JSON object.
                        """

                        raw_res_text = call_gemini_dynamic(prompt, payload)
                        clean_json = extract_json(raw_res_text)
                        data = json.loads(clean_json)

                        st.session_state["auto_analyzed_data"] = data
                        st.rerun()

                    except Exception as e:
                        st.error(f"Analysis Error: {e}")

    # Display Analyzed Data
    if "auto_analyzed_data" in st.session_state:
        aud_data = st.session_state["auto_analyzed_data"]
        summ = aud_data.get("summary", {})
        ads_l = aud_data.get("ads", [])
        verd = aud_data.get("audit_verdict", {})
        det_plat = aud_data.get("detected_platform", "Meta Ads")
        det_time = aud_data.get("detected_timeframe", "Auto-Detected")

        st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
        
        t_c1, t_c2 = st.columns([1.6, 1.4])
        with t_c1:
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                <span class="pill-blue">{det_plat}</span>
                <span class="pill-green">📅 Auto-Detected Period: {det_time}</span>
            </div>
            """, unsafe_allow_html=True)
        with t_c2:
            html_rep = generate_audit_html_report(summ, ads_l, verd, det_time, det_plat)
            st.download_button(
                label="📄 Export A4 Audit Deck",
                data=html_rep,
                file_name=f"Studio_Audit_{datetime.now().strftime('%d_%b')}.html",
                mime="text/html"
            )

        st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)

        ak1, ak2, ak3, ak4, ak5 = st.columns(5)
        cpa_v = summ.get('blended_cpa', 0)
        roas_v = summ.get('blended_roas', 0)
        
        with ak1:
            st.markdown(f"""<div class="kpi-card"><div class="kpi-lbl">Total Ad Spend</div><div class="kpi-val">₹{summ.get('total_spend', 0):,.0f}</div><span class="kpi-pill" style="background:#1e293b; color:#94a3b8;">Total Outflow</span></div>""", unsafe_allow_html=True)
        with ak2:
            st.markdown(f"""<div class="kpi-card"><div class="kpi-lbl">Orders / Purchases</div><div class="kpi-val">{int(summ.get('total_purchases', 0))}</div><span class="kpi-pill pill-green">Direct Conversions</span></div>""", unsafe_allow_html=True)
        with ak3:
            st.markdown(f"""<div class="kpi-card"><div class="kpi-lbl">Blended CPA</div><div class="kpi-val">₹{cpa_v:,.0f}</div><span class="kpi-pill {'pill-green' if cpa_v < 900 and cpa_v > 0 else 'pill-red'}">{'✓ Profitable' if cpa_v < 900 and cpa_v > 0 else '⚠ Elevated'}</span></div>""", unsafe_allow_html=True)
        with ak4:
            st.markdown(f"""<div class="kpi-card"><div class="kpi-lbl">Gross Revenue</div><div class="kpi-val">₹{summ.get('total_revenue', 0):,.0f}</div><span class="kpi-pill" style="background:#1e293b; color:#cbd5e1;">Topline Yield</span></div>""", unsafe_allow_html=True)
        with ak5:
            st.markdown(f"""<div class="kpi-card"><div class="kpi-lbl">Account ROAS</div><div class="kpi-val" style="color:{'#34d399' if roas_v >= 2.5 else '#fb7185'};">{roas_v:.2f}x</div><span class="kpi-pill {'pill-green' if roas_v >= 2.5 else 'pill-red'}">{'★ Winner' if roas_v >= 2.5 else 'Below Target'}</span></div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)

        aud_t1, aud_t2, aud_t3, aud_t4, aud_t5 = st.tabs([
            "📋 Action Matrix", 
            "📈 Spend vs Revenue Chart", 
            "🔮 Horizon Forecast (1D-90D)", 
            "🧠 Senior Media Buyer Directives",
            "🚀 ROAS Scaling Blueprint (3X - 7X)"
        ])
        
        with aud_t1:
            if ads_l:
                st.dataframe(pd.DataFrame(ads_l), use_container_width=True)
                
                ck1, ck2 = st.columns(2)
                with ck1:
                    st.markdown("""<div style="background:rgba(244,63,94,0.06); border:1px solid rgba(244,63,94,0.2); border-radius:12px; padding:15px;"><h5 style="color:#fb7185; margin:0 0 10px 0; font-size:14px; font-weight:800;">🛑 IMMEDIATE CAPITAL BLEEDERS (KILL)</h5>""", unsafe_allow_html=True)
                    kills = [a for a in ads_l if "KILL" in str(a.get("decision", "")).upper()]
                    if not kills:
                        st.markdown("<p style='color:#34d399; font-size:12px;'>✓ No ad is leaking budget</p>", unsafe_allow_html=True)
                    for k in kills:
                        st.markdown(f"<p style='font-size:13px; margin:4px 0;'><b>{k.get('ad_name')}</b> — Spend: ₹{k.get('spend')} | <span style='color:#fb7185;'>{k.get('reason')}</span></p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                with ck2:
                    st.markdown("""<div style="background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.2); border-radius:12px; padding:15px;"><h5 style="color:#34d399; margin:0 0 10px 0; font-size:14px; font-weight:800;">🚀 HIGH-EFFICIENCY SCALERS (SCALE)</h5>""", unsafe_allow_html=True)
                    scales = [a for a in ads_l if "SCALE" in str(a.get("decision", "")).upper()]
                    if not scales:
                        st.markdown("<p style='color:#94a3b8; font-size:12px;'>Scaling requires at least 2 sales and 3x+ ROAS.</p>", unsafe_allow_html=True)
                    for s in scales:
                        st.markdown(f"<p style='font-size:13px; margin:4px 0;'><b>{s.get('ad_name')}</b> — ROAS: {s.get('roas')}x | <span style='color:#34d399;'>{s.get('reason')}</span></p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

        with aud_t2:
            if ads_l:
                df_c = pd.DataFrame(ads_l)
                fig_c = px.bar(df_c, x="ad_name", y=["spend", "revenue"], barmode="group",
                             labels={"value": "Amount (₹)", "ad_name": "Ad Name"},
                             color_discrete_map={"spend": "#f43f5e", "revenue": "#10b981"},
                             template="plotly_dark")
                fig_c.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=380)
                st.plotly_chart(fig_c, use_container_width=True)

        # --- FORECASTING SUITE ---
        with aud_t3:
            st.markdown("#### 🔮 Horizon Forecasting Suite (1D, 3D, 7D, 15D, 30D, 90D)")
            st.caption("Forecasting future revenue, target order volumes, and inventory requirements based on active run-rate:")

            fc_c1, fc_c2, fc_c3 = st.columns(3)
            with fc_c1:
                forecast_scenario = st.selectbox("Growth Trajectory Model:", [
                    "Expected / Moderate Run-Rate", "Conservative Buffer Model", "Aggressive Scale Model (20+ Orders/Day)"
                ])
            with fc_c2:
                base_daily_spend = st.number_input("Base Daily Spend Rate (₹):", value=max(float(summ.get('total_spend', 4500)), 1500.0), step=500.0)
            with fc_c3:
                effective_cpa = st.number_input("Effective Target CPA (₹):", value=max(float(summ.get('blended_cpa', 650)), 400.0), step=50.0)

            if "Conservative" in forecast_scenario:
                cpa_mult = 1.15
            elif "Aggressive" in forecast_scenario:
                cpa_mult = 0.85
            else:
                cpa_mult = 1.0

            proj_cpa = effective_cpa * cpa_mult

            periods = [
                {"label": "1 Day (Tonight Pacing)", "days": 1, "budget_mult": 1.0},
                {"label": "3 Days (Short-term Horizon)", "days": 3, "budget_mult": 1.08},
                {"label": "7 Days (Weekly Pacing)", "days": 7, "budget_mult": 1.15},
                {"label": "15 Days (Bi-weekly Run)", "days": 15, "budget_mult": 1.30},
                {"label": "30 Days (Full Month GMV)", "days": 30, "budget_mult": 1.50},
                {"label": "90 Days (Quarterly Festive Scale)", "days": 90, "budget_mult": 2.00}
            ]

            forecast_rows = []
            chart_days = []
            chart_revenue = []
            chart_spend = []

            for p in periods:
                d_count = p["days"]
                avg_daily_budget = base_daily_spend * p["budget_mult"]
                total_proj_spend = avg_daily_budget * d_count
                proj_orders = int(total_proj_spend / proj_cpa) if proj_cpa > 0 else 0
                proj_revenue = proj_orders * target_aov
                proj_roas = round(proj_revenue / total_proj_spend, 2) if total_proj_spend > 0 else 0
                stock_needed = int(proj_orders * 1.10)

                forecast_rows.append({
                    "Forecast Horizon": p["label"],
                    "Projected Spend": f"₹{total_proj_spend:,.0f}",
                    "Projected Orders": f"{proj_orders} Orders",
                    "Daily Order Run-Rate": f"{round(proj_orders/d_count, 1)} / day",
                    "Projected GMV (Revenue)": f"₹{proj_revenue:,.0f}",
                    "Target ROAS": f"{proj_roas}x",
                    "Stock Buffer Required": f"{stock_needed} Units"
                })
                chart_days.append(f"{d_count}D")
                chart_revenue.append(proj_revenue)
                chart_spend.append(total_proj_spend)

            df_forecast = pd.DataFrame(forecast_rows)
            st.dataframe(df_forecast, use_container_width=True)

            fig_fc = go.Figure()
            fig_fc.add_trace(go.Bar(x=chart_days, y=chart_spend, name='Projected Ad Capital (Spend)', marker_color='#f43f5e'))
            fig_fc.add_trace(go.Bar(x=chart_days, y=chart_revenue, name='Projected Gross GMV (Revenue)', marker_color='#10b981'))
            fig_fc.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                template="plotly_dark",
                barmode='group',
                height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_fc, use_container_width=True)

        with aud_t4:
            st.markdown(f"""
            <div style="background:#0f172a; padding:16px; border-radius:10px; border-left:4px solid #10b981; margin-bottom:10px;">
                <b style="color:#34d399; font-family:'Outfit',sans-serif; font-size:15px;">[+] TOP WINNER:</b><br>{verd.get('winner', 'N/A')}
            </div>
            <div style="background:#0f172a; padding:16px; border-radius:10px; border-left:4px solid #f43f5e; margin-bottom:10px;">
                <b style="color:#fb7185; font-family:'Outfit',sans-serif; font-size:15px;">[-] IMMEDIATE BLEEDER (KILL):</b><br>{verd.get('bleeder', 'N/A')}
            </div>
            <div style="background:#0f172a; padding:16px; border-radius:10px; border-left:4px solid #6366f1; margin-bottom:10px;">
                <b style="color:#818cf8; font-family:'Outfit',sans-serif; font-size:15px;">[*] TONIGHT'S SCALING ACTION:</b><br>{verd.get('scaling_advice', 'N/A')}
            </div>
            <div style="background:#0f172a; padding:16px; border-radius:10px; border-left:4px solid #94a3b8; margin-bottom:10px;">
                <b style="color:#cbd5e1; font-family:'Outfit',sans-serif; font-size:15px;">[>] TACTICAL ROADMAP:</b><br>{verd.get('next_action', 'N/A')}
            </div>
            """, unsafe_allow_html=True)

        # ==============================================================================
        # TAB 5: ROAS BLUEPRINT (PERFECTLY CENTERED ACTION BUTTON)
        # ==============================================================================
        with aud_t5:
            roas_target_tier = st.radio(
                "Select Target ROAS Milestone to Scale:",
                [
                    "🎯 3X ROAS (Break-even to Stable Profit)",
                    "🚀 4X ROAS (Growth & Capital Efficiency)",
                    "💎 5X ROAS (Aggressive Profit Scaling)",
                    "👑 7X ROAS (Hyper-Margin Market Domination)"
                ],
                horizontal=True
            )

            current_aov = target_aov
            
            if "3X" in roas_target_tier:
                req_roas = 3.0
                req_cpa = round(current_aov / 3.0, 0)
                badge_color = "#38bdf8"
            elif "4X" in roas_target_tier:
                req_roas = 4.0
                req_cpa = round(current_aov / 4.0, 0)
                badge_color = "#818cf8"
            elif "5X" in roas_target_tier:
                req_roas = 5.0
                req_cpa = round(current_aov / 5.0, 0)
                badge_color = "#34d399"
            else:
                req_roas = 7.0
                req_cpa = round(current_aov / 7.0, 0)
                badge_color = "#f43f5e"

            is_google_active = "Google" in det_plat
            is_meta_active = "Meta" in det_plat
            if not is_google_active and not is_meta_active:
                is_google_active = True
                is_meta_active = True

            meta_strategy_dict = {
                "3X": "[1D - Tonight Immediate]: Pause any ad spending >1x AOV (₹2,800) with 0 purchases. Uncheck Audience Network & Messenger placements to prevent click leakage.\n\n[3D - Stabilization]: Consolidate budget into 1 CBO campaign. Keep only top 2 winning creatives (e.g. Ad C). Turn OFF duplicate sets.\n\n[5D - Audience Tune]: Switch targeting to Open Broad (Women 24-48) with Advantage+ audience suggestions (Zara, Fabindia, Cotton dresses).\n\n[7D - Scale Horizon]: Once daily CPA settles under ₹930 for 48 consecutive hours, increase campaign budget by +20% at 11:59 PM.",
                "4X": "[1D - Tonight Immediate]: Offer Injection: Add 'Buy 2 Get 10% OFF + Flat ₹150 on Prepaid UPI' to Primary Text. This pushes blended AOV to ₹5,200+, boosting ROAS mathematically by 35%.\n\n[3D - Creative Refresh]: Deploy the 4:5 Carousel featuring Top 5 hero dresses alongside the 9:16 Full-screen video.\n\n[5D - Bidding Optimization]: Set up a dedicated Scaling CBO with Cost Cap = ₹700. Meta will only enter auctions where purchase probability is verified.\n\n[7D - Scale Horizon]: Duplicate winner into a pure Broad CBO campaign at ₹5,000/day. Scale budget +20% every 48 hours.",
                "5X": "[1D - Tonight Immediate]: Isolate super-winners (Ad C) into a Winner-Only CBO. Allocate 70% of budget strictly to the top 2 creatives.\n\n[3D - Creative DCT (3:2:2)]: Launch Dynamic Creative Testing (3 pattern-interrupt video hooks, 2 pain-point copies, 2 headlines). Kill hooks with <30% thumbstop rate.\n\n[5D - Exclusion Hygiene]: Exclude past 180-day website purchasers to ensure 100% of capital captures fresh cold prospects.\n\n[7D - Scale Horizon]: Introduce Minimum ROAS bidding (Set Min ROAS = 4.2x). Scale aggressively into top 15 Indian fashion hubs.",
                "7X": "[1D - Tonight Immediate]: High-Ticket Bundle Play: Launch 'Buy Any 3 Dresses at ₹6,999' package. At ₹400 target CPA, ROAS hits 7.5x instantly on checkout.\n\n[3D - Bid Cap Sniper]: Run Bid Cap testing with bids set at ₹450. Capture only bottom-of-funnel hyper-ready buyers.\n\n[5D - Top 25% LTV LAL]: Upload VIP customer list to build 1% Lookalikes based on highest spenders.\n\n[7D - Scale Horizon]: Rapid creative injection (1 new video hook every 4 days) to prevent creative decay."
            }

            google_strategy_dict = {
                "3X": "[1D - Tonight Immediate]: In PMax (e.g. CB: Performance Max), cut daily budget by 25% immediately. Turn OFF Final URL Expansion to prevent traffic waste on non-product pages.\n\n[3D - Negative Shield]: Apply Account-Level Negative Keyword list (exclude cheap, sasta, wholesale, kurti, saree, stitching, tailor).\n\n[5D - Location Hygiene]: Switch Location Options strictly to 'Presence: People in or regularly in your targeted locations'.\n\n[7D - Smart Bidding Transition]: Once account hits 25 conversions, switch bidding to Maximize Conversion Value with Target ROAS = 300%.",
                "4X": "[1D - Tonight Immediate]: Brand Exclusion: Add brand list (Sneha B, snehab.com) to PMax settings. Stop paying Google for organic brand searches.\n\n[3D - Asset Group Segmentation]: Split PMax into 2 dedicated Asset Groups: 'Cotton Staples' vs 'Curvy & Plus Size'.\n\n[5D - Shopping Feed Dominance]: Optimize Google Merchant Center feed titles: Add 'Pure Breathable Cotton Maxi Dress with Pockets'.\n\n[7D - Smart Bidding Transition]: Set Target ROAS to 400%. Google automatically eliminates low-intent placements.",
                "5X": "[1D - Tonight Immediate]: Exclude Mobile App Placements: Block adsenseformobileapps.com to kill zero-converting mobile game banner clicks.\n\n[3D - High-Intent Search STAGs]: Launch Exact/Phrase match Search campaign: 'pure cotton dresses with pockets', [plus size cotton dresses online].\n\n[5D - Customer Acquisition]: Enable 'Bid only for new customers' with ₹500 incremental value.\n\n[7D - Smart Bidding Transition]: Lock Target ROAS to 500%. Channel 80% budget into approved Google Shopping feed items.",
                "7X": "[1D - Tonight Immediate]: Restrict Location to Top 5 High-AOV Metros (Bangalore, Mumbai, Delhi-NCR, Hyderabad, Chennai). Exclude low-intent postal codes.\n\n[3D - First-Party Customer Match]: Upload 1,000+ past customer emails/phones into Audience Manager as PMax signal.\n\n[5D - Value-Based Bidding Rules]: Set value rules: +25% conversion value for South India Tier-1 cities.\n\n[7D - Smart Bidding Transition]: Enforce Target ROAS = 700% with custom label filtering (only high-margin bestsellers active)."
            }

            active_tier_key = "3X" if "3X" in roas_target_tier else ("4X" if "4X" in roas_target_tier else ("5X" if "5X" in roas_target_tier else "7X"))
            
            strategy_export_content = f"TARGET: {req_roas}X ROAS (Max CPA: Rs. {req_cpa:,.0f})\n\n"
            if is_meta_active:
                strategy_export_content += f"=== META ADS LEVERS ===\n{meta_strategy_dict[active_tier_key]}\n\n"
            if is_google_active:
                strategy_export_content += f"=== GOOGLE ADS LEVERS ===\n{google_strategy_dict[active_tier_key]}\n"

            roas_hdr_col1, roas_hdr_col2 = st.columns([1.6, 1.4])
            with roas_hdr_col1:
                st.markdown(f"#### 🚀 Target ROAS Multiplier Engine ({req_roas}X Target)")
                st.caption(f"Active Channel: **{det_plat}** (Showing active levers for detected channel, inactive channel set to OFF)")
            with roas_hdr_col2:
                strat_html = generate_roas_strategy_html(roas_target_tier, req_roas, req_cpa, current_aov, det_plat, strategy_export_content)
                st.download_button(
                    label="📄 Export Strategy (PDF)",
                    data=strat_html,
                    file_name=f"ROAS_{req_roas}X_Blueprint_{datetime.now().strftime('%d_%b')}.html",
                    mime="text/html"
                )

            st.markdown(f"""
            <div style="background:rgba(15,23,42,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:15px; margin-bottom:15px; display:flex; justify-content:space-around; text-align:center;">
                <div><span style="font-size:11px; color:#94a3b8; font-weight:700; text-transform:uppercase;">Target ROAS</span><h3 style="margin:2px 0 0 0; color:{badge_color};">{req_roas}x</h3></div>
                <div><span style="font-size:11px; color:#94a3b8; font-weight:700; text-transform:uppercase;">Required Max CPA</span><h3 style="margin:2px 0 0 0; color:#ffffff;">₹{req_cpa:,.0f}</h3></div>
                <div><span style="font-size:11px; color:#94a3b8; font-weight:700; text-transform:uppercase;">Product AOV</span><h3 style="margin:2px 0 0 0; color:#ffffff;">₹{current_aov:,.0f}</h3></div>
                <div><span style="font-size:11px; color:#94a3b8; font-weight:700; text-transform:uppercase;">Active Channel</span><h3 style="margin:2px 0 0 0; color:#818cf8;">{det_plat}</h3></div>
            </div>
            """, unsafe_allow_html=True)

            col_meta_proto, col_google_proto = st.columns(2)

            with col_meta_proto:
                if is_meta_active:
                    st.markdown("##### 📱 Meta Ads Manager — 🟢 ACTIVE (Auto-Detected)")
                    st.markdown(f"""
                    <div class="roas-milestone-card" style="border-left:4px solid {badge_color};">
                        {meta_strategy_dict[active_tier_key].replace(chr(10)+chr(10), '<br><br>')}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("##### 📱 Meta Ads Manager — ⚪ OFF (Inactive for this Screenshot)")
                    st.markdown("""
                    <div class="roas-inactive-card">
                        <span style="color:#94a3b8; font-weight:700;">⚪ Inactive Mode:</span> Meta Ads was not detected in this screenshot. Only Google Ads settings are currently being scaled.
                    </div>
                    """, unsafe_allow_html=True)

            with col_google_proto:
                if is_google_active:
                    st.markdown("##### 🔍 Google Ads (PMax & Search) — 🟢 ACTIVE (Auto-Detected)")
                    st.markdown(f"""
                    <div class="roas-milestone-card" style="border-left:4px solid {badge_color};">
                        {google_strategy_dict[active_tier_key].replace(chr(10)+chr(10), '<br><br>')}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("##### 🔍 Google Ads (PMax & Search) — ⚪ OFF (Inactive for this Screenshot)")
                    st.markdown("""
                    <div class="roas-inactive-card">
                        <span style="color:#94a3b8; font-weight:700;">⚪ Inactive Mode:</span> Google Ads was not detected in this screenshot. Only Meta Ads settings are currently being scaled.
                    </div>
                    """, unsafe_allow_html=True)

            # 3-COLUMN PYTHON GRID FOR BULLETPROOF CENTERING
            _, c_btn_tactical, _ = st.columns([1, 2, 1])
            with c_btn_tactical:
                btn_live_tactical = st.button("⚡ GENERATE AI LIVE TACTICAL AUDIT FOR THIS ROAS TARGET")

            if btn_live_tactical:
                if not active_api_key:
                    st.error("Please enter your Gemini API Key in the left sidebar!")
                else:
                    with st.spinner(f"Analyzing live account metrics against {req_roas}x ROAS target on {det_plat}..."):
                        try:
                            bridge_prompt = f"""
                            You are an Elite Senior Performance Marketer for D2C brand Sneha B.
                            Active Account Summary:
                            {json.dumps(summ)}
                            Active Ads/Campaigns:
                            {json.dumps(ads_l)}
                            Active Detected Platform: {det_plat}
                            Target ROAS: {req_roas}x (Target CPA: ₹{req_cpa}).
                            
                            Based strictly on the current performance and detected platform:
                            Provide an aggressive, step-by-step tactical directive on:
                            ### 1. EXACT ACTIONS TONIGHT (Stop the Bleed)
                            ### 2. 3-DAY STABILIZATION STEP (Bidding & Budget Guardrails)
                            ### 3. 7-DAY SCALING PROTOCOL to hit {req_roas}x ROAS.
                            
                            Format with tight, clean bullet points without unnecessary blank lines.
                            """
                            bridge_res = call_gemini_dynamic(bridge_prompt)
                            st.session_state["live_tactical_plan"] = bridge_res
                            st.session_state["live_tactical_roas"] = req_roas
                            st.session_state["live_tactical_plat"] = det_plat
                            st.session_state["live_tactical_cpa"] = req_cpa
                            st.rerun()
                        except Exception as be:
                            st.error(f"Error generating scaling plan: {be}")

            if "live_tactical_plan" in st.session_state:
                st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
                
                tac_bar_c1, tac_bar_c2 = st.columns([1.6, 1.4])
                with tac_bar_c1:
                    st.markdown(f"<h5 style='color:#818cf8; margin:0;'>⚡ TACTICAL PROTOCOL FOR {st.session_state['live_tactical_roas']}X ROAS SCALING ({st.session_state['live_tactical_plat'].upper()})</h5>", unsafe_allow_html=True)
                with tac_bar_c2:
                    tac_plan_html = generate_roas_strategy_html(
                        f"{st.session_state['live_tactical_roas']}X Tactical Milestone",
                        st.session_state['live_tactical_roas'],
                        st.session_state['live_tactical_cpa'],
                        current_aov,
                        st.session_state['live_tactical_plat'],
                        st.session_state['live_tactical_plan']
                    )
                    st.download_button(
                        label="📄 Export Tactical Plan (PDF)",
                        data=tac_plan_html,
                        file_name=f"Tactical_{st.session_state['live_tactical_roas']}X_Protocol_{datetime.now().strftime('%d_%b')}.html",
                        mime="text/html"
                    )

                cleaned_plan = re.sub(r'\n{3,}', '\n\n', st.session_state['live_tactical_plan']).strip()
                
                st.markdown(f"""
                <div class="deck-card">
                    {cleaned_plan}
                </div>
                """, unsafe_allow_html=True)

# ==============================================================================
# TAB 2: AD COPY STUDIO & STRUCTURED CAMPAIGN BLUEPRINT
# ==============================================================================
with nav_tab2:
    st.markdown("#### 🎯 Financial Media Plan, Architecture Settings & Ad Copy Studio")
    st.caption(f"Active Category: **{selected_category}** (Real-time recalculation using pre-loaded Indian benchmarks)")
    
    col_in1, col_in2, col_in3 = st.columns(3)
    
    with col_in1:
        calc_budget = st.number_input("💵 Daily Ad Budget (₹):", value=5000, step=500)
        calc_target_rev = st.number_input("🎯 Target Daily Revenue (₹):", value=20000, step=1000)
        calc_aov = st.number_input("📦 Product Price / AOV (₹):", value=int(target_aov), step=100)

    with col_in2:
        location_options = [
            "🇮🇳 Pan-India (All India Broad Scaling)",
            "🏙️ Tier-1 Metros (Mumbai, Delhi-NCR, Bangalore, Hyderabad, Pune, Chennai, Kolkata)",
            "🌴 South India Tier-1 & Tier-2 (Bangalore, Chennai, Hyderabad, Kochi, Coimbatore, Vizag)",
            "📈 Top 25 High-Growth Tier-2 Hubs (Jaipur, Chandigarh, Surat, Lucknow, Indore, etc.)",
            "🧭 North & West India Focus (Delhi-NCR, Punjab, Rajasthan, Gujarat, Maharashtra)",
            "✏️ Custom Location (Enter Below)"
        ]
        sel_location = st.selectbox("📍 Target Geography:", location_options, index=2)
        if "Custom" in sel_location:
            calc_location = st.text_input("Enter Custom Location:", value="Mumbai & Bangalore")
        else:
            calc_location = sel_location
            
        offer_options = [
            "🛍️ Buy Any 2 & Get 10% OFF + Flat 10% Extra on UPI / Prepaid",
            "🎁 Buy 1 Get 1 FREE (BOGO Offer)",
            "⚡ Flat 15% Instant OFF + Free Shipping on All Orders",
            "🔥 End of Season Clearance: Flat 50% OFF",
            "🏷️ Bundle Value Deal: Buy Any 2 for ₹1,999",
            "💥 Flash Promo: Up to 70% OFF + Extra ₹200 OFF on Prepaid",
            "✏️ Custom Offer (Enter Below)"
        ]
        sel_offer = st.selectbox("⚡ Active Offer / Promotional Hook:", offer_options, index=0)
        if "Custom" in sel_offer:
            calc_discount = st.text_input("Enter Custom Offer:", value="Buy 2 Get 15% OFF")
        else:
            calc_discount = sel_offer

    with col_in3:
        brand_name = st.text_input("🏷️ Brand / Product Title:", value="Sneha B")
        
        platform_choice = st.selectbox("🎯 Target Advertising Platform:", [
            "📱 Meta Ads (Instagram & Facebook 3:2:2 Direct Response)",
            "🔍 Google Ads (Search & Performance Max Complete Deck)",
            "🚀 Omnichannel Suite (Both Meta & Google Complete Package)"
        ])

    b_cpm = cat_benchmarks['cpm']
    b_ctr = cat_benchmarks['ctr']
    b_cvr = cat_benchmarks['cvr']
    
    calc_target_roas = (calc_target_rev / calc_budget) if calc_budget > 0 else 0
    calc_target_orders = int(calc_target_rev / calc_aov) if calc_aov > 0 else 0
    calc_target_cpa = (calc_budget / calc_target_orders) if calc_target_orders > 0 else 0
    
    est_clicks_needed = int(calc_target_orders / (b_cvr / 100)) if b_cvr > 0 else 0
    est_impressions_needed = int(est_clicks_needed / (b_ctr / 100)) if b_ctr > 0 else 0

    st.markdown("---")
    st.markdown("##### 📐 Auto-Recalculated Financial & Traffic Funnel")
    
    f1, f2, f3, f4, f5, f6 = st.columns(6)
    f1.metric("Target ROAS", f"{calc_target_roas:.2f}x", delta="Required" if calc_target_roas >= cat_benchmarks['target_roas'] else "Aggressive")
    f2.metric("Target Orders", f"{calc_target_orders} / day")
    f3.metric("Max Target CPA", f"₹{calc_target_cpa:,.0f}")
    f4.metric("Required Clicks", f"{est_clicks_needed:,}")
    f5.metric("Required Views", f"{est_impressions_needed:,}")
    f6.metric("Benchmark CVR", f"{b_cvr}%")

    calc_payload = {
        "daily_budget": calc_budget,
        "target_rev": calc_target_rev,
        "aov": calc_aov,
        "target_roas": calc_target_roas,
        "target_orders": calc_target_orders,
        "target_cpa": calc_target_cpa,
        "est_clicks": est_clicks_needed,
        "est_impressions": est_impressions_needed,
        "cpm": b_cpm,
        "ctr": b_ctr,
        "cvr": b_cvr
    }

    # 3-COLUMN PYTHON GRID FOR BULLETPROOF CENTERING
    _, c_btn_copy, _ = st.columns([1, 2, 1])
    with c_btn_copy:
        btn_copy_gen = st.button(f"⚡ GENERATE STEP-BY-STEP SETTINGS & AD ASSETS FOR {platform_choice.split(' ')[1].upper()}")

    if btn_copy_gen:
        if not active_api_key:
            st.error("Please enter your 'Google Gemini API Key' in the left sidebar!")
        else:
            with st.spinner(f"✍️ Connecting to Google live engine to build campaign architecture & ad copy for {platform_choice}..."):
                try:
                    if "Google" in platform_choice:
                        prompt_framework = f"""
                        TASK FOR GOOGLE ADS ONLY:
                        Produce a clean, unmixed, step-by-step Campaign Architecture Guide AND Headlines/Copy Suite for GOOGLE ADS.
                        Do NOT include Meta Ads or Instagram terminology here.

                        ### 🏗️ SECTION 1: GOOGLE ADS STEP-BY-STEP CAMPAIGN ARCHITECTURE (Scaled for {calc_target_orders} Orders/Day)
                        - Campaign 1 (Performance Max - PMax):
                          * Asset Group Structure: Split into 'Hero Bestsellers' and 'Curvy / Inclusive Fits'.
                          * Budget Allocation: Allocate 65% of daily budget (₹{int(calc_budget*0.65)}) to PMax.
                          * Customer Acquisition Settings: Bid higher for new customers, URL Expansion OFF.
                        - Campaign 2 (High-Intent Search STAG):
                          * Structure: Exact and Phrase Match Single-Theme Ad Groups.
                          * Budget Allocation: Allocate 35% of daily budget (₹{int(calc_budget*0.35)}) to Search.
                        - Bidding Strategy: Start with Maximize Conversions -> Shift to Target ROAS ({calc_target_roas:.1f}x) after 25 conversions.
                        - Negative Keyword Shield: 15+ low-intent negative terms to block wasted spend in India.
                        - Location Settings: Strictly 'Presence: People in or regularly in your targeted locations'.

                        ### 📝 SECTION 2: GOOGLE ADS COPY & HEADLINES SUITE
                        - 15 Responsive Search Ad (RSA) Headlines (<30 characters each, numbered 1-15 with exact character counts).
                        - 5 Long Headlines for PMax & Search (<90 characters each, numbered 1-5 with char counts).
                        - 4 Descriptions (<90 characters each, numbered 1-4 with char counts).
                        - 6 High-Intent Search Themes / Phrase Match Keywords.
                        - Extension Assets Brief (Sitelinks, Callouts, Promotions).
                        """
                    elif "Meta" in platform_choice:
                        prompt_framework = f"""
                        TASK FOR META ADS ONLY:
                        Produce a clean, unmixed, step-by-step Campaign Architecture Guide AND 3:2:2 Creative Copy Suite for META ADS (Instagram & Facebook).
                        Do NOT include Google Ads terminology here.

                        ### 🏗️ SECTION 1: META ADS STEP-BY-STEP CAMPAIGN ARCHITECTURE (Scaled for {calc_target_orders} Orders/Day)
                        - Campaign Objective: Sales with CBO (Advantage Campaign Budget) ON at ₹{calc_budget}/day.
                        - Ad Set 1 (Broad Scaling - 65% Budget): Open Broad (Women 24-48, Pan-India or South India).
                        - Ad Set 2 (High-Affinity Stack - 35% Budget): Interest stack for India D2C.
                        - Placements: Manual Placements (Instagram & Facebook Feeds, Stories, Reels). Uncheck Audience Network & Messenger.
                        - Execution Rules: Kill spend limit (1x AOV with 0 sales) and Scale rule (+20% budget every 48h).

                        ### 🎬 SECTION 2: 3:2:2 DIRECT RESPONSE CREATIVE & COPY SUITE
                        - 3 Viral Video Hooks for the first 3 seconds of Instagram Reels/Stories (High pattern-interrupt, addressing pain points).
                        - 2 High-Converting Primary Texts (1 Emotional/Fit Angle + 1 Offer/Urgency Angle with bulleted features and clear CTA).
                        - 2 Punchy Headlines (<30 characters each).
                        - 1 Reassuring Description (<90 characters).
                        - Recommended CTA Button & Creative Staging Tips.
                        """
                    else:
                        prompt_framework = f"""
                        TASK FOR OMNICHANNEL SUITE:
                        Provide BOTH complete Meta Ads architecture & copy AND Google Ads architecture & copy in distinct, completely separate sections!
                        """

                    copy_prompt = f"""
                    You are an Elite Direct-Response Performance Media Buyer & Ads Architect specializing in Indian D2C E-commerce.
                    Category: {selected_category}
                    Brand / Product: {brand_name}
                    Target Geography: {calc_location}
                    Product AOV: ₹{calc_aov}
                    Active Promotion / Offer: {calc_discount}
                    Target Platform: {platform_choice}
                    Financial Mandate: Deliver {calc_target_orders} orders/day at ₹{calc_budget} daily budget (Target ROAS: {calc_target_roas:.2f}x, Max CPA: ₹{calc_target_cpa:.0f}).
                    Category Context & USPs: {cat_benchmarks['usp_prompt']}

                    {prompt_framework}

                    Maintain crisp, elite English with high conversion intent for direct Indian e-commerce buyers.
                    """

                    c_response_text = call_gemini_dynamic(copy_prompt)

                    st.session_state["generated_ad_copy"] = c_response_text
                    st.session_state["last_calc_payload"] = calc_payload
                    st.session_state["last_platform_choice"] = platform_choice
                    st.rerun()

                except Exception as e:
                    st.error(f"Copy Generation Error: {e}")

    if "generated_ad_copy" in st.session_state:
        st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
        
        pdf_c1, pdf_c2 = st.columns([1.6, 1.4])
        with pdf_c1:
            st.markdown(f"##### 📝 Deployment-Ready Asset Deck ({st.session_state.get('last_platform_choice', 'Ad Copy')})")
        with pdf_c2:
            brief_html = generate_copy_media_plan_html(
                st.session_state["last_calc_payload"],
                st.session_state["generated_ad_copy"],
                brand_name,
                calc_discount,
                calc_location,
                selected_category,
                st.session_state.get("last_platform_choice", "Omnichannel")
            )
            st.download_button(
                label="📄 Export A4 Plan (PDF)",
                data=brief_html,
                file_name=f"{brand_name}_Settings_and_Brief_{datetime.now().strftime('%d_%b')}.html",
                mime="text/html"
            )

        cleaned_copy = re.sub(r'\n{3,}', '\n\n', st.session_state['generated_ad_copy']).strip()
        st.markdown(f"""
        <div class="deck-card">
            {cleaned_copy}
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# TAB 3: CREATIVE SCORING & SAFE-ZONE STUDIO (PERFECTLY BALANCED COLUMNS)
# ==============================================================================
with nav_tab3:
    st.markdown("#### 🎨 Creative Scoring & Safe-Zone Studio")
    st.caption("Upload any static image (1:1, 4:5, 9:16) or video asset (MP4, MOV). The AI verifies dimensions, safe-zone clearance, hook strength, and grades compliance for Meta & Google Ads:")

    cr_col1, cr_col2 = st.columns([2, 1])
    with cr_col1:
        creative_file = st.file_uploader(
            "📤 Upload Ad Creative (Photo: JPG/PNG/WEBP or Video: MP4/MOV):",
            type=["png", "jpg", "jpeg", "webp", "mp4", "mov"],
            key="creative_eval_upload"
        )
    with cr_col2:
        intended_placement = st.selectbox(
            "🎯 Intended Main Placement:",
            [
                "📱 9:16 Instagram Reels & Stories",
                "🖼️ 4:5 Instagram & Facebook Feed",
                "⏹️ 1:1 Square Feed & Carousel",
                "🔍 Google Performance Max / Display Asset"
            ]
        )

    if creative_file is not None:
        file_ext = creative_file.name.split('.')[-1].lower()
        is_video = file_ext in ['mp4', 'mov']
        
        # PERFECTLY BALANCED 1:1.3 COLUMN RATIO TO ELIMINATE VOID
        preview_col, info_col = st.columns([1, 1.3])
        
        with preview_col:
            st.markdown("##### 👁️ Creative Asset Preview")
            if is_video:
                st.video(creative_file)
                detected_ratio = "9:16 Vertical Video" if "9:16" in intended_placement else "Standard Video"
                res_info = "Video Stream Loaded"
            else:
                img_obj = Image.open(creative_file)
                st.image(img_obj, use_container_width=True)
                w, h = img_obj.size
                calc_ratio = round(w / h, 2)
                if 0.50 <= calc_ratio <= 0.62:
                    detected_ratio = "9:16 Vertical (Reel/Story)"
                elif 0.75 <= calc_ratio <= 0.85:
                    detected_ratio = "4:5 Vertical Portrait (Feed)"
                elif 0.95 <= calc_ratio <= 1.05:
                    detected_ratio = "1:1 Square (Feed/Carousel)"
                elif calc_ratio > 1.5:
                    detected_ratio = "16:9 Landscape"
                else:
                    detected_ratio = f"{w}x{h} (Ratio {calc_ratio})"
                res_info = f"{w} × {h} px"

        # DENSE, INFORMATIVE SAAS COCKPIT (NO EMPTY SPACE)
        with info_col:
            st.markdown("##### 📐 Technical Specs & Safe-Zone Radar")
            
            # WIDGET 1: ASSET ATTRIBUTES GRID
            c_attr1, c_attr2 = st.columns(2)
            with c_attr1:
                st.markdown(f"""
                <div class="radar-box" style="padding:10px 14px;">
                    <span class="kpi-lbl">Asset Identifier</span>
                    <div style="font-weight:700; font-size:12px; margin-top:2px;">{creative_file.name[:25]}</div>
                    <span class="kpi-lbl" style="margin-top:8px; display:block;">Aspect Ratio</span>
                    <div style="font-weight:800; color:#818cf8; font-size:14px;">{detected_ratio}</div>
                </div>
                """, unsafe_allow_html=True)
            with c_attr2:
                st.markdown(f"""
                <div class="radar-box" style="padding:10px 14px;">
                    <span class="kpi-lbl">Resolution Matrix</span>
                    <div style="font-weight:700; font-size:12px; margin-top:2px;">{res_info}</div>
                    <span class="kpi-lbl" style="margin-top:8px; display:block;">Target Placement</span>
                    <div style="font-weight:800; color:#34d399; font-size:14px;">{intended_placement.split(' ')[1]}</div>
                </div>
                """, unsafe_allow_html=True)

            # WIDGET 2: VISUAL SAFE-ZONE RADAR MAP
            st.markdown("""
            <div class="radar-box">
                <span class="kpi-lbl" style="color:#cbd5e1; margin-bottom:8px; display:block;">🛡️ Mobile Safe-Zone Visual Grid</span>
                <div class="radar-zone zone-red">
                    <span>⛔ Top 14% Dead-Zone (0 - 268px)</span>
                    <span>Brand Avatar & Handle</span>
                </div>
                <div class="radar-zone zone-green">
                    <span>✅ Center 66% Golden Zone (268 - 1536px)</span>
                    <span>Primary Safe Zone (Text & Dress)</span>
                </div>
                <div class="radar-zone zone-red">
                    <span>⛔ Bottom 20% Dead-Zone (1536 - 1920px)</span>
                    <span>CTA Button & Audio Wave</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # WIDGET 3: LIVE PRE-AUDIT QUALITY CHECKLIST
            st.markdown("""
            <div class="radar-box" style="margin-bottom:0;">
                <span class="kpi-lbl" style="color:#cbd5e1; margin-bottom:6px; display:block;">⚡ D2C Conversion Pre-Check</span>
                <div style="font-size:11px; line-height:1.7; color:#94a3b8;">
                    • <b>Thumbstop Window:</b> First 2 seconds must interrupt feed scroll.<br>
                    • <b>Mute Readability:</b> 70%+ users watch without sound; bold text is mandatory.<br>
                    • <b>Contrast Rule:</b> Text overlay must have solid background pill/stroke.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 3-COLUMN PYTHON GRID FOR BULLETPROOF CENTERING
        _, c_btn_audit_cr, _ = st.columns([1, 2, 1])
        with c_btn_audit_cr:
            btn_audit_cr = st.button("🚀 AUDIT CREATIVE COMPLIANCE & SCORE PERFORMANCE")

        if btn_audit_cr:
            if not active_api_key:
                st.error("Please enter your Gemini API Key in the left sidebar!")
            else:
                with st.spinner("🤖 Analyzing visual composition, safe-zone text placement, and conversion power..."):
                    try:
                        cr_payload = []
                        if is_video:
                            creative_file.seek(0)
                            v_bytes = creative_file.read()
                            cr_payload.append(types.Part.from_bytes(data=v_bytes, mime_type=f"video/{file_ext}"))
                        else:
                            img_obj = Image.open(creative_file)
                            b_buf = io.BytesIO()
                            img_obj.convert('RGB').save(b_buf, format='JPEG')
                            cr_payload.append(types.Part.from_bytes(data=b_buf.getvalue(), mime_type='image/jpeg'))

                        cr_audit_prompt = f"""
                        You are an Elite Direct-Response Performance Creative Director for Indian D2C E-commerce.
                        Category: {selected_category}
                        Target Placement: {intended_placement}
                        Aspect Ratio: {detected_ratio}
                        Target Product AOV: ₹{target_aov}
                        Category USPs: {cat_benchmarks['usp_prompt']}

                        TASK:
                        Evaluate this creative against Meta Ads (Instagram Reels, Stories, Feeds) and Google Ads compliance and conversion rules.
                        Scoring instructions: Evaluate on a 1-10 scale. Center all scores around 5-7 (avoid extreme 1 or 10 scores). Keep all explanations concise and summarized, reducing verbosity by 50%.
                        
                        Return a STRICT JSON object in this exact schema:
                        {{
                            "overall_score": 6.8,
                            "redesigned_score": 8.4,
                            "aspect_ratio": "{detected_ratio}",
                            "safe_zone_verdict": "Clear pass or warning summary",
                            "scores": {{
                                "hook_strength": 6.5,
                                "safe_zone_clearance": 7.0,
                                "visual_clarity": 7.2,
                                "roas_potential": 6.8
                            }},
                            "safe_zone_critique": "Brief assessment of text overlay position vs UI buttons",
                            "roas_improvements": [
                                "Concise high-level lever 1",
                                "Concise high-level lever 2",
                                "Concise high-level lever 3"
                            ]
                        }}
                        Respond ONLY with the JSON object.
                        """

                        raw_cr_eval = call_gemini_dynamic(cr_audit_prompt, cr_payload)
                        clean_cr_json = extract_json(raw_cr_eval)
                        st.session_state["creative_eval_result"] = json.loads(clean_cr_json)
                        st.session_state["evaluated_asset_name"] = creative_file.name
                        st.session_state["evaluated_asset_type"] = "video" if is_video else "image"
                        st.rerun()

                    except Exception as ce:
                        st.error(f"Creative Audit Error: {ce}")

    # Display Creative Scoring Results
    if "creative_eval_result" in st.session_state:
        c_res = st.session_state["creative_eval_result"]
        scores = c_res.get("scores", {})
        
        st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
        st.markdown(f"##### 📊 Creative Performance Grade: `{st.session_state.get('evaluated_asset_name', 'Asset')}`")

        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        sc1.metric("Overall Creative Score", f"{c_res.get('overall_score', 6.8)} / 10", delta="Balanced Grade")
        sc2.metric("Hook / Thumbstop Strength", f"{scores.get('hook_strength', 6.5)} / 10")
        sc3.metric("Safe-Zone Clearance", f"{scores.get('safe_zone_clearance', 7.0)} / 10")
        sc4.metric("Visual Clarity & Contrast", f"{scores.get('visual_clarity', 7.2)} / 10")
        sc5.metric("ROAS Conversion Potential", f"{scores.get('roas_potential', 6.8)} / 10")

        st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)

        sc_col1, sc_col2 = st.columns(2)
        with sc_col1:
            st.markdown(f"""
            <div class="deck-card">
                <h5 style="color:#818cf8; margin-top:0;">🛡️ Safe-Zone & UI Overlay Analysis</h5>
                <p style="font-size:13px; line-height:1.5;">{c_res.get('safe_zone_critique', 'Safe-zone analyzed.')}</p>
                <span class="kpi-pill pill-blue">Status: {c_res.get('safe_zone_verdict', 'Pass')}</span>
            </div>
            """, unsafe_allow_html=True)

        with sc_col2:
            st.markdown("""
            <div class="deck-card">
                <h5 style="color:#34d399; margin-top:0;">📈 Levers to Scale Target ROAS</h5>
                <ul style="font-size:13px; margin-bottom:0;">
            """, unsafe_allow_html=True)
            for imp in c_res.get("roas_improvements", []):
                st.markdown(f"<li style='margin-bottom:4px;'>{imp}</li>", unsafe_allow_html=True)
            st.markdown("</ul></div>", unsafe_allow_html=True)

        # CENTERED REDESIGN BUTTON
        st.markdown("---")
        st.markdown("<div style='text-align:center;'><h5>⚡ Auto-Redesign & Maximum Compliance Engine</h5><p style='color:#94a3b8; font-size:12px;'>Re-engineer on-screen hook & overlay text into verified safe zones for maximum compliance:</p></div>", unsafe_allow_html=True)

        _, c_btn_redesign, _ = st.columns([1, 2, 1])
        with c_btn_redesign:
            btn_redesign = st.button("✨ REDESIGN TEXT & OPTIMIZE FOR MAXIMUM SCORE")

        if btn_redesign:
            if not active_api_key:
                st.error("Please enter your Gemini API Key in the left sidebar!")
            else:
                with st.spinner("✍️ Re-engineering on-screen text, safe-zone positioning, and high-converting hooks..."):
                    try:
                        redesign_prompt = f"""
                        You are a Legendary Direct-Response Creative Director for Indian D2C E-commerce.
                        Category: {selected_category}
                        Current Creative Score: {c_res.get('overall_score', 6.8)} / 10
                        Safe-zone Analysis: {c_res.get('safe_zone_critique', '')}
                        Target Placement: {intended_placement}
                        Target Product AOV: ₹{target_aov}
                        Category USPs: {cat_benchmarks['usp_prompt']}

                        TASK:
                        Redesign the textual and visual layout of this creative to maximize compliance and conversions (Target Score: {c_res.get('redesigned_score', 8.4)} / 10).
                        Keep narrative concise, focusing on direct directives:

                        ### 🎯 1. REDESIGNED ON-SCREEN TEXT & SAFE-ZONE COORDINATES
                        - Main Headline (Keep under 6 words, high pattern-interrupt).
                        - Exact Safe-Zone Coordinate Recommendation (e.g. Center Y=45% to Y=55%, X=Center, away from top 14% and bottom 20%).
                        - Background Pill / Stroke Styling Rule for 100% mobile readability.

                        ### 🎬 2. THREE (3) RE-ENGINEERED 3-SECOND VIRAL HOOKS
                        - Hook 1 (Pain-Point Angle).
                        - Hook 2 (Curiosity / Pattern-Interrupt Angle).
                        - Hook 3 (Social Proof / High-AOV Offer Angle).

                        ### 📝 3. COMPLIMENTARY AD COPY SUITE
                        - High-Converting Primary Text (Bulleted USPs + Offer Hook + Clear CTA).
                        - 2 Punchy Headlines (<30 chars).
                        - Recommended CTA Button.

                        Output in clean, punchy, high-impact English.
                        """

                        redesign_output = call_gemini_dynamic(redesign_prompt)
                        st.session_state["creative_redesign_text"] = redesign_output
                        st.rerun()

                    except Exception as re_err:
                        st.error(f"Redesign Error: {re_err}")

        # Display Redesigned Output with Anchored Top-Right Download
        if "creative_redesign_text" in st.session_state:
            st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
            
            rd_col1, rd_col2 = st.columns([1.6, 1.4])
            with rd_col1:
                st.markdown("##### 🚀 Optimized & Re-Engineered Creative Blueprint")
            with rd_col2:
                redesign_html = generate_creative_redesign_html(
                    c_res,
                    st.session_state["creative_redesign_text"],
                    st.session_state.get("evaluated_asset_name", "Creative_Asset")
                )
                st.download_button(
                    label="📄 Export Redesign Brief (PDF)",
                    data=redesign_html,
                    file_name=f"Redesign_Brief_{datetime.now().strftime('%d_%b')}.html",
                    mime="text/html"
                )

            cleaned_redesign = re.sub(r'\n{3,}', '\n\n', st.session_state["creative_redesign_text"]).strip()
            st.markdown(f"""
            <div class="deck-card" style="border-left:4px solid #10b981;">
                {cleaned_redesign}
            </div>
            """, unsafe_allow_html=True)
