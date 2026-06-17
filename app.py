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

# Page setup using a clean wide matrix
st.set_page_config(page_title="Market Intelligence Terminal", layout="wide")

# Minimalist Corporate Fintech Styling UI Override
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #0A0C10 !important;
        color: #E6EDF3 !important;
    }
    .stApp {
        background-color: #0A0C10;
    }
    section[data-testid="stSidebar"] {
        background-color: #0D1117 !important;
        border-right: 1px solid #21262D !important;
    }
    .sidebar-title {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #8B949E;
        font-weight: 600;
        margin-bottom: 15px;
    }
    .asset-row {
        padding: 8px 0px;
        border-bottom: 1px solid #21262D;
        font-size: 13px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .asset-label {
        font-weight: 500;
        color: #C9D1D9;
        max-width: 60%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .asset-metrics {
        text-align: right;
        font-family: monospace;
    }
    .change-positive {
        color: #34D399;
        font-weight: 500;
    }
    .change-negative {
        color: #F87171;
        font-weight: 500;
    }
    .market-brief-box {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 24px;
    }
    .ribbon-bar {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #8B949E;
        margin-top: 8px;
        border-top: 1px solid #21262D;
        padding-top: 8px;
    }
    div.stButton > button {
        background-color: #21262D !important;
        color: #C9D1D9 !important;
        border: 1px solid #30363D !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: background-color 0.2s ease;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #30363D !important;
        border-color: #8B949E !important;
    }
    h1, h2, h3 {
        color: #F0F6FC !important;
        font-weight: 600 !important;
    }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# DATA INGESTION ENGINE
# =====================================================================
def load_portfolio_sheet(sheet_id: str, gid: str) -> pd.DataFrame:
    """Downloads sheet and cleans up background trailing spaces."""
    try:
        download_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        df = pd.read_csv(download_url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Spreadsheet Link Connection Error: {e}")
        return pd.DataFrame()

def fetch_full_articles_for_keyword(keyword: str) -> list:
    """Scrapes underlying news bodies to parse depth context safely."""
    articles_data = []
    try:
        encoded_query = urllib.parse.quote(keyword)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        req = urllib.request.Request(rss_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            root = ET.fromstring(response.read())
            
        for item in root.findall('.//item')[:2]:
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            
            full_text = ""
            if link:
                try:
                    art_req = urllib.request.Request(link, headers=headers)
                    with urllib.request.urlopen(art_req, timeout=3) as art_res:
                        html = art_res.read().decode('utf-8', errors='ignore')
                        paragraphs = []
                        start = 0
                        while True:
                            start_idx = html.find('<p', start)
                            if start_idx == -1: break
                            tag_end = html.find('>', start_idx)
                            end_idx = html.find('</p>', tag_end)
                            if end_idx == -1: break
                            text_block = html[tag_end+1:end_idx]
                            while '<' in text_block and '>' in text_block:
                                s = text_block.find('<')
                                e = text_block.find('>')
                                text_block = text_block[:s] + text_block[e+1:]
                            if len(text_block.strip()) > 30:
                                paragraphs.append(text_block.strip())
                            start = end_idx + 4
                        full_text = "\n".join(paragraphs[:5])
                except:
                    full_text = title
                    
            articles_data.append(f"Title: {title}\nContent: {full_text if len(full_text) > 50 else title}")
        return articles_data
    except:
        return [f"No news gathered for vector: {keyword}"]

async def run_macro_news_pipeline(keywords: list) -> dict:
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [loop.run_in_executor(pool, fetch_full_articles_for_keyword, kw) for kw in keywords]
        results = await asyncio.gather(*tasks)
    return {kw: res for kw, res in zip(keywords, results)}

# =====================================================================
# DEFENSIVE VALUE CONVERTERS
# =====================================================================
def safe_float_convert(val) -> float:
    """Shields application against text strings matching in numerical loops."""
    if pd.isna(val):
        return 0.0
    try:
        cleaned = str(val).replace('%', '').replace('$', '').replace(',', '').strip()
        return float(cleaned)
    except ValueError:
        return None

# =====================================================================
# INTELLIGENCE SYNDICATION (AI EXECUTIVE GENERATORS)
# =====================================================================
def generate_top_summary(macro_news: dict, api_key: str) -> dict:
    """Generates the clean headline brief and the sector ribbon vector."""
    try:
        client = genai.Client(api_key=api_key)
        context = str(macro_news)
        
        prompt = f"""
        Analyze these news contexts and output a flat raw JSON object. Do not include markdown wraps or backticks.
        Required Keys:
        "headline": Exactly 1 or 2 high-level sentences capturing the primary global market narrative.
        "ribbon": A short, elegant performance ribbon text summarizing sectors (e.g., "Sectors: Tech, Financials leading | Energy lagging").
        
        Context: {context}
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json")
        )
        return json.loads(response.text.strip())
    except:
        return {
            "headline": "Broad macro assets consolidate as market systems assess global policy frameworks.",
            "ribbon": "Sectors: Mixed execution across major industrial lines"
        }

def generate_pm_report(portfolio_summary: str, macro_news: dict, api_key: str) -> str:
    try:
        client = genai.Client(api_key=api_key)
        system_instruction = """
        You are an Institutional Portfolio Manager. Generate a precise 3-paragraph executive brief.
        Do not use any lists, markdown bullet points, or introductory phrases.
        
        Structure Requirements:
        Paragraph 1: Macro & Broad Market Overview (Synthesizing news and core global macroeconomic conditions).
        Paragraph 2: Portfolio Exposure Impact (Connecting specific asset classes from the sheet directly to these shifts).
        Paragraph 3: Actionable PM Takeaways (Concrete, risk-adjusted positioning guidance).
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Portfolio Assets:\n{portfolio_summary}\n\nNews Data:\n{str(macro_news)}",
            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
        )
        return response.text.strip()
    except Exception as e:
        return f"AI Synthesis failed to construct report matrix: {str(e)}"

# =====================================================================
# INTERFACE IMPLEMENTATION
# =====================================================================
st.title("Market Intelligence Terminal")
st.markdown("<p style='color:#8B949E; margin-top:-15px;'>Quantitative Asset Tracking & Macro Synthesis Portfolio Dashboard</p>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<div class='sidebar-title'>Authentication & Access</div>", unsafe_allow_html=True)
    api_key_input = st.text_input("Gemini API Key", type="password")
    sheet_id_input = st.text_input("Google Sheet ID", value="16p_m-M3rW6BwMh9y8D38U_xJm-zN9FwQ6rS_7v2eA6A")
    gid_input = st.text_input("Sheet GID (Tab ID)", value="0")
    
    st.markdown("<br><div class='sidebar-title'>Watchlist Monitor</div>", unsafe_allow_html=True)
    watchlist_area = st.empty()
    watchlist_area.caption("Initialize pipeline execution to populate portfolio component metrics.")

if not api_key_input:
    st.info("System Standby: Authenticate via the secure sidebar panel to deploy infrastructure pipelines.")
else:
    if st.button("Execute Pipeline Analysis"):
        with st.status("Executing Analytics Array...", expanded=True) as status:
            
            st.write("Fetching source dataset ledgers...")
            df = load_portfolio_sheet(sheet_id_input, gid_input)
            
            if df.empty:
                status.update(label="Pipeline terminated: Ledger empty.", state="error")
            else:
                status.update(label="Processing Macro Context Strings...", state="running")
                
                # Intelligent Column Disambiguation Map
                ticker_col = next((c for c in df.columns if c.lower() in ['ticker', 'symbol', 'isin', 'code']), df.columns[0])
                name_col = next((c for c in df.columns if c.lower() in ['name', 'asset name', 'security', 'asset', 'description']), None)
                price_col = next((c for c in df.columns if c.lower() in ['price', 'last price', 'last', 'close']), None)
                change_col = next((c for c in df.columns if c.lower() in ['1d change', 'change', 'daily change', 'chg', 'chg%']), None)
                
                # Fetch News Payload based on global parameters
                search_targets = ["Federal Reserve Interest Rates", "US Inflation CPI", "Global Market Trends"]
                macro_news = asyncio.run(run_macro_news_pipeline(search_targets))
                
                st.write("Synthesizing multi-page textual bodies...")
                brief_payload = generate_top_summary(macro_news, api_key_input)
                executive_commentary = generate_pm_report(df.to_string(index=False), macro_news, api_key_input)
                
                status.update(label="Terminal Processing Concluded", state="complete")
                
                # --- SIDEBAR WATCHLIST DISPLAY BLOCK ---
                with watchlist_area.container():
                    for _, row in df.iterrows():
                        # Extract ticker if valid, fallback to asset description name text string
                        tick_raw = str(row[ticker_col]).strip() if ticker_col else "N/A"
                        if tick_raw.upper() in ["N/A", "", "NONE", "NULL"] and name_col:
                            label = str(row[name_col]).strip()
                        else:
                            label = tick_raw
                        
                        # Defensively convert metrics to float to eliminate parsing failures
                        p_float = safe_float_convert(row[price_col]) if price_col else None
                        c_float = safe_float_convert(row[change_col]) if change_col else None
                        
                        p_display = f"${p_float:,.2f}" if p_float is not None else str(row[price_col])
                        
                        if c_float is not None:
                            c_class = "change-positive" if c_float >= 0 else "change-negative"
                            sign = "+" if c_float > 0 else ""
                            c_display = f"<span class='{c_class}'>{sign}{c_float:.2f}%</span>"
                        else:
                            c_display = f"<span style='color:#8B949E;'>{str(row[change_col]) if change_col else '0.00%'}</span>"
                        
                        st.markdown(f"""
                            <div class='asset-row'>
                                <div class='asset-label'>{label}</div>
                                <div class='asset-metrics'>{p_display} | {c_display}</div>
                            </div>
                        """, unsafe_allow_html=True)
                
                # --- MAIN TERMINAL RENDER PANEL ---
                st.markdown(f"""
                    <div class='market-brief-box'>
                        <div style='font-size: 15px; font-weight: 400; line-height: 1.6; color: #C9D1D9;'>
                            {brief_payload.get('headline')}
                        </div>
                        <div class='ribbon-bar'>
                            {brief_payload.get('ribbon')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.subheader("Executive Portfolio Commentary Briefing")
                st.markdown(f"<div style='line-height:1.7; font-size:15px; color:#C9D1D9;'>{executive_commentary}</div>", unsafe_allow_html=True)
