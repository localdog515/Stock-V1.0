import streamlit as st
import yfinance as yf
import mplfinance as mpf
import google.generativeai as genai
from PIL import Image
import smc_tools as tools
import pandas as pd

# ---------------------------------------------------------
# 0. 設定與樣式
# ---------------------------------------------------------
st.set_page_config(page_title="SMC 戰略終端", layout="wide", page_icon="📈")
st.markdown(tools.UI_CSS, unsafe_allow_html=True)

# 嘗試讀取 Secrets，否則使用預設密碼
try:
    APP_PASSWORD = st.secrets["APP_PASSWORD"]
except:
    APP_PASSWORD = "bro"

def check_password():
    if st.session_state.get("password_correct", False): return True
    def password_entered():
        if st.session_state["password"] == APP_PASSWORD:
            st.session_state["password_correct"] = True; del st.session_state["password"]
        else: st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.text_input("🔒 請輸入通關密碼", type="password", on_change=password_entered, key="password"); return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 請輸入通關密碼", type="password", on_change=password_entered, key="password"); st.error("❌ 密碼錯誤"); return False
    return True

try:
    if "GOOGLE_API_KEY" in st.secrets: GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    else: GOOGLE_API_KEY = "AIzaSyCPqvmQZka2R8jalkpTHHBl_VPvvgUFVrU"
except: GOOGLE_API_KEY = "AIzaSyCPqvmQZka2R8jalkpTHHBl_VPvvgUFVrU"

# ---------------------------------------------------------
# 1. 主程式邏輯
# ---------------------------------------------------------
if check_password():
    # 初始化資料庫
    tools.init_db()
    
    # 頂部標題
    c1, c2 = st.columns([3, 1])
    with c1: st.markdown("## 🚀 SMC 賽博戰略終端 (V32.0)")
    with c2:
        with st.expander("📖 技術指標百科 (Wiki)"):
            st.markdown(tools.WIKI_HTML, unsafe_allow_html=True)

    # 設定 AI 模型
    model = None
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in valid_models if 'flash' in m), valid_models[0] if valid_models else None)
        if target: model = genai.GenerativeModel(target)
    except: pass

    # 側邊欄選單
    st.sidebar.header("🕹️ 戰略指揮中心")
    app_mode = st.sidebar.radio("模式", ["🔍 深度戰情室", "🎯 市場雷達", "⚙️ 清單管理", "📂 歷史戰報"])

    # =========================================================
    # 功能 A: 深度戰情室 (Deep Dive)
    # =========================================================
    if app_mode == "🔍 深度戰情室":
        st.sidebar.markdown("---")
        stock_id = st.sidebar.text_input("輸入代號 (例如 2330)", "2330")
        timeframe = st.sidebar.selectbox("K線週期", ["15m", "1h", "4h", "1d", "1wk"], index=3)
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📸 籌碼證據上傳")
        uploaded_files = st.sidebar.file_uploader("拖曳上傳截圖 (多張)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        if st.sidebar.button("🔥 啟動全域分析", type="primary"):
            st.write(f"正在連線... 目標：{stock_id}")
            
            try:
                fetch_tf = "1h" if timeframe == "4h" else timeframe
                stock_obj, df = tools.fetch_data_by_timeframe(stock_id, fetch_tf)
                
                if df.empty:
                    st.error("❌ 找不到數據，請確認代號或網路連線。")
                else:
                    pe, pb = tools.get_valuation_info(stock_obj)
                    chips = tools.get_chips_silent(stock_id)
                    df, trend = tools.calculate_technicals(df)
                    latest = df.iloc[-1]
                    curr_price = latest['Close']
                    
                    status_tag = "<span class='dd-tag-long'>多頭排列</span>" if "多" in trend else "<span class='dd-tag-short'>空頭排列</span>"
                    trend_color = '#3fb950' if '多' in trend else '#f85149'

                    html_content = f"""
                    <div class="dd-box">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <h2 style="margin:0; color:white;">{stock_id} <span style="font-size:0.6em; color:#8b949e;">.TW</span></h2>
                            {status_tag}
                        </div>
                        <div style="display:flex; gap:20px; font-size:0.9rem; color:#8b949e;">
                            <div>現價: <span style="color:white; font-weight:bold;">{curr_price}</span></div>
                            <div>趨勢: <span style="color:{trend_color};">{trend}</span></div>
                            <div>RSI: <span style="color:#e6edf3;">{latest.get('RSI',0):.1f}</span></div>
                        </div>
                        <div style="display:flex; gap:40px; margin-top:20px;">
                            <div style="flex:1;">
                                <div class="dd-header">自動爬蟲數據 (參考)</div>
                                <div style="font-size:0.9rem;">
                                    <div>外資: <span style="color:#e6edf3;">{chips.get('外資','N/A')}</span></div>
                                    <div>投信: <span style="color:#e6edf3;">{chips.get('投信','N/A')}</span></div>
                                    <div style="color:#da3633; font-size:0.8em; margin-top:5px;">*若顯示 N/A 請看 AI 截圖分析</div>
                                </div>
                            </div>
                            <div style="flex:1;">
                                <div class="dd-header">基本面估值</div>
                                <div style="font-size:0.9rem;">
                                    <div>PE (本益比): <span style="color:#e6edf3;">{pe}</span></div>
                                    <div>PB (淨值比): <span style="color:#e6edf3;">{pb}</span></div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(tools.clean_html_output(html_content), unsafe_allow_html=True)

                    image_parts = []
                    if uploaded_files:
                        cols = st.columns(min(len(uploaded_files), 4))
                        for i, f in enumerate(uploaded_files):
                            img = Image.open(f)
                            image_parts.append(img)
                            cols[i % 4].image(img, use_container_width=True)

                    if model:
                        system_prompt = f"""
你現在是「投資導航員」(Investment Navigator)。
標的：{stock_id}。現價：{curr_price}。趨勢：{trend}。
自動爬蟲數據：{chips}。用戶上傳了 {len(image_parts)} 張圖片。
**核心哲學：** 1. 風險優先。 2. 蘇格拉底式引導。 3. 客觀中立。
**請以繁體中文 HTML 格式輸出 (使用以下 class)，不要使用 markdown code block：**
- `<div class="dd-box">`: 外框
- `<div class="dd-header">`: 標題
- `<div class="dd-sub-header">`: 小標題
- `<div class="dd-inner">`: 內文
- `<span class="dd-highlight">`: 重點
**內容 SOP：**
1. **基本面戰略**：估值、產業地位。
2. **技術面七位一體**：FVG、亞當理論、BIAS、RSI、DMI、K線。
3. **籌碼與資金 (關鍵)**：**仔細閱讀截圖**。外資/投信/融資動向。
4. **決策與執行**：給出 TP (止盈), SL (止損), Entry (進場) 的具體價位。
"""
                        st.markdown("### 🧬 導航員戰略分析")
                        with st.spinner("正在進行七位一體掃描..."):
                            try:
                                content = [system_prompt] + image_parts
                                res = model.generate_content(content)
                                clean_html = tools.clean_html_output(res.text)
                                st.markdown(clean_html, unsafe_allow_html=True)
                                
                                with st.form("save"):
                                    if st.form_submit_button("💾 存檔戰報"):
                                        tools.save_history(stock_id, stock_id, curr_price, trend, "HTML_REPORT")
                            except Exception as e: st.error(f"AI Error: {e}")

                    st.markdown("### 🕯️ 多週期戰略圖表")
                    tabs = st.tabs(["週線", "日線", "4小時", "1小時", "15分"])
                    tfs = ["1wk", "1d", "1h", "1h", "15m"]
                    
                    for i, tab in enumerate(tabs):
                        with tab:
                            _, df_tf = tools.fetch_data_by_timeframe(stock_id, tfs[i])
                            if not df_tf.empty:
                                df_tf, _ = tools.calculate_technicals(df_tf)
                                recent = df_tf.tail(120)
                                h = recent['High'].max(); l = recent['Low'].min()
                                f618 = h - (h-l)*0.618; f05 = (h+l)/2; f382 = h - (h-l)*0.382
                                
                                trend_points = tools.calculate_support_line(recent)
                                fib_lines = dict(hlines=[f618, f05, f382], colors=['#00FFA3', 'gray', '#FF4B4B'], linewidths=[1.5, 0.5, 1.0], alpha=0.7)
                                mc = mpf.make_marketcolors(up='#00FFA3', down='#FF4B4B', edge='inherit', wick='inherit', volume='in')
                                s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, gridstyle=':', y_on_right=True, facecolor='#161b22')
                                
                                title_str = f"\n{stock_id} ({tfs[i]}) | TP(0.618): {f618:.1f} | SL(0.382): {f382:.1f}"
                                
                                if trend_points:
                                    fig, ax = mpf.plot(recent, type='candle', style=s, hlines=fib_lines, 
                                                       alines=dict(alines=trend_points, colors=['#44a4f2'], linewidths=1.5),
                                                       volume=True, returnfig=True, figsize
