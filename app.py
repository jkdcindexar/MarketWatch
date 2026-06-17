import asyncio
import concurrent.futures
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# Set up the dashboard page configuration
st.set_page_config(page_title="Market Watch Bot", page_icon="📈", layout="wide")

st.title("📈 Elite Portfolio & Macro Analyzer")
st.caption("Failsafe Edition - Deep-Article Intelligence Processor")

# =====================================================================
# MODULE 1: Spreadsheet Data Loader (Failsafe Ticker/ISIN Parser)
# =====================================================================
def load_portfolio_sheet(sheet_id: str, gid: str) -> pd.DataFrame:
    """
    Downloads and sanitizes the user portfolio without requiring Google Cloud APIs.
    Supports either Ticker or ISIN columns smoothly.
    """
    try:
        download_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        df = pd.read_csv(download_url)
        
        # Strip string whitespace across headers
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Failed to read the Google Sheet: {e}")
        return pd.DataFrame()

# =====================================================================
# MODULE 2: Deep-Text News Pipeline (Fetches & Extracts Full Article Data)
# =====================================================================
def fetch_full_articles_for_keyword(keyword: str) -> list:
    """
    Queries Google News, extracts primary source article URLs, 
    and downloads full text bodies instead of simple headline strings.
    """
    articles_data = []
    try:
        encoded_query = urllib.parse.quote(keyword)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        req = urllib.request.Request(rss_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        
        # Scan the top 3 deep articles to avoid overwhelming tokens while maintaining depth
        for item in root.findall('.//item')[:3]:
            title = item.find('title').text if item.find('title') is not None else "No Title"
            link = item.find('link').text if item.find('link') is not None else ""
            
            # Attempt deep scrape of full article text body
            full_text = ""
            if link:
                try:
                    art_req = urllib.request.Request(link, headers=headers)
                    with urllib.request.urlopen(art_req, timeout=5) as art_res:
                        html = art_res.read().decode('utf-8', errors='ignore')
                        # Quick native extract of paragraph tags to avoid heavy dependencies like bs4
                        paragraphs = []
                        start = 0
                        while True:
                            start_idx = html.find('<p', start)
                            if start_idx == -1:
                                break
                            tag_end = html.find('>', start_idx)
                            end_idx = html.find('</p>', tag_end)
                            if end_idx == -1:
                                break
                            text_block = html[tag_end+1:end_idx]
                            # Clean primitive HTML tags out
                            while '<' in text_block and '>' in text_block:
                                s = text_block.find('<')
                                e = text_block.find('>')
                                text_block = text_block[:s] + text_block[e+1:]
                            if len(text_block.strip()) > 30:
                                paragraphs.append(text_block.strip())
                            start = end_idx + 4
                        full_text = "\n".join(paragraphs[:8]) # Extract first 8 meaningful paragraphs
                except:
                    full_text = "Full body pull blocked by publisher privacy walls. Relying on baseline context."
            
            combined_body = f"Source Title: {title}\nLink: {link}\nDeep Contents:\n{full_text if len(full_text) > 100 else title}"
            articles_data.append(combined_body)
            
        return articles_data
    except Exception as e:
        return [f"Macro engine gathering failed for keyword '{keyword}': {str(e)}"]

async def run_macro_news_pipeline(search_keywords: list) -> dict:
    """Runs keyword deep text collection concurrently via workers."""
    loop = asyncio.get_event_loop()
    master_news = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        tasks = [
            loop.run_in_executor(pool, fetch_full_articles_for_keyword, kw)
            for kw in search_keywords
        ]
        results = await asyncio.gather(*tasks)
        
    for keyword, contents in zip(search_keywords, results):
        master_news[keyword] = contents
        
    return master_news

# =====================================================================
# MODULE 3: Intelligence System (Strict Executive Prompt)
# =====================================================================
def generate_pm_commentary(portfolio_summary: str, macro_news: dict, api_key: str) -> str:
    """Passes portfolio layout and long full-article text straight to Gemini."""
    try:
        client = genai.Client(api_key=api_key)
        
        formatted_news = ""
        for kw, articles in macro_news.items():
            formatted_news += f"\n=== MACRO KEYWORD TARGET: {kw} ===\n"
            formatted_news += "\n---\n".join(articles) + "\n"
            
        system_instruction = """
        You are a Senior Quantitative Macro Portfolio Manager. Your job is to read through raw structural assets and matching extracted deep news articles to write a high-level briefing.
        
        Strict Guidelines:
        1. Base your answers entirely on the structural data provided.
        2. Never invent or assume numerical percentages or movements if they are absent from the context.
        3. Break down the assessment cleanly into 3 structured executive paragraphs:
           - Paragraph 1: Macro Context (Synthesize what the full articles indicate about rates, inflation, or political changes).
           - Paragraph 2: Portfolio Exposure Impact (Evaluate how your fixed assets, equites, or international holdings cross-examine with these discoveries).
           - Paragraph 3: Defensive Action Tactics (Concrete risk mitigation or positioning steps based purely on your expertise).
        """
        
        user_prompt = f"""
        Here is the user's current static portfolio data:
        {portfolio_summary}
        
        Here are the completely extracted news articles from global macro feeds:
        {formatted_news}
        
        Generate the executive commentary according to your system mandate.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            )
        )
        return response.text.strip()
    except Exception as e:
        return f"❌ AI Generation Engine Failed: {str(e)}"

# =====================================================================
# MODULE 4: Streamlit UI Implementation
# =====================================================================
with st.sidebar:
    st.header("🔑 Authentication & Source Links")
    api_key_input = st.text_input("Gemini API Key", type="password", help="Input your free Gemini API key here")
    
    st.markdown("---")
    st.subheader("📊 Google Sheets Configurations")
    sheet_id_input = st.text_input("Google Sheet ID", value="16p_m-M3rW6BwMh9y8D38U_xJm-zN9FwQ6rS_7v2eA6A", help="The long random string in your sheet URL")
    gid_input = st.text_input("Sheet GID (Tab ID)", value="0", help="The numbers following 'gid=' at the very end of your URL")

if not api_key_input:
    st.info("💡 Welcome! Please provide your Gemini API Key in the left sidebar configuration panel to turn on the processing engine.")
else:
    if st.button("🚀 Analyze Portfolio & Read Full Articles"):
        with st.status("⚙️ Processing Data Pipeline...", expanded=True) as status:
            st.write("📂 Connecting to Google Sheets link...")
            raw_data = load_portfolio_sheet(sheet_id_input, gid_input)
            
            if raw_data.empty:
                status.update(label="Spreadsheet Loading Failed!", state="error")
            else:
                st.write(f"🎉 Successfully imported table with {len(raw_data)} assets.")
                
                # Identify Column Mapping Options (Ticker vs ISIN fallback)
                id_col = None
                for col in ['ISIN', 'Ticker', 'Asset', 'Symbol']:
                    if col in raw_data.columns:
                        id_col = col
                        break
                
                if id_col is None:
                    st.error(f"Could not automatically detect identification flags. Columns found: {list(raw_data.columns)}")
                    status.update(label="Mapping Error", state="error")
                else:
                    st.write(f"🔍 Mapping structural macroeconomic linkages using the '{id_col}' tracking column...")
                    
                    # Convert static table into string format for the AI model
                    portfolio_summary = raw_data.to_string(index=False)
                    
                    # Determine general search keywords to build deep targets safely
                    search_keywords = ["Federal Reserve Interest Rates", "US Inflation CPI", "Wall Street Market Momentum", "European Central Bank Policy"]
                    
                    st.write("🕊️ Deploying network pigeons to extract and read full-text articles...")
                    macro_news = asyncio.run(run_macro_news_pipeline(search_keywords))
                    
                    st.write("🔮 Synthesizing multi-page content vectors with Gemini 2.5 Flash...")
                    final_report = generate_pm_commentary(portfolio_summary, macro_news, api_key_input)
                    
                    status.update(label="Portfolio Evaluation Matrix Finalized!", state="complete")
                    
                    # --- DISPLAY RESULTS PANEL ---
                    st.success("🎉 Custom Portfolio Executive Commentary Completed!")
                    
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.subheader("📋 Parsed Structural Assets")
                        st.dataframe(raw_data, use_container_width=True, hide_index=True)
                        
                    with col2:
                        st.subheader("🦅 Executive Portfolio Manager Report")
                        st.markdown(final_report)
