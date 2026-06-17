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

st.set_page_config(page_title="Market Intelligence Terminal", layout="wide")

# Modern Fintech UI Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0A0C10; color: #E6EDF3; }
    .asset-row { padding: 10px; border-bottom: 1px solid #21262D; display: flex; justify-content: space-between; }
    .change-pos { color: #34D399; } .change-neg { color: #F87171; }
    </style>
""", unsafe_allow_html=True)

def load_portfolio_sheet(sheet_id: str, gid: str):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Spreadsheet error: {e}")
        return None

def safe_convert(val):
    try: return float(str(val).replace('%', '').replace('$', '').replace(',', '').strip())
    except: return None

st.title("Market Intelligence Terminal")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    sheet_id = st.text_input("Sheet ID", value="16p_m-M3rW6BwMh9y8D38U_xJm-zN9FwQ6rS_7v2eA6A")
    gid = st.text_input("GID", value="0")
    run_btn = st.button("Initialize Analysis")

if run_btn and api_key:
    df = load_portfolio_sheet(sheet_id, gid)
    if df is not None:
        # Strict Column Validation
        ticker_col = next((c for c in df.columns if c.lower() in ['ticker', 'symbol']), None)
        price_col = next((c for c in df.columns if c.lower() in ['price', 'last']), None)
        change_col = next((c for c in df.columns if c.lower() in ['change', '1d change']), None)

        if not all([ticker_col, price_col, change_col]):
            st.error(f"Missing columns! Found: {list(df.columns)}. Please rename your columns to include 'Ticker', 'Price', and 'Change'.")
        else:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("Watchlist")
                for _, row in df.iterrows():
                    p_val = safe_convert(row[price_col])
                    c_val = safe_convert(row[change_col])
                    c_class = "change-pos" if (c_val or 0) >= 0 else "change-neg"
                    st.markdown(f"<div class='asset-row'><span>{row[ticker_col]}</span><span>${p_val:.2f} <span class='{c_class}'>{c_val:.2f}%</span></span></div>", unsafe_allow_html=True)
            
            with col2:
                st.subheader("Executive Commentary")
                client = genai.Client(api_key=api_key)
                resp = client.models.generate_content(model='gemini-2.5-flash', contents=f"Analyze: {df.to_string()}")
                st.write(resp.text)
