# 公司資訊顯示代碼片段

# 中文業務說明映射
cn_summaries = {
    'TSLA': '特斯拉公司設計、開發、製造、租賃和銷售電動車,以及在美國、中國和全球其他地區的能源發電和儲存系統。公司運營兩個業務區塊:汽車業務和能源發電及儲存業務。汽車業務提供電動車輛,並銷售汽車監管信用、非保固售後車輛服務、二手車、車體維修和零件、超級充電站、零售商品和車輛保險服務。能源發電及儲存業務區塊從事太陽能發電和能源儲存產品的設計、製造、安裝、銷售和租賃,以及相關服務。',
    'NVDA': '輝達公司是一家運算基礎設施公司,在美國、新加坡、台灣、中國、香港和全球其他地區提供圖形、運算和網路解決方案。運算與網路業務區塊包括數據中心加速運算平台和人工智慧解決方案及軟體、網路、汽車平台和自動駕駛及電動車解決方案、機器人和其他嵌入式平台的Jetson,以及DGX雲端運算服務。圖形業務區塊提供用於遊戲和PC的GeForce GPU、GeForce NOW遊戲串流服務及相關基礎設施、企業工作站圖形的Quadro/NVIDIA RTX GPU、用於雲端視覺和虛擬運算的虛擬GPU或vGPU軟體、資訊娛樂系統的汽車平台,以及Omniverse軟體用於構建和運營工業AI和數位孿生應用。',
    'GOOG': '谷歌公司是一家全球科技領導者,專注於改進人們與資訊互動的方式。公司的主要業務包括搜尋引擎、線上廣告技術、雲端運算、軟體和硬體產品。谷歌的產品和服務包括Android作業系統、Chrome瀏覽器、Gmail電子郵件、Google Maps地圖、YouTube影片平台、Google Cloud雲端服務、Google Workspace辦公套件,以及Pixel智慧型手機等硬體產品。公司也在人工智慧、機器學習和自動駕駛技術等領域進行大量投資。',
    'AAPL': '蘋果公司設計、製造和銷售智慧型手機、個人電腦、平板電腦、可穿戴裝置和配件。公司的主要產品線包括iPhone智慧型手機、Mac個人電腦、iPad平板電腦、Apple Watch智慧手錶、AirPods無線耳機等。蘋果也提供各種服務,包括雲端服務、數位內容商店和串流服務、支付服務等。公司以其創新的產品設計、用戶體驗和生態系統整合而聞名。',
    'MSFT': '微軟公司是一家全球領先的技術公司,開發、授權和支援各種軟體產品、服務和裝置。公司的主要產品包括Windows作業系統、Microsoft Office辦公軟體套件、Azure雲端運算平台、Dynamics業務應用程式,以及Surface個人電腦和Xbox遊戲主機等硬體產品。微軟也提供各種雲端服務,包括Microsoft 365、LinkedIn職業社交平台、GitHub開發者平台等。公司也在人工智慧領域進行大量投資,包括Copilot AI助手等產品。'
}

# 使用範例
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
    
    # 公司業務說明 (中文)
    # 如果有中文版本則使用,否則使用英文
    if ticker in cn_summaries:
        business_summary = cn_summaries[ticker]
    else:
        business_summary = info.get('longBusinessSummary', '無法獲取公司業務說明')
    
    st.markdown(f"""
    <div style="font-size: 14px; margin-top: 10px; line-height: 1.6;">
        <b>💼 業務說明:</b><br>
        {business_summary}
    </div>
    """, unsafe_allow_html=True)
    
except Exception as e:
    st.warning(f"無法獲取 {ticker} 的公司資訊: {str(e)}")
