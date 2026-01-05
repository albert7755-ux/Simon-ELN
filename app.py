import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re

# 頁面設定
st.set_page_config(
    page_title="FCN參考資訊",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自訂CSS樣式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stAlert {
        margin-top: 1rem;
    }
    @media print {
        @page {
            size: A4;
            margin: 1cm;
        }
        body {
            print-color-adjust: exact;
            -webkit-print-color-adjust: exact;
        }
        .stButton, .stSidebar, [data-testid="stSidebar"] {
            display: none !important;
        }
        .main-header {
            font-size: 1.8rem;
            page-break-after: avoid;
        }
        .stPlotlyChart {
            page-break-inside: avoid;
        }
    }
</style>
""", unsafe_allow_html=True)

# 快取數據獲取函數
@st.cache_data(ttl=3600)
def get_stock_data(ticker, start_date="2009-01-01"):
    """獲取股票歷史數據並快取1小時"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=datetime.now())
        if hist.empty:
            return None
        return hist
    except Exception as e:
        st.error(f"獲取 {ticker} 數據時發生錯誤: {str(e)}")
        return None

@st.cache_data(ttl=86400)  # 快取24小時
def fetch_moneydj_company_description(ticker):
    """從MoneyDJ網站動態抓取公司經營概述"""
    try:
        url = f"https://www.moneydj.com/us/basic/basic0001/{ticker.lower()}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'zh-TW,zh;q=0.9',
        }
        
        # 設定較短的超時時間
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        # 使用lxml解析器提高速度
        soup = BeautifulSoup(response.content, 'lxml')
        
        # 尋找包含 "經營概述" 的表格行
        all_text = soup.get_text(separator='\n', strip=True)
        lines = all_text.split('\n')
        
        # 找到經營概述的位置
        for i, line in enumerate(lines):
            if line.strip() == '經營概述':
                # 下一行就是經營概述的內容
                if i + 1 < len(lines):
                    description = lines[i + 1].strip()
                    if description and len(description) > 50:
                        return description
                break
        
        return None
        
    except requests.Timeout:
        return None
    except Exception as e:
        return None

def calculate_profit_probability(hist, strike_price, period_months):
    """計算獲利機率"""
    if hist is None or len(hist) == 0:
        return 0.0
    
    period_days = period_months * 30
    total_periods = len(hist) - period_days
    if total_periods <= 0:
        return 0.0
    
    profit_count = 0
    for i in range(total_periods):
        start_price = hist['Close'].iloc[i]
        end_price = hist['Close'].iloc[i + period_days]
        if end_price >= strike_price:
            profit_count += 1
    
    return (profit_count / total_periods) * 100

def analyze_price_breach(hist, strike_price, ki_price):
    """分析是否曾跌破Strike和KI,以及回升所需交易日數"""
    if hist is None or len(hist) == 0:
        return {
            'strike_breached': False,
            'strike_recovery_days': None,
            'ki_breached': False,
            'ki_recovery_days': None
        }
    
    result = {
        'strike_breached': False,
        'strike_recovery_days': None,
        'ki_breached': False,
        'ki_recovery_days': None
    }
    
    # 檢查Strike跌破
    strike_breach_idx = None
    for i in range(len(hist)):
        if hist['Close'].iloc[i] < strike_price:
            result['strike_breached'] = True
            strike_breach_idx = i
            break
    
    # 如果跌破Strike,計算回升所需交易日
    if strike_breach_idx is not None:
        for i in range(strike_breach_idx + 1, len(hist)):
            if hist['Close'].iloc[i] >= strike_price:
                result['strike_recovery_days'] = i - strike_breach_idx
                break
    
    # 檢查KI跌破 (只有當KI > 0時)
    if ki_price > 0:
        ki_breach_idx = None
        for i in range(len(hist)):
            if hist['Close'].iloc[i] < ki_price:
                result['ki_breached'] = True
                ki_breach_idx = i
                break
        
        # 如果跌破KI,計算回升所需交易日
        if ki_breach_idx is not None:
            for i in range(ki_breach_idx + 1, len(hist)):
                if hist['Close'].iloc[i] >= ki_price:
                    result['ki_recovery_days'] = i - ki_breach_idx
                    break
    
    return result

def create_stock_chart(hist, ticker, current_price, ko_price, strike_price, ki_price, ko_pct, strike_pct, ki_pct, height=500):
    """建立股票價格走勢圖"""
    fig = go.Figure()
    
    # 股價走勢線
    fig.add_trace(go.Scatter(
        x=hist.index,
        y=hist['Close'],
        mode='lines',
        name='股價',
        line=dict(color='black', width=2)
    ))
    
    # KO 線 (敵出價)
    fig.add_hline(
        y=ko_price,
        line_dash="dash",
        line_color="red",
        annotation_text=f"KO ({ko_pct}%): ${ko_price:.2f}",
        annotation_position="right"
    )
    
    # Strike 線 (執行價)
    fig.add_hline(
        y=strike_price,
        line_dash="solid",
        line_color="green",
        annotation_text=f"Strike ({strike_pct}%): ${strike_price:.2f}",
        annotation_position="right"
    )
    
    # KI 線 (敵入價) - 只有當KI > 0時才顯示
    if ki_pct > 0:
        fig.add_hline(
            y=ki_price,
            line_dash="dot",
            line_color="orange",
            annotation_text=f"KI ({ki_pct}%): ${ki_price:.2f}",
            annotation_position="right"
        )
    
    # 圖表布局
    fig.update_layout(
        title=f"{ticker} - 走勢與關鍵價位 (近3年)",
        xaxis_title="日期",
        yaxis_title="價格 (USD)",
        hovermode='x unified',
        height=height,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig

# ========== 主程式 ==========

# 標題區
st.markdown('<div class="main-header">📊 FCN參考資訊</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">關鍵點位與長週期風險回測 | 並排圖表顯示</div>', unsafe_allow_html=True)

# 側邊欄 - 參數設定
with st.sidebar:
    st.header("1️⃣ 輸入標的")
    tickers_input = st.text_area(
        "股票代碼 (逗號分隔)",
        value="TSLA, NVDA, GOOG",
        height=100,
        help="輸入多個股票代碼,用逗號分隔。最少1檔，最套5檔。例如: TSLA, NVDA, GOOG, AAPL, MSFT"
    )
    
    st.header("2️⃣ 結構條件 (%)")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        ko_pct = st.number_input(
            "KO (敲出價 %)",
            min_value=50.0,
            max_value=150.0,
            value=100.0,
            step=1.0,
            help="敲出價格百分比,通常為100%"
        )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        strike_pct = st.number_input(
            "Strike (轉換/執行價 %)",
            min_value=50.0,
            max_value=150.0,
            value=80.0,
            step=1.0,
            help="執行價格百分比,通常為70-90%"
        )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        ki_pct = st.number_input(
        "KI (下檔保護價 %) - 可輸入0表示無",
        min_value=0.0,
        max_value=100.0,
        value=65.0,
        step=1.0,
        format="%.2f",
        help="下檔保護價，低於此價可能觸發敵入機制。輸入0表示無KI保護"
    )
    
    st.header("3️⃣ 商品期間")
    period_months = st.number_input(
        "產品/觀察天期 (月)",
        min_value=1,
        max_value=36,
        value=6,
        step=1,
        help="產品觀察期間,單位為月"
    )
    
    st.divider()
    
    analyze_btn = st.button("🚀 開始分析", type="primary", use_container_width=True)
    
    st.divider()
    
    # 參數驗證提示
    if ko_pct <= strike_pct or strike_pct <= ki_pct:
        st.warning("⚠️ 建議參數關係: KO > Strike > KI")

# 主要內容區
st.caption("📅 回測區間：2009/01/01 至今 | 📊 報告期序號化：獲利潛力 > 安全性 > 解禁時間")

# 免責聲明
with st.expander("⚠️ 免責聲明與資料來源", expanded=False):
    st.warning("""
    **免責聲明與資料來源**
    
    1. **本工具僅供教學與模擬試算** - 本系統計算之數據，黑點為價格，不代表實際投資建議，不代表任何形式之投資建議。
    
    2. **歷史不代表未來** - 回測數據基於 2009 年至今之歷史取樣，場景的市場狀況不保證未來趨勢。
    
    3. **非本本商品** - 結構型商品之實際條款、配息率、費用結構與實際風險，應以發行機構提供之公開說明書(或承銷機構之簡章)。
    
    4. **實際報酬率** - 實際商品之報酬率，配息率、提早贖回(KO判定)之天，請以發行機構之公開說明書及條款為準。
    
    5. **資料來源** - 股價數據來源於 Yahoo Finance 公開數據，可能存在延遲或誤差，本系統不保證資料之絕對準確性。
    """)

# 提示訊息
if not analyze_btn:
    st.info("👈 請在左側設定參數，按下「開始分析」按鈕開始回測分析。")
    st.stop()

# 開始分析
with st.spinner("🔄 正在獲取股票數據並進行回測分析..."):
    # 解析股票代碼
    ticker_list = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
    
    if not ticker_list:
        st.error("❌ 請輸入至少一個股票代碼!")
        st.stop()
    
    if len(ticker_list) > 5:
        st.error("❌ 最多只能分析5檔股票! 請減少輸入數量。")
        st.stop()
    
    # 驗證參數邏輯
    if ko_pct <= strike_pct:
        st.error("❌ 參數設定錯誤! 必須滿足: KO > Strike")
        st.stop()
    
    if ki_pct > 0 and strike_pct <= ki_pct:
        st.error("❌ 參數設定錯誤! 當KI > 0時，必須滿足: Strike > KI")
        st.stop()
    
    # 獲取所有股票數據
    stock_data = {}
    failed_tickers = []
    
    for ticker in ticker_list:
        hist = get_stock_data(ticker)
        if hist is not None and not hist.empty:
            stock_data[ticker] = hist
        else:
            failed_tickers.append(ticker)
    
    if failed_tickers:
        st.warning(f"⚠️ 以下股票代碼無法獲取數據: {', '.join(failed_tickers)}")
    
    if not stock_data:
        st.error("❌ 所有股票代碼都無法獲取數據,請檢查代碼是否正確!")
        st.stop()

# 成功獲取數據,開始展示結果
st.success(f"✅ 成功獲取 {len(stock_data)} 檔股票數據!")

st.divider()

# ========== 並排顯示股票圖表 ==========
st.subheader("📈 股價走勢與關鍵價位分析 (並排顯示)")

# 單列布局: 1-5檔均在同一列橫向並排
num_stocks = len(stock_data)
cols = st.columns(num_stocks)
chart_height = 400  # 統一高度,適合單列顯示

# 為每檔股票建立圖表
for idx, (ticker, hist) in enumerate(stock_data.items()):
    with cols[idx]:
        # 計算關鍵價位
        current_price = hist['Close'].iloc[-1]
        ko_price = current_price * (ko_pct / 100)
        strike_price = current_price * (strike_pct / 100)
        ki_price = current_price * (ki_pct / 100)
        
        # 顯示標的資訊
        st.markdown(f"### 📌 {ticker}")
        
        # 關鍵數據卡片 - 統一黑體字與字體大小
        ki_display = f"${ki_price:.2f}" if ki_pct > 0 else "無"
        st.markdown(f"""
        <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">
            最新: ${current_price:.2f} | KO: ${ko_price:.2f} | Strike: ${strike_price:.2f} | KI: {ki_display}
        </div>
        """, unsafe_allow_html=True)
        
        # 繪製圖表 (只顯示近3年數據)
        # 如果索引有時區，將整個 DataFrame 轉換為 timezone-naive
        if hist.index.tz is not None:
            hist_copy = hist.copy()
            hist_copy.index = hist_copy.index.tz_localize(None)
        else:
            hist_copy = hist
        
        three_years_ago = pd.Timestamp.now() - pd.Timedelta(days=3*365)
        recent_hist = hist_copy[hist_copy.index >= three_years_ago]
        
        fig = create_stock_chart(
            recent_hist, ticker, current_price,
            ko_price, strike_price, ki_price,
            ko_pct, strike_pct, ki_pct,
            height=chart_height
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 公司資訊與基本面數據
        st.markdown("**🏛️ 公司資訊與基本面分析**")
        
        try:
            # 獲取公司資訊
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 基本面數據
            eps = info.get('trailingEps', 'N/A')
            pe_ratio = info.get('trailingPE', 'N/A')
            forward_eps = info.get('forwardEps', 'N/A')
            forward_pe = info.get('forwardPE', 'N/A')
            gross_margin = info.get('grossMargins', 'N/A')
            debt_to_equity = info.get('debtToEquity', 'N/A')
            
            # 格式化數據
            if isinstance(eps, (int, float)):
                eps = f"${eps:.2f}"
            if isinstance(pe_ratio, (int, float)):
                pe_ratio = f"{pe_ratio:.2f}"
            if isinstance(forward_eps, (int, float)):
                forward_eps = f"${forward_eps:.2f}"
            if isinstance(forward_pe, (int, float)):
                forward_pe = f"{forward_pe:.2f}"
            if isinstance(gross_margin, (int, float)):
                gross_margin = f"{gross_margin*100:.2f}%"
            if isinstance(debt_to_equity, (int, float)):
                debt_to_equity = f"{debt_to_equity:.2f}"
            
            # 顯示基本面數據 (放在上方)
            st.markdown(f"""
            <div style="font-size: 14px; margin-bottom: 15px;">
                <b>📊 基本面數據:</b><br>
                <table style="width: 100%; margin-top: 5px;">
                    <tr>
                        <td><b>EPS:</b> {eps}</td>
                        <td><b>P/E:</b> {pe_ratio}</td>
                        <td><b>EPS next Y:</b> {forward_eps}</td>
                    </tr>
                    <tr>
                        <td><b>Forward P/E:</b> {forward_pe}</td>
                        <td><b>Gross Margin:</b> {gross_margin}</td>
                        <td><b>Debt/Eq:</b> {debt_to_equity}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
            # 公司業務說明 (從MoneyDJ動態抓取)
            business_summary = fetch_moneydj_company_description(ticker)
            
            # 若MoneyDJ抓取失敗，使用Yahoo Finance的英文說明
            if not business_summary:
                business_summary = info.get('longBusinessSummary', '無法獲取公司業務說明')
            
            st.markdown(f"""
            <div style="font-size: 14px; margin-top: 10px; line-height: 1.6;">
                <b>💼 業務說明:</b><br>
                {business_summary}
            </div>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            st.warning(f"無法獲取 {ticker} 的公司資訊: {str(e)}")

st.divider()

# ========== 列印功能 ==========
st.divider()
if st.button("🖨️ 列印此頁面", use_container_width=True):
    st.markdown("""
    <script>
    window.print();
    </script>
    """, unsafe_allow_html=True)
    st.success("已開啟列印對話框，請選擇印表機或儲存為PDF。")

st.divider()

# 頁腳
st.caption("💡 本工具使用 Yahoo Finance 數據，僅供教學與研究用途。投資有風險，請謹慎評估。")
st.caption("🔄 數據快取時間: 1小時 | 最後更新: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
