import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="terminl.", layout="wide")

# Modern Institutional Styling
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #1a1a1a; font-family: 'Inter', sans-serif; }
    .logo { font-size: 28px; font-weight: 800; margin-bottom: 20px; }
    .perf-bar { display: flex; gap: 20px; padding: 15px; border-bottom: 1px solid #e0e0e0; margin-bottom: 20px; font-weight: 600; }
    .nav-card { padding: 10px; border: 1px solid #eee; border-radius: 4px; cursor: pointer; }
    </style>
""", unsafe_allow_html=True)

def get_asset_info(ticker_sym):
    try:
        t = yf.Ticker(ticker_sym)
        hist = t.history(period="1d")
        info = t.info
        # Return price, sector, and holders data
        return {
            "price": hist['Close'].iloc[-1] if not hist.empty else 0.0,
            "sector": info.get('sector', 'Uncategorized'),
            "holders": t.institutional_holders # Returns top holders
        }
    except:
        return {"price": 0.0, "sector": "Uncategorized", "holders": pd.DataFrame()}

# --- MAIN ENGINE ---
if 'auth' not in st.session_state:
    st.markdown("<div class='logo'>terminl.</div>", unsafe_allow_html=True)
    sid = st.text_input("google sheet id")
    if st.button("enter"):
        st.session_state.auth = True
        st.session_state.sid = sid
        st.rerun()
else:
    st.markdown("<div class='logo'>terminl.</div>", unsafe_allow_html=True)
    df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{st.session_state.sid}/export?format=csv&gid=0")
    
    # Process data with defensive defaults
    data_list = []
    for _, row in df.iterrows():
        meta = get_asset_info(row['Ticker'])
        data_list.append({**row, **meta})
    
    assets_df = pd.DataFrame(data_list)
    
    col_l, col_r = st.columns([1, 2])
    
    with col_l:
        st.subheader("watchlist")
        # Ensure 'sector' exists as a grouping key
        for sector, group in assets_df.groupby('sector'):
            with st.expander(f"{sector} ({len(group)})"):
                for _, item in group.iterrows():
                    st.markdown(f"<div class='nav-card'><b>{item['Security Name']}</b><br>${item['price']:.2f}</div>", unsafe_allow_html=True)
                    # Display top 3 holders if available
                    if not item['holders'].empty:
                        with st.expander("View Top Holders"):
                            st.table(item['holders'].head(3))

    with col_r:
        st.subheader("market commentary")
        st.write("Professional-grade synthesis of current market data and holdings distribution.")
        with st.expander("expand deep analysis"):
            st.write("Insert your detailed PM commentary here...")
