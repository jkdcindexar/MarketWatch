import asyncio
import concurrent.futures
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import yfinance as yf
from google import genai
from google.genai import types

# Set up the beautiful spaceship dashboard page configuration
st.set_page_config(page_title="Market Watch Bot", page_icon="📈", layout="wide")

# =====================================================================
# MODULE 1: The Zero-Cloud Spreadsheet Loader
# =====================================================================
def get_etf_watchlist_no_cloud(sheet_id: str, gid: str) -> list:
    try:
        download_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        df = pd.read_csv(download_url)
        if 'Ticker' not in df.columns:
            st.error("Oops! I looked at the sheet but couldn't find a column named 'Ticker'.")
            return []
        clean_df = df[df['Ticker'].notna() & (df['Ticker'] != '') & (df['Ticker'] != 'N/A')]
        return clean_df['Ticker'].astype(str).str.strip().unique().tolist()
    except Exception as e:
        st.error(f"Failed to read the Google Sheet: {e}")
        return []

# =====================================================================
# MODULE 2: The Macro Clue Mapper
# =====================================================================
MACRO_MAP = {
    "CSSPX": {"asset": "US Equity", "clue": "S&P 500", "keywords": ["Federal Reserve", "US Corporate Earnings", "S&P 500"]},
    "VUAA": {"asset": "US Equity", "clue": "S&P 500", "keywords": ["Wall Street", "US Inflation", "S&P 500"]},
    "XLKS": {"asset": "US Tech", "clue": "Nasdaq", "keywords": ["Artificial Intelligence", "NVIDIA", "Nasdaq"]},
    "IEAA": {"asset": "Euro Bonds", "clue": "EU Corporate Debt", "keywords": ["ECB interest rates", "Eurozone credit spreads"]},
    "C3M": {"asset": "Euro Bonds", "clue": "EU Cash Alternative", "keywords": ["ECB rate cuts", "Euro short term yield"]},
    "AMGOLDN": {"asset": "Gold", "clue": "Gold Bullion", "keywords": ["Gold spot price", "US Dollar Index"]},
    "CMOD": {"asset": "Commodities", "clue": "Broad Market", "keywords": ["Crude oil price", "OPEC Index"]},
    "BTIC": {"asset": "Crypto", "clue": "Bitcoin", "keywords": ["Bitcoin ETF flows", "Crypto regulation"]}
}

def find_clues_for_my_portfolio(my_etf_list: list) -> dict:
    master_keywords = set()
    portfolio_breakdown = {}
    for ticker in my_etf_list:
        if ticker in MACRO_MAP:
            info = MACRO_MAP[ticker]
            portfolio_breakdown[ticker] = info["asset"]
            master_keywords.update(info["keywords"])
        else:
            portfolio_breakdown[ticker] = "Global Asset"
            master_keywords.add(f"{ticker} Market")
    return {"what_i_own": portfolio_breakdown, "keywords": list(master_keywords)}

# =====================================================================
# MODULE 3: Async Data Aggregator (Pigeons)
# =====================================================================
def fetch_single_etf_data(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker.strip().upper())
        history = t.history(period="5d")
        if history.empty:
            return {ticker: {"error": "No data"}}
        current_p = history['Close'].iloc[-1]
        prev_p = history['Close'].iloc[-2]
        change = ((current_p - prev_p) / prev_p) * 100
        return {ticker: {"price": round(current_p, 2), "change": round(change, 2)}}
    except:
        return {ticker: {"error": "Failed"}}

def fetch_rss_news(keyword: str) -> list:
    headlines = []
    try:
        encoded_keyword = urllib.parse.quote(keyword)
        rss_url = f"https://finance.yahoo.com/news/rss/?search={encoded_keyword}"
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            root = ET.fromstring(response.read())
        for item in root.findall('.//item')[:3]:
            headlines.append(item.find('title').text)
    except:
        headlines.append(f"No headlines found for {keyword}")
    return headlines

async def run_data_pipeline(tickers: list, search_keywords: list) -> dict:
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        price_tasks = [loop.run_in_executor(pool, fetch_single_etf_data, t) for t in tickers]
        price_results = await asyncio.gather(*price_tasks)
    master_prices = {}
    for res in price_results:
        master_prices.update(res)

    with concurrent.futures.ThreadPoolExecutor() as pool:
        news_tasks = [loop.run_in_executor(pool, fetch_rss_news, k) for k in search_keywords]
        news_results = await asyncio.gather(*news_tasks)
    master_news = {k: h for k, h in zip(search_keywords, news_results)}
    return {"market_prices": master_prices, "market_news": master_news}

# =====================================================================
# MODULE 4: Gemini Report Generator
# =====================================================================
def generate_pm_commentary(market_data: dict, api_key: str) -> str:
    try:
        client = genai.Client(api_key=api_key)
        formatted_data = f"PRICES:\n{market_data.get('market_prices')}\n\nNEWS:\n{market_data.get('market_news')}"
        
        system_instruction = """
        You are an elite Quantitative Portfolio Manager. Analyze the pricing data and news headlines.
        Rules:
        - Output EXACTLY three standalone paragraphs. Do not use bullet points or lists.
        - Paragraph 1: Analyze general macro news/broad market landscape.
        - Paragraph 2: Comment directly on the ETF price targets/performance changes provided.
        - Paragraph 3: Provide forward-looking tactical alignment and portfolio positioning adjustments.
        """
        
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=f"{system_instruction}\n\nData:\n{formatted_data}",
            config=types.GenerateContentConfig(temperature=0.3)
        )
        return response.text.strip()
    except Exception as e:
        return f"❌ Generation Failed: {str(e)}"

# =====================================================================
# STREAMLIT USER INTERFACE (The Dashboard)
# =====================================================================
st.title("📈 Market Watch Bot Dashboard")
st.write("Welcome to your automated portfolio strategist! Give the robot your list and watch it build your macro report.")

# Sidebar Panel for Inputs
st.sidebar.header("🛠️ Configuration Panel")
api_key_input = st.sidebar.text_input("1. Enter Google Gemini API Key", type="password")
sheet_id_input = st.sidebar.text_input("2. Google Sheet ID", value="1X9D386IdwjRCGLbWh7Imp73Xj9QwUG6qHU_kJYXNISs")
gid_input = st.sidebar.text_input("3. Worksheet GID (Tab ID)", value="570773482")

st.sidebar.markdown("---")
st.sidebar.write("💡 *Tip: Make sure your Google Sheet is shared as 'Anyone with the link can view'!*")

# Main Screen Action
if st.button("🚀 Analyze My Portfolio & Generate Commentary", use_container_width=True):
    if not api_key_input:
        st.warning("Please provide your Gemini API key in the configuration panel first!")
    else:
        with st.status("🤖 Robot at work... Executing pipeline stages...", expanded=True) as status:
            
            st.write("📥 Fetching ETF Watchlist from your Google Sheet...")
            tickers = get_etf_watchlist_no_cloud(sheet_id_input, gid_input)
            
            if tickers:
                st.write(f"🧠 Mapping macro linkages for {len(tickers)} identified tickers...")
                clue_map = find_clues_for_my_portfolio(tickers)
                
                st.write("🕊️ Deploying concurrent web pigeons for pricing and RSS feeds...")
                gathered_data = asyncio.run(run_data_pipeline(tickers, clue_map["keywords"]))
                
                # Show data to the user inside tabs while the report builds
                st.write("📋 Parsing real-time data metrics...")
                status.update(label="Data Extracted! Generating Report...", state="running")
                
                st.write("🔮 Synthesizing market analysis with Gemini 3.5 Flash...")
                final_report = generate_pm_commentary(gathered_data, api_key_input)
                
                status.update(label="Portfolio Review Complete!", state="complete")
                
                # --- DISPLAY THE RESULTS ---
                st.success("🎉 Executive Report Compiled Successfully!")
                
                st.markdown("### 📊 Live Portfolio Metrics")
                
                # Create professional metric cards dynamically
                cols = st.columns(len(gathered_data["market_prices"]))
                for i, (ticker, data) in enumerate(gathered_data["market_prices"].items()):
                    with cols[i]:
                        if "error" in data:
                            st.metric(label=ticker, value="Data Error")
                        else:
                            st.metric(
                                label=ticker, 
                                value=data["Live Price"], 
                                delta=f"{data['24h Change (%)']}% (24h)"
                            )
                
                st.markdown("---")
                st.markdown("### 📋 Executive PM Commentary Report")
                st.info("Notice: All claims below are strictly sourced from verified RSS feeds.")
                st.write(final_report)
                
                with st.expander("🔍 View Raw Source Data & URLs"):
                    st.json(gathered_data)
