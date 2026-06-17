import streamlit as st
import pandas as pd
import yfinance as yf
import asyncio
from google import genai
from google.genai import types

st.set_page_config(page_title="Institutional Terminal", layout="wide")

# Light Mode Professional Styling
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    .stButton>button { background-color: #f0f2f6; border: 1px solid #ccc; color: #000; }
    .perf-bar { padding: 10px; border-radius: 4px; font-weight: bold; margin-bottom: 20px; }
    .green { color: #008000; } .red { color: #FF0000; }
    </style>
""", unsafe_allow_html=True)

# Function: Fetch Live Price
def get_live_data(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        curr = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change = ((curr - prev) / prev) * 100
        return curr, change
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
    
    # 1. Top Ribbon Performance
    st.markdown("<div class='perf-bar' style='background-color:#e8f5e9;'>Market Status: <span class='green'>Equities Up 0.4%</span> | <span class='red'>Bonds Down 0.1%</span></div>", unsafe_allow_html=True)
    
    # 2. Dropdown Watchlist
    with st.expander("Expand Portfolio Watchlist"):
        for _, row in df.iterrows():
            ticker = row['Ticker']
            price, change = get_live_data(ticker)
            if price:
                color = "green" if change >= 0 else "red"
                st.markdown(f"**{ticker}**: ${price:.2f} <span class='{color}'>({change:.2f}%)</span>", unsafe_allow_html=True)
    
    # 3. Market Commentary
    st.subheader("Executive Market Commentary")
    client = genai.Client(api_key=api_key)
    with st.spinner("Synthesizing market intelligence..."):
        resp = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Analyze portfolio: {df.to_string()}. Provide a 2-sentence market outlook and tactical positioning advice."
        )
        st.write(resp.text)
