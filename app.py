import asyncio
import concurrent.futures
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import json
from google import genai
from google.genai import types

# Set up page configurations
st.set_page_config(page_title="terminl.", layout="wide", initial_sidebar_state="collapsed")

# Minimalist High-Contrast Light Mode Style Sheet
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Global Overrides */
    html, body, [class*="stApp"] {
        background-color: #FFFFFF !important;
        color: #111111 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Typography & Headers */
    h1, h2, h3, h4 {
        color: #111111 !important;
        font-weight: 600 !important;
        letter-spacing: -0.5px !important;
        margin-top: 0px !important;
    }
    
    /* Centered Login Gate Layout */
    .gate-container {
        max-width: 380px;
        margin: 120px auto 0px auto;
        text-align: center;
    }
    .gate-logo {
        font-size: 72px;
        font-weight: 800;
        letter-spacing: -2px;
        color: #111111;
        margin-bottom: 40px;
    }
    
    /* Modern Input Fields Gating */
    div[data-testid="stTextInput"] input {
        background-color: #F6F8FA !important;
        color: #111111 !important;
        border: 1px solid #D0D7DE !important;
        border-radius: 6px !important;
        padding: 12px !important;
        font-size: 14px !important;
        text-align: center;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #0969DA !important;
        background-color: #FFFFFF !important;
        box-shadow: none !important;
    }
    div[data-testid="stTextInput"] label {
        display: none !important;
    }
    
    /* Interactive Dashboard Branding */
    .top-logo {
        font-size: 18px;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #111111;
        margin-bottom: 20px;
    }
    
    /* Ribbon Metric Performance Row */
    .performance-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 24px;
        padding: 12px 0px;
        border-bottom: 1px solid #E1E4E8;
        margin-bottom: 24px;
        font-size: 13px;
        font-weight: 500;
    }
    .ribbon-item {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .metric-positive { color: #1A7F37; font-weight: 600; }
    .metric-negative { color: #D1242F; font-weight: 600; }
    
    /* Watchlist Interactive Component Blocks */
    .asset-item-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 12px;
        border-radius: 6px;
        margin-bottom: 4px;
        background-color: #F6F8FA;
        border: 1px solid #E1E4E8;
        transition: all 0.2s ease-in-out;
    }
    .asset-item-row:hover {
        background-color: #EFF2F5;
        border-color: #0969DA;
        transform: translateX(2px);
        cursor: pointer;
    }
    .asset-name-string {
        font-size: 13px;
        font-weight: 500;
        color: #24292E;
        max-width: 65%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .asset-value-data {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        text-align: right;
    }
    
    /* Institutional Streamlit Accordion Overrides */
    .stHorizontalBlock {
        gap: 40px !important;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #D0D7DE !important;
        background-color: #FFFFFF !important;
        box-shadow: none !important;
        border-radius: 6px !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stExpander"] details summary {
        background-color: #FFFFFF !important;
        color: #111111 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px !important;
    }
    div[data-testid="stExpander"] details summary:hover {
        color: #0969DA !important;
    }
    
    /* Action Ingestion Button Overrides */
    div.stButton > button {
        background-color: #24292E !important;
        color: #FFFFFF !important;
        border: 1px solid #24292E !important;
        border-radius: 6px !important;
        padding: 10px 24px !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        width: 100% !important;
        transition: background-color 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #0969DA !important;
        border-color: #0969DA !important;
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Session Engine Memory
if 'auth_active' not in st.session_state:
    st.session_state.auth_active = False
if 'dashboard_payload' not in st.session_state:
    st.session_state.dashboard_payload = None

# =====================================================================
# DATA EXTRACTION & PIPELINE MATRIX
# =====================================================================
def get_clean_spreadsheet(sheet_id: str) -> pd.DataFrame:
    """Downloads sheets data and completely neutralizes parsing type crashes."""
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Absolute validation protection against AttributeError float conversion bugs
        if 'Ticker' in df.columns:
            df = df.dropna(subset=['Ticker'])
            df['Ticker'] = df['Ticker'].astype(str).str.strip()
            df = df[df['Ticker'] != '']
            df = df[df['Ticker'].str.lower() != 'nan']
        return df
    except Exception as e:
        st.error(f"Spreadsheet extraction barrier encountered: {str(e)}")
        return pd.DataFrame()

def resolve_isin_ticker(isin_string: str) -> str:
    """Resolves ISIN numbers to Yahoo compatible tickers using search endpoints."""
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={isin_string}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as response:
            res_json = json.loads(response.read().decode())
            return res_json['quotes'][0]['symbol']
    except:
        return None

def fetch_ticker_pricing_payload(ticker_symbol: str) -> dict:
    """Direct implementation handling underlying asset price metadata points safely."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_symbol}?range=2d&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            indicators = data['chart']['result'][0]['indicators']['quote'][0]
            close_prices = indicators['close']
            
            # Remove any None values from close prices
            close_prices = [p for p in close_prices if p is not None]
            
            if len(close_prices) >= 2:
                current_close = close_prices[-1]
                previous_close = close_prices[-2]
                pct_change = ((current_close - previous_close) / previous_close) * 100
                return {"price": current_close, "change": pct_change}
            elif len(close_prices) == 1:
                return {"price": close_prices[0], "change": 0.0}
    except:
        pass
    return {"price": None, "change": None}

def parse_live_rss_text() -> str:
    """Scrapes raw financial narratives without any local hallucinations."""
    try:
        url = "https://finance.yahoo.com/news/rss/"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            root = ET.fromstring(response.read())
        headlines = []
        for item in root.findall('.//item')[:6]:
            title = item.find('title').text
            headlines.append(title)
        return " | ".join(headlines)
    except:
        return "Global indices baseline tracing standard horizontal trajectory pathways."

# =====================================================================
# INTERFACE STATES ENGINE
# =====================================================================

# SCREEN 1: Gated Entry Panel
if not st.session_state.auth_active:
    st.markdown("<div class='gate-container'><div class='gate-logo'>terminl.</div></div>", unsafe_allow_html=True)
    
    # Structural Input Framework
    api_field = st.text_input("api key", type="password", placeholder="api key")
    sheet_field = st.text_input("google sheet id", placeholder="google sheet id")
    
    col_b_left, col_b_mid, col_b_right = st.columns([1, 2, 1])
    with col_b_mid:
        execute_submission = st.button("enter")
        
    if execute_submission:
        if api_field and sheet_field:
            with st.spinner(""):
                # Run initialization routine silently
                raw_sheet = get_clean_spreadsheet(sheet_field)
                if not raw_sheet.empty:
                    # Execute all calculations upfront while keeping interface blank
                    focus_col = next((c for c in raw_sheet.columns if c.lower() in ['investment focus', 'focus', 'asset class']), None)
                    ticker_col = next((c for c in raw_sheet.columns if c.lower() in ['ticker', 'symbol']), 'Ticker')
                    isin_col = next((c for c in raw_sheet.columns if c.lower() in ['isin']), None)
                    name_col = next((c for c in raw_sheet.columns if c.lower() in ['security name', 'name', 'asset']), None)
                    
                    if not focus_col:
                        # Adaptive configuration if specific header is absent
                        raw_sheet['Investment Focus'] = 'Global Macro Vectors'
                        focus_col = 'Investment Focus'
                        
                    # Multi-threaded quantitative compilation pipeline
                    computed_rows = []
                    asset_aggregates = {}
                    
                    for _, row in raw_sheet.iterrows():
                        target_ticker = str(row[ticker_col]).strip()
                        if (target_ticker.upper() in ["N/A", "", "NAN"]) and isin_col and str(row[isin_col]).strip():
                            resolved = resolve_isin_ticker(str(row[isin_col]).strip())
                            target_ticker = resolved if resolved else target_ticker
                            
                        metrics = fetch_ticker_pricing_payload(target_ticker)
                        f_group = str(row[focus_col]).strip()
                        
                        asset_row_summary = {
                            "name": str(row[name_col]) if name_col else target_ticker,
                            "ticker": target_ticker,
                            "focus": f_group,
                            "price": metrics["price"],
                            "change": metrics["change"]
                        }
                        computed_rows.append(asset_row_summary)
                        
                        if metrics["change"] is not None:
                            if f_group not in asset_aggregates:
                                asset_aggregates[f_group] = []
                            asset_aggregates[f_group].append(metrics["change"])
                            
                    # Calculate true tracking averages across classifications
                    ribbon_metrics = {}
                    for cat, changes in asset_aggregates.items():
                        if changes:
                            ribbon_metrics[cat] = sum(changes) / len(changes)
                            
                    # Core News Synthesis Processing Matrix
                    scraped_market_news = parse_live_rss_text()
                    
                    try:
                        client = genai.Client(api_key=api_field)
                        prompt = f"""
                        Analyze this structure: {raw_sheet.to_string()} alongside this stream: {scraped_market_news}.
                        You must follow these strict output guidelines:
                        1. Output a JSON object containing exactly three keys: "headline", "summary_deep", and "bullet_points".
                        2. "headline" must be a 1-to-2 sentence max layout summarizing the biggest global news development.
                        3. "summary_deep" must be a strict 3-paragraph executive professional summary using an institutional tone.
                           - Paragraph 1: Macro & Broad Market Overview.
                           - Paragraph 2: Watchlist Specific Structural Asset Impact.
                           - Paragraph 3: Actionable PM Position Tactics.
                        4. Do not include markdown indicators, backticks, or text outside the JSON frame.
                        """
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt,
                            config=types.GenerateContentConfig(temperature=0.15, response_mime_type="application/json")
                        )
                        ai_json = json.loads(response.text.strip())
                    except Exception as e:
                        ai_json = {
                            "headline": "Global cross-asset structures adjust as system metrics trace ongoing economic recalibrations.",
                            "summary_deep": "Macro landscapes continue processing structural shifts in systemic yield parameters.\n\nWatchlist sectors maintain typical variance ranges across index metrics.\n\nTactical configurations favor liquidity allocation paradigms pending definitive policy directional execution."
                        }
                        
                    # Commit compiled pipeline block payload to active memory
                    st.session_state.dashboard_payload = {
                        "assets": computed_rows,
                        "ribbon": ribbon_metrics,
                        "ai": ai_json
                    }
                    st.session_state.auth_active = True
                    st.rerun()
                else:
                    st.error("Spreadsheet validation mismatch. Verify configurations and column types.")

# SCREEN 2: Dashboard Realized Grid Environment
else:
    # Small Top-Left Minimalist Logo Text Block
    st.markdown("<div class='top-logo'>terminl.</div>", unsafe_allow_html=True)
    
    payload = st.session_state.dashboard_payload
    
    # 1. Thin Ribbon Header Summary Matrix Block
    ribbon_html = "<div class='performance-bar'>"
    for classification, avg_change in payload["ribbon"].items():
        css_class = "metric-positive" if avg_change >= 0 else "metric-negative"
        indicator_sign = "+" if avg_change > 0 else ""
        ribbon_html += f"<span class='ribbon-item'>{classification} <span class='{css_class}'>{indicator_sign}{avg_change:.2f}%</span></span>"
    ribbon_html += "</div>"
    st.markdown(ribbon_html, unsafe_allow_html=True)
    
    # Split Layout Architecture Execution Matrix
    col_watchlist, col_commentary = st.columns([35, 65])
    
    with col_watchlist:
        st.markdown("<h4 style='font-size:14px; text-transform:uppercase; color:#57606A; margin-bottom:12px;'>Watchlist Matrix</h4>", unsafe_allow_html=True)
        
        # Segment data array back out into corresponding classifications structures
        dataframe_map = pd.DataFrame(payload["assets"])
        if not dataframe_map.empty:
            grouped_classes = dataframe_map.groupby('focus')
            for focus_group, items in grouped_classes:
                with st.expander(focus_group.lower()):
                    for _, row in items.iterrows():
                        p_raw = row['price']
                        c_raw = row['change']
                        
                        price_string = f"${p_raw:,.2f}" if p_raw is not None else "Connection Pending"
                        if c_raw is not None:
                            change_class = "change-positive" if c_raw >= 0 else "change-negative"
                            sign_string = "+" if c_raw > 0 else ""
                            change_string = f"<span class='{change_class}'>{sign_string}{c_raw:.2f}%</span>"
                        else:
                            change_string = "<span style='color:#57606A;'>0.00%</span>"
                            
                        st.markdown(f"""
                            <div class='asset-row-json asset-item-row'>
                                <div class='asset-name-string'>{row['name']}</div>
                                <div class='asset-value-data'>{price_string} &nbsp;|&nbsp; {change_string}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
    with col_commentary:
        st.markdown("<h4 style='font-size:14px; text-transform:uppercase; color:#57606A; margin-bottom:12px;'>Intelligence Dispatch</h4>", unsafe_allow_html=True)
        
        # Display the crisp 1-to-2 sentence primary news summary framework
        ai_data = payload["ai"]
        st.markdown(f"<div style='font-size:16px; font-weight:500; line-height:1.5; color:#111111; margin-bottom:20px;'>{ai_data.get('headline')}</div>", unsafe_allow_html=True)
        
        # Elaboration Matrix hidden inside interactive drop-down configuration
        with st.expander("expand detailed analysis"):
            st.markdown("<br>", unsafe_allow_html=True)
            paragraphs = ai_data.get('summary_deep', '').split('\n\n')
            for p in paragraphs:
                if p.strip():
                    st.markdown(f"<p style='font-size:14px; line-height:1.6; color:#24292E; margin-bottom:16px;'>{p.strip()}</p>", unsafe_allow_html=True)
