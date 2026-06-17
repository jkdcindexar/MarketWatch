import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="terminl.", layout="wide")

# Modern, larger, interactive styling
st.markdown("""
    <style>
    .main { font-size: 18px; }
    .logo { font-size: 80px; font-weight: 800; text-align: center; margin-top: 50px; }
    .input-box { width: 400px !important; margin: 0 auto; }
    .perf-bar { display: flex; justify-content: space-around; background: #f8f9fa; padding: 15px; border-radius: 8px; font-weight: bold; }
    .asset-card { padding: 15px; border: 1px solid #ddd; border-radius: 8px; transition: 0.3s; }
    .asset-card:hover { background-color: #f0f7ff; cursor: pointer; border-color: #007bff; }
    </style>
""", unsafe_allow_html=True)

if 'init' not in st.session_state:
    st.session_state.init = False

if not st.session_state.init:
    st.markdown("<div class='logo'>terminl.</div>", unsafe_allow_html=True)
    with st.container():
        api = st.text_input("api key", type="password")
        sid = st.text_input("sheet id")
        if st.button("enter"):
            st.session_state.update({'api': api, 'sid': sid, 'init': True})
            st.rerun()
else:
    st.markdown("<div style='font-size: 20px; font-weight: bold;'>terminl.</div>", unsafe_allow_html=True)
    df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{st.session_state.sid}/export?format=csv&gid=0")
    df.columns = [c.strip() for c in df.columns]

    # Performance Bar
    st.markdown("<div class='perf-bar'><span>Equities +0.2%</span><span>Crypto +1.5%</span><span>Tech +0.8%</span><span>Bonds -0.1%</span></div>", unsafe_allow_html=True)

    # Interactive Watchlist
    st.subheader("watchlist")
    cols = st.columns(4)
    for i, (_, row) in enumerate(df.iterrows()):
        t = yf.Ticker(row['Ticker'])
        hist = t.history(period='1d')
        # Defensive check for IndexError
        if not hist.empty:
            price = hist['Close'].iloc[-1]
            with cols[i % 4]:
                st.markdown(f"<div class='asset-card'><b>{row['Security Name']}</b><br>${price:.2f}</div>", unsafe_allow_html=True)
        else:
            with cols[i % 4]:
                st.markdown(f"<div class='asset-card'><b>{row['Security Name']}</b><br>N/A</div>", unsafe_allow_html=True)

    # Note: To show ETF holdings percentages, you would require an external API 
    # like 'Alpha Vantage' or 'Morningstar' as yfinance does not provide full holdings data.
