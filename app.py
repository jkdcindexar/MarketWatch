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

# Page Config
st.set_page_config(page_title="Institutional Market Intelligence", page_icon="📈", layout="wide")

# Modern CSS Injection for Professional Aesthetic
st.markdown("""
    <style>
    .main {background-color: #0e1117;}
    .stApp {background-color: #0e1117;}
    div.stButton > button {width: 100%; border-radius: 5px; font-weight: bold;}
    .css-1r6slp0 {background-color: #1c2029; border: 1px solid #30363d; border-radius: 10px; padding: 20px;}
    .metric-card {background: #1c2029; padding: 15px; border-radius: 10px; border-left: 4px solid #4a90e2; margin-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# CORE FUNCTIONS
# =====================================================================
def load_portfolio_sheet(sheet_id: str, gid: str):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Spreadsheet connection error: {e}")
        return pd.DataFrame()

def fetch_full_articles(keyword: str):
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(keyword)}&hl=en-US&gl=US&ceid=US:en"
        with urllib.request.urlopen(url, timeout=5) as res:
            root = ET.fromstring(res.read())
            titles = [item.find('title').text for item in root.findall('.//item')[:3]]
            return f"Keywords: {keyword} | Headlines: {', '.join(titles)}"
    except: return f"News feed unavailable for {keyword}"

async def run_pipeline(keywords):
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        tasks = [loop.run_in_executor(pool, fetch_full_articles, kw) for kw in keywords]
        return await asyncio.gather(*tasks)

# =====================================================================
# UI INTERFACE
# =====================================================================
st.title("📈 Institutional Intelligence Terminal")

with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Gemini API Key", type="password")
    sheet_id = st.text_input("Sheet ID", value="16p_m-M3rW6BwMh9y8D38U_xJm-zN9FwQ6rS_7v2eA6A")
    gid = st.text_input("GID", value="0")
    run_btn = st.button("🚀 Initialize Market Analysis")

if run_btn and api_key:
    with st.spinner("Analyzing market vectors..."):
        df = load_portfolio_sheet(sheet_id, gid)
        news_data = asyncio.run(run_pipeline(["Federal Reserve", "US Inflation", "Tech Sector"]))
        
        # Header Row
        col1, col2 = st.columns([1, 3])
        with col1:
            st.subheader("🔍 Portfolio Watchlist")
            ticker_col = next((c for c in df.columns if c in ['Ticker', 'Symbol']), df.columns[0])
            price_col = next((c for c in df.columns if c in ['Price', 'Last']), df.columns[1])
            change_col = next((c for c in df.columns if c in ['1d Change', 'Change']), df.columns[2])
            
            for _, row in df.iterrows():
                p = row[price_col]
                c = float(str(row[change_col]).replace('%', ''))
                color = "green" if c >= 0 else "red"
                st.markdown(f"<div class='metric-card'><b>{row[ticker_col]}</b>: ${p} <span style='color:{color}'>{c}%</span></div>", unsafe_allow_html=True)

        with col2:
            st.subheader("📰 Market Macro Brief")
            st.info(f"**Brief:** Markets are currently observing heavy volatility driven by: {', '.join(news_data)}")
            
            st.subheader("🦅 PM Executive Summary")
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"Analyze this portfolio: {df.to_string()} and these trends: {news_data}. Write a 3-paragraph institutional briefing."
            )
            st.write(resp.text)
elif run_btn and not api_key:
    st.warning("Please provide a Gemini API Key to proceed.")
