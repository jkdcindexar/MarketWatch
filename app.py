import streamlit as st
import pandas as pd
import yfinance as yf
import requests

st.set_page_config(page_title="terminl.", layout="wide")

# Institutional Styling
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #1a1a1a; font-family: 'Inter', sans-serif; }
    .logo { font-size: 28px; font-weight: 800; margin-bottom: 20px; }
    .perf-bar { display: flex; gap: 20px; padding: 15px; border-bottom: 1px solid #e0e0e0; margin-bottom: 20px; font-size: 14px; font-weight: 600; }
    .nav-card { padding: 12px; border: 1px solid #eee; border-radius: 6px; margin-bottom: 8px; cursor: pointer; transition: 0.2s; }
    .nav-card:hover { background-color: #f0f7ff; border-color: #007bff; }
    </style>
""", unsafe_allow_html=True)

def get_ticker_meta(isin_or_ticker):
    """Resolves ISIN to Ticker and fetches Sector/Price."""
    try:
        # Resolve to ticker if input looks like an ISIN
        if len(isin_or_ticker) > 10:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={isin_or_ticker}"
            resp = requests.get(url, timeout=5).json()
            ticker = resp['quotes'][0]['symbol']
        else:
            ticker = isin_or_ticker
        
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "ticker": ticker,
            "price": t.history(period="1d")['Close'].iloc[-1],
            "sector": info.get('sector', 'General Macro')
        }
    except: return None

# Entry Screen
if 'auth' not in st.session_state:
    st.markdown("<div class='logo'>terminl.</div>", unsafe_allow_html=True)
    key = st.text_input("api key", type="password")
    sid = st.text_input("sheet id")
    if st.button("enter"):
        st.session_state.auth = True
        st.session_state.sid = sid
        st.rerun()
else:
    st.markdown("<div class='logo'>terminl.</div>", unsafe_allow_html=True)
    
    # 1. Performance Ribbon
    st.markdown("<div class='perf-bar'>Equities: <span style='color:green'>+0.4%</span> | Crypto: <span style='color:green'>+1.2%</span> | Bonds: <span style='color:red'>-0.3%</span></div>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns([1, 2])
    
    # Load Sheet
    df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{st.session_state.sid}/export?format=csv&gid=0")
    
    with col_l:
        st.subheader("watchlist")
        # Organize by Asset Class
        processed_data = []
        for _, row in df.iterrows():
            meta = get_ticker_meta(row.get('ISIN', row.get('Ticker')))
            if meta: processed_data.append({**row, **meta})
        
        assets_df = pd.DataFrame(processed_data)
        for sector, group in assets_df.groupby('sector'):
            with st.expander(sector):
                for _, item in group.iterrows():
                    st.markdown(f"<div class='nav-card'><b>{item['Security Name']}</b><br>${item['price']:.2f}</div>", unsafe_allow_html=True)

    with col_r:
        st.subheader("market commentary")
        st.write("### Strategic Market Outlook")
        st.write("The current macro landscape reflects tight labor markets and persistent structural inflation, requiring defensive portfolio adjustments.")
        
        with st.expander("expand detailed analysis"):
            st.write("Paragraph 1: Executive macro outlook and global liquidity status...")
            st.write("Paragraph 2: Detailed asset class sensitivity analysis...")
            st.write("Paragraph 3: Tactical portfolio manager recommendations and positioning...")
            st.write("Paragraph 4: Risk mitigation strategies for upcoming quarterly windows...")
