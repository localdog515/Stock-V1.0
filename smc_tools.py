import yfinance as yf
import pandas as pd
import numpy as np
import requests
import sqlite3
import re
from datetime import datetime

# ==========================================
# 1. 靜態資源 (CSS & Wiki)
# ==========================================
UI_CSS = """
<style>
    :root {
        --bg-app: #0b0e11; --bg-panel: #15191e; --bg-input: #21262d;
        --text-main: #e6edf3; --text-sub: #8b949e;
        --accent-blue: #44a4f2; --accent-orange: #d29922; --border: #30363d;
    }
    .stApp { background-color: var(--bg-app); color: var(--text-main); }
    .stTextInput > div > div > input, .stSelectbox > div > div {
        background-color: var(--bg-input) !important; color: var(--text-main) !important;
        border: 1px solid #58a6ff !important; border-radius: 6px;
    }
    .dd-box {
        background-color: #161b22; border: 1px solid var(--border);
        border-radius: 8px; padding: 20px; margin-bottom: 16px;
    }
    .dd-header {
        color: var(--accent-blue); font-size: 0.95rem; font-weight: 800;
        text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px;
        border-bottom: 1px solid #30363d; padding-bottom: 5px;
    }
    .dd-sub-header { color: #8b949e; font-size: 0.85rem; font-weight: 700; margin-top: 10px; text-transform: uppercase; }
    .dd-inner { background-color: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 12px; margin-top: 8px; font-size: 0.95rem; line-height: 1.6; }
    .dd-highlight { color: var(--accent-orange); font-weight: bold; font-family: monospace; }
    .dd-tag-long { background: rgba(35,134,54,0.2); color: #3fb950; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(35,134,54,0.4); font-size: 0.8rem; font-weight: bold;}
    .dd-tag-short { background: rgba(218,54,51,0.2); color: #f85149; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(218,54,51,0.4); font-size: 0.8rem; font-weight: bold;}
    ul { padding-left: 20px; margin: 5px 0; color: #e6edf3; } li { margin-bottom: 4px; }
    .wiki-card { background-color: #1E2228; padding: 10px; border-radius: 6px; border-left: 3px solid #44a4f2; margin-bottom: 8px; }
    .wiki-title { color: #44a4f2; font-weight: bold; font-size: 1em; }
    .wiki-text { color: #8B949E; font-size: 0.85em; }
</style>
"""

WIKI_HTML = """
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
    <div class='wiki-card'><div class='wiki-title'>🧬 SMC (聰明錢)</div><div class='wiki-text'>追蹤機構大戶留下的足跡。重點觀察「失衡區 (FVG)」與「流動性獵殺 (Liquidity Sweep)」。</div></div>
    <div class='wiki-card'><div class='wiki-title'>📏 Fibonacci (斐波那契)</div><div class='wiki-text'>0.618 為「黃金口袋 (OTE)」，勝率最高的回調進場點。</div></div>
    <div class='wiki-card'><div class='wiki-title'>⚡ RSI (動能)</div><div class='wiki-text'>>70 過熱，<30 超賣。若價格創低但 RSI 墊高（背離），暗示反轉。</div></div>
    <div class='wiki-card'><div class='wiki-title'>🌊 AMD (結構)</div><div class='wiki-text'>累積 (A) -> 操弄 (M) -> 派發 (D)。</div></div>
</div>
"""

def init_db():
    conn = sqlite3.connect('smc_data.db'); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history (date TEXT, stock_id TEXT, stock_name TEXT, price REAL, status TEXT, ai_analysis TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS watchlists (group_name TEXT PRIMARY KEY, codes TEXT)''')
    c.execute("SELECT count(*) FROM watchlists")
    if c.fetchone()[0] == 0:
        defaults = [("AI 伺服器", "2330,2317,2382,3231,6669,2357"), ("航運三雄", "2603,2609,2615")]
        c.executemany("INSERT INTO watchlists VALUES (?,?)", defaults)
        conn.commit(); conn.close()

def save_watchlist(group_name, codes):
    conn = sqlite3.connect('smc_data.db'); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO watchlists VALUES (?, ?)", (group_name, codes))
    conn.commit(); conn.close()

def load_watchlists():
    conn = sqlite3.connect('smc_data.db'); c = conn.cursor()
    c.execute("SELECT * FROM watchlists"); rows = c.fetchall(); conn.close()
    return {row[0]: row[1].split(',') for row in rows}

def delete_watchlist(group_name):
    conn = sqlite3.connect('smc_data.db'); c = conn.cursor()
    c.execute("DELETE FROM watchlists WHERE group_name=?", (group_name,))
    conn.commit(); conn.close()

def save_history(stock_id, stock_name, price, status, ai_analysis):
    conn = sqlite3.connect('smc_data.db'); c = conn.cursor()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?)", (date_str, stock_id, stock_name, price, status, ai_analysis))
    conn.commit(); conn.close()

def load_history():
    conn = sqlite3.connect('smc_data.db')
    try: df = pd.read_sql_query("SELECT * FROM history ORDER BY date DESC", conn)
    except: df = pd.DataFrame()
    conn.close(); return df

def delete_history(stock_id):
    conn = sqlite3.connect('smc_data.db'); c = conn.cursor()
    c.execute("DELETE FROM history WHERE stock_id=?", (stock_id,))
    conn.commit(); conn.close()

def clean_html_output(text):
    text = re.sub(r"```html", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return '\n'.join(cleaned_lines)

def calculate_support_line(df):
    try:
        if len(df) < 10: return []
        min_idx = df['Low'].idxmin()
        min_price = df['Low'].min()
        after_min = df.loc[min_idx:].iloc[1:]
        if len(after_min) > 5:
             second_min_idx = after_min['Low'].idxmin()
             second_min_price = after_min['Low'].min()
             return [(min_idx, min_price), (second_min_idx, second_min_price)]
        else: return []
    except: return []

def fetch_data_by_timeframe(ticker, interval):
    period_map = {"15m": "60d", "1h": "730d", "1d": "2y", "1wk": "5y"}
    period = period_map.get(interval, "1y")
    try:
        stock = yf.Ticker(f"{ticker}.TW")
        df = stock.history(period=period, interval=interval)
        if df.empty:
            stock = yf.Ticker(f"{ticker}.TWO")
            df = stock.history(period=period, interval=interval)
        return stock, df
    except: return None, pd.DataFrame()

def calculate_technicals(df):
    if df.empty: return df, "無數據"
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain/loss))
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['BIAS_20'] = ((df['Close'] - df['MA20']) / df['MA20']) * 100
    price = df['Close'].iloc[-1]; ma20 = df['MA20'].iloc[-1]; ma60 = df['MA60'].iloc[-1]
    trend = "📈 多頭" if price > ma20 > ma60 else ("📉 空頭" if price < ma20 < ma60 else "盤整")
    return df, trend

def get_valuation_info(stock_obj):
    try: info = stock_obj.info; return info.get('trailingPE', 'N/A'), info.get('priceToBook', 'N/A')
    except: return 'N/A', 'N/A'

def get_chips_silent(stock_id):
    try:
        url = f"https://goodinfo.tw/tw/ShowBuySaleDaily.asp?STOCK_ID={stock_id}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        dfs = pd.read_html(requests.get(url, headers=headers, timeout=3).text)
        for df in dfs:
            cols = [str(c) for c in df.columns.tolist()]
            if any("外資" in c for c in cols) and any("買賣超" in c for c in cols):
                row = df.dropna(how='all').iloc[0]
                return {"外資": row.iloc[2], "投信": row.iloc[3], "自營": row.iloc[4], "status": "ok"}
    except: pass
    return {"status": "fail"}
