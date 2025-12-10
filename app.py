import streamlit as st
import requests
from bs4 import BeautifulSoup
import time

# 設定頁面標題
st.set_page_config(page_title="專利 PDF 下載小幫手", page_icon="📑")

st.title("📑 Google Patents PDF 下載器")
st.markdown("請輸入專利案號（例如：US10000000），每行一個。")

# 1. 獲取使用者輸入
patent_ids = st.text_area("在此輸入專利案號", height=150, placeholder="US9000000\nUS10000000")

# 模擬瀏覽器的標頭（這是為了讓程式看起來像真人，減少被封鎖的機率）
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_pdf_link(patent_id):
    """嘗試從 Google Patents 頁面解析 PDF 連結"""
    base_url = f"https://patents.google.com/patent/{patent_id}/en"
    try:
        # 發送請求到 Google
        response = requests.get(base_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # 尋找頁面中含有 .pdf 的連結
            # Google Patents 的結構通常包含一個連向 storage.googleapis.com 的 PDF 連結
            for link in soup.find_all('a', href=True):
                if link['href'].endswith('.pdf'):
                    return link['href']
        return None
    except Exception as e:
        return None

# 2. 按鈕邏輯
if st.button("開始搜尋並生成下載連結"):
    if patent_ids:
        ids_list = patent_ids.split('\n')
        # 去除空白並過濾空行
        ids_list = [pid.strip() for pid in ids_list if pid.strip()]
        
        st.info(f"正在處理 {len(ids_list)} 筆專利...")
        
        for pid in ids_list:
            with st.spinner(f"正在分析專利 {pid}..."):
                # 為了避免太快被 Google 封鎖，我們稍微暫停一下
                time.sleep(1.0) 
                pdf_url = get_pdf_link(pid)
                
                if pdf_url:
                    st.success(f"找到專利 {pid}！")
                    # Streamlit 無法直接「幫你存到電腦」，但可以提供按鈕讓你點擊
                    st.link_button(f"📥 下載 {pid} PDF", pdf_url)
                else:
                    st.error(f"無法找到專利 {pid} 的 PDF，或是被 Google 阻擋。")
                    # 提供原始頁面連結作為備案
                    st.markdown(f"[前往 {pid} Google 專利頁面](https://patents.google.com/patent/{pid}/en)")
            st.divider()
    else:
        st.warning("請先輸入至少一個專利案號。")
