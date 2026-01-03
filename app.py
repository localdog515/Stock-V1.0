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

# 嘗試從 Secrets 讀取密碼 (雲端部署用)，否則使用預設
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
    tools.init_db()
    
    c1, c2 = st.columns([3, 1])
    with c1: st.markdown("## 🚀 SMC 賽博戰略終端 (V31.1)")
    with c2:
        with st.expander("📖 技術指標百科 (Wiki)"):
            st.markdown(tools.WIKI_HTML, unsafe_allow_html=True)

    model = None
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in valid_models if 'flash' in m), valid_models[0] if valid_models else None)
        if target: model = genai.GenerativeModel(target)
    except: pass

    st.sidebar.header("🕹️ 戰略指揮中心")
    app_mode = st.sidebar.radio("模式", ["🔍 深度戰情室", "🎯 市場雷達", "⚙️ 清單管理", "📂 歷史戰報"])

    # ==========================================
    # 功能 A: 深度戰情室 (Deep Dive)
    # ==========================================
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
                    st.error("❌ 找不到數據")
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
                                                       volume=True, returnfig=True, figsize=(12, 6), title=title_str)
                                else:
                                    fig, ax = mpf.plot(recent, type='candle', style=s, hlines=fib_lines, 
                                                       volume=True, returnfig=True, figsize=(12, 6), title=title_str)
                                
                                st.pyplot(fig)
                                st.caption("🟦 **藍線**: 上升趨勢線 (自動偵測支撐) | 🟩 **TP**: 0.618 黃金口袋 | 🟥 **SL**: 0.382 止損位")

            except Exception as e: st.error(f"System Error: {e}")

    # ==========================================
    # 功能 B: 市場雷達 (Radar) - 復活！
    # ==========================================
    elif app_mode == "🎯 市場雷達":
        st.header("🎯 戰略雷達")
        watch_lists = tools.load_watchlists()
        if watch_lists:
            c1, c2 = st.columns([1,3])
            with c1:
                g = st.selectbox("選擇族群", list(watch_lists.keys()))
                if st.button("啟動掃描"):
                    res = []
                    bar = st.progress(0)
                    targets = watch_lists[g]
                    for i, c in enumerate(targets):
                        try:
                            # 這裡預設掃描日K
                            s_obj, df = tools.fetch_data_by_timeframe(c.strip(), "1d")
                            if not df.empty:
                                df, tr = tools.calculate_technicals(df)
                                cur = df.iloc[-1]['Close']; hi = df['High'].tail(60).max(); lo = df['Low'].tail(60).min()
                                fib = hi - (hi-lo)*0.618
                                # 簡單篩選：接近 0.618 黃金位
                                status = ""
                                if cur <= fib * 1.05 and cur >= fib * 0.95:
                                    status = "🔥 接近黃金位"
                                elif "多頭" in tr:
                                    status = "📈 多頭排列"
                                
                                res.append({"代號":c, "現價": round(cur,1), "趨勢": tr, "訊號": status})
                        except: pass
                        bar.progress((i+1)/len(targets))
                    bar.empty()
                    if res: st.dataframe(pd.DataFrame(res), use_container_width=True)
                    else: st.info("該族群目前無資料或連線失敗")
        else: st.warning("請先到「清單管理」新增觀察名單")

    # ==========================================
    # 功能 C: 清單管理 (List) - 復活！
    # ==========================================
    elif app_mode == "⚙️ 清單管理":
        st.header("⚙️ 觀察名單管理")
        watch_lists = tools.load_watchlists()
        with st.expander("查看目前名單", expanded=True):
            for g, c in watch_lists.items(): st.text(f"【{g}】: {c}")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("add"):
                n = st.text_input("群組名稱 (例如: 機器人概念股)"); c = st.text_area("代號 (以逗號隔開, 如: 2330,2317)")
                if st.form_submit_button("儲存"): tools.save_watchlist(n, c); st.rerun()
        with c2:
            if watch_lists:
                d = st.selectbox("刪除群組", list(watch_lists.keys()))
                if st.button("確認刪除"): tools.delete_watchlist(d); st.rerun()

    # ==========================================
    # 功能 D: 歷史戰報 (History) - 復活！
    # ==========================================
    elif app_mode == "📂 歷史戰報":
        st.header("📂 歷史戰報")
        df = tools.load_history()
        if not df.empty:
            st.dataframe(df[['date', 'stock_name', 'status', 'ai_analysis']], use_container_width=True)
            t = st.selectbox("刪除紀錄 (選擇代號)", df['stock_id'].unique())
            if st.button("刪除"): tools.delete_history(t); st.rerun()
        else: st.info("目前尚無存檔紀錄")
