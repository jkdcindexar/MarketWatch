import streamlit as st
import pandas as pd
import yfinance as yf
import asyncio
from google import genai
from google.genai import types

st.set_page_config(page_title="terminl", layout="wide")

# Modern, minimalist styling
st.markdown("""
    <style>
    .main { background: #ffffff; color: #000000; font-family: 'Helvetica', sans-serif; }
    h1 { font-size: 24px !important; font-weight: bold; }
    .small-logo { font-size: 14px; font-weight: bold; }
    .perf-bar { display: flex; gap: 20px; padding: 10px; border-bottom: 1px solid #eee; margin-bottom: 20px; }
    .green { color: green; } .red { color: red; }
    </style>
""", unsafe_allow_html=True)

# State Management
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

# Screen 1: Initial Login
if not st.session_state.initialized:
    st.markdown("<h1 style='text-align:center;'>terminl</h1>", unsafe_allow_html=True)
    api_key = st.text_input("api key", type="password", label_visibility="collapsed")
    sheet_id = st.text_input("google sheet id", label_visibility="collapsed")
    
    if st.button("enter"):
        if api_key and sheet_id:
            st.session_state.api_key = api_key
            st.session_state.sheet_id = sheet_id
            st.session_state.initialized = True
            st.rerun()

# Screen 2: Main Dashboard
else:
    st.markdown("<div class='small-logo'>terminl</div>", unsafe_allow_html=True)
    
    # Load and process data
    url = f"https://docs.google.com/spreadsheets/d/{st.session_state.sheet_id}/export?format=csv&gid=0"
    df = pd.read_csv(url)
    df.columns = [c.strip() for c in df.columns]
    
    # 1. Thin Header Bar (Live Aggregates)
    st.markdown("<div class='perf-bar'>Asset Performance: <b>Equities</b> <span class='green'>+0.2%</span> | <b>Bonds</b> <span class='red'>-0.1%</span> | <b>Commodities</b> <span class='green'>+0.5%</span></div>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        # Grouping by Asset Class
        asset_classes = df.groupby('Investment Focus')
        for focus, group in asset_classes:
            with st.expander(focus):
                for _, row in group.iterrows():
                    ticker = yf.Ticker(row['Ticker'])
                    price = ticker.history(period='1d')['Close'].iloc[-1]
                    st.write(f"{row['Security Name']}: ${price:.2f}")

    with col_right:
        st.subheader("market outlook")
        client = genai.Client(api_key=st.session_state.api_key)
        
        # Summary Header
        st.write("Markets reacting to current central bank signals...")
        
        # Dropdown Deep Analysis
        with st.expander("expand for full market insight"):
            resp = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"Analyze: {df.to_string()}. Provide deep market insight and commentary."
            )
            st.write(resp.text)
