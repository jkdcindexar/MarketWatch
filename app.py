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
st.set_page_config(page_title="Terminal", layout="wide")

# Modern, High-Contrast "Midnight" CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&family=JetBrains+Mono&display=swap');
    
    html, body, [class*="st"] { font-family: 'Inter', sans-serif; background-color: #050505; color: #E0E0E0; }
    
    .terminal-card { 
        background: #0d0d0d; border: 1px solid #262626; border-radius: 8px; 
        padding: 20px; margin-bottom: 15px; 
    }
    
    .ticker-header { font-family: 'JetBrains Mono', monospace; font-size: 1.1em; color: #ffffff; }
    .metric-up { color: #4ade80; font-weight: 700; }
    .metric-down { color: #f87171; font-weight: 700; }
    
    .stButton>button { 
        background: #171717; border: 1px solid #404040; color: #fafafa; border-radius: 4px;
        width: 100%; padding: 10px; font-weight: 600; 
    }
    .stButton>button:hover { background: #262626; }
    
    h1, h2, h3 { color: #ffffff !important; letter-spacing: -0.5px; }
    </style>
""", unsafe_allow_html=True)

def load_data(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

# Layout
st.title("Market Intelligence Terminal")
st.markdown("---")

with st.sidebar:
    st.header("Terminal Config")
    api_key = st.text_input("Gemini API Key", type="password")
    sheet_id = st.text_input("Sheet ID", value="16p_m-M3rW6BwMh9y8D38U_xJm-zN9FwQ6rS_7v2eA6A")
    gid = st.text_input("GID", value="0")
    run_btn = st.button("Initialize Pipeline")

if run_btn and api_key:
    df = load_data(sheet_id, gid)
    
    # Map your specific columns to the logic
    # We use 'Security Name' as primary if Ticker is missing
    ticker_col = 'Ticker' if 'Ticker' in df.columns else 'Security Name'
    # Since your sheet lacks Price/Change, we provide placeholder metrics
    price_col = 'Volatility 1Y' # Using Volatility as a proxy for the demo
    change_col = 'Exp Ratio (TER)' 

    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Asset Watchlist")
        for _, row in df.iterrows():
            st.markdown(f"""
                <div class='terminal-card'>
                    <div class='ticker-header'>{row[ticker_col]}</div>
                    <div style='font-size: 0.9em; margin-top: 5px;'>
                        Stat: {row[price_col]} | Ratio: <span class='metric-up'>{row[change_col]}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
    with col2:
        st.subheader("Executive Macro Intelligence")
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Analyze this portfolio structure: {df.to_string()}. Provide a high-level institutional macro outlook."
        )
        st.markdown(f"<div class='terminal-card'>{resp.text}</div>", unsafe_allow_html=True)
