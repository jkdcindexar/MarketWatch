import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from google import genai
from google.genai import types

# Page Config
st.set_page_config(page_title="Executive Market Terminal", layout="wide")

# Light Mode Professional Styling
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #1A1A1A; font-family: sans-serif; }
    .perf-bar { padding: 12px; border: 1px solid #E0E0E0; border-radius: 6px; background-color: #F8F9FA; margin-bottom: 20px; font-size: 0.9em; }
    .green { color: #008000; font-weight: bold; } 
    .red { color: #C0392B; font-weight: bold; }
    .asset-row { border-bottom: 1px solid #EEE; padding: 8px 0; display: flex; justify-content: space-between; }
    </style>
""", unsafe_allow_html=True)

def resolve_isin_to_ticker(isin):
    """Fallback: Maps ISIN to Yahoo-compatible ticker symbol."""
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={isin}"
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
        return resp['quotes'][0]['symbol']
    except: return None

def get_live_data(identifier):
    """Fetches price using identifier (resolves ISIN first)."""
    ticker_sym = resolve_isin_to_ticker(identifier) if len(identifier) > 10 else identifier
    if not ticker_sym: return None, None
    try:
        t = yf.Ticker(ticker_sym)
        hist = t.history(period="2d")
        if len(hist) < 2: return None, None
        curr, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
        return curr, ((curr - prev) / prev) * 100
    except: return None, None

st.title("Executive Market Terminal")

with st.sidebar:
    st.header("Terminal Configuration")
    api_key = st.text_input("Gemini API Key", type="password")
    sheet_id = st.text_input("Google Sheet ID")
    gid = st.text_input("Sheet GID")
    run_btn = st.button("Initialize Terminal")

if run_btn and api_key and sheet_id:
    # Load Data
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    df = pd.read_csv(url)
    df.columns = [str(c).strip() for c in df.columns]
    
    # 1. Performance Ribbon
    st.markdown("<div class='perf-bar'>Market Status: <b>Equities</b> <span class='green'>+0.4%</span> | <b>Fixed Income</b> <span class='red'>-0.1%</span> | <b>Commodities</b> <span class='green'>+0.2%</span></div>", unsafe_allow_html=True)
    
    # 2. Portfolio Watchlist
    st.subheader("Portfolio Assets")
    for _, row in df.iterrows():
        id_val = str(row.get('ISIN', row.get('Ticker', '')))
        price, change = get_live_data(id_val)
        if price:
            color = "green" if change >= 0 else "red"
            st.markdown(f"<div class='asset-row'><span>{row.get('Security Name', id_val)}</span><span>${price:.2f} <span class='{color}'>({change:.2f}%)</span></span></div>", unsafe_allow_html=True)
    
    # 3. Dropdown Commentary
    with st.expander("Expand Executive Market Analysis"):
        st.subheader("Tactical Positioning & Commentary")
        client = genai.Client(api_key=api_key)
        with st.spinner("Synthesizing market intelligence..."):
            resp = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"Analyze portfolio: {df.to_string()}. Provide 3-paragraph institutional briefing: Macro context, Portfolio exposure, and Defensive tactics."
            )
            st.write(resp.text)
