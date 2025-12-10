import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import re

st.set_page_config(page_title="專利 PDF 下載小幫手 v2.0", page_icon="🕵️")

st.title("🕵️ Google Patents PDF 下載器 v2.0")
st.markdown("""
**使用說明：**
1. 請盡量輸入 **完整案號** (例如：`US20240088000A1`)。
2. 程式會自動嘗試幫你去除連字號 `-` 或空白。
3. 如果 Google 擋住下載，會提供備用連結。
""")

# 1. 獲取使用者輸入
patent_ids = st.text_area("在此輸入專利案號", height=150, placeholder="US20240088000A1")

# 偽裝成更像真人的瀏覽器標頭
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def clean_patent_id(pid):
    """清理案號：移除空白和連字號，轉大寫"""
    return pid.replace("-", "").replace(" ", "").upper()

def get_pdf_link(patent_id):
    """嘗試解析 PDF 連結，並回傳狀態"""
    # 建構網址
    url = f"https://patents.google.com/patent/{patent_id}/en"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # 狀況 A: Google 覺得我們是機器人
        if response.status_code == 429:
            return "BLOCKED", url
        
        # 狀況 B: 找不到網頁 (案號錯誤)
        if response.status_code == 404:
            return "NOT_FOUND", url
            
        # 狀況 C: 成功進入，開始找 PDF
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # 方法 1: 找結尾是 .pdf 的連結
            for link in soup.find_all('a', href=True):
                if link['href'].endswith('.pdf'):
                    return "SUCCESS", link['href']
            
            # 方法 2: 有時候 PDF 連結藏在特定的按鈕裡 (meta tag)
            meta_pdf = soup.find("meta", {"name": "citation_pdf_url"})
            if meta_pdf:
                 return "SUCCESS", meta_pdf['content']

            return "NO_PDF_LINK", url
            
    except Exception as e:
        return "ERROR", str(e)
    
    return "UNKNOWN", url

# 2. 按鈕邏輯
if st.button("🚀 開始搜尋"):
    if patent_ids:
        raw_list = patent_ids.split('\n')
        st.write(f"收到 {len(raw_list)} 筆輸入，開始處理...")
        
        for raw_id in raw_list:
            if not raw_id.strip(): continue # 跳過空行
            
            # 自動清理案號
            pid = clean_patent_id(raw_id.strip())
            
            with st.container():
                st.subheader(f"🔍 搜尋: {pid}")
                
                # 執行搜尋
                status, result = get_pdf_link(pid)
                
                if status == "SUCCESS":
                    st.success("✅ 成功找到 PDF！")
                    st.link_button(f"📥 下載 {pid}.pdf", result)
                
                elif status == "BLOCKED":
                    st.error("⚠️ Google 暫時封鎖了來自此伺服器的請求 (429 Error)。")
                    st.markdown(f"建議直接前往頁面下載：[點我打開 Google 專利頁]({result})")
                    
                elif status == "NOT_FOUND":
                    st.warning(f"❌ 找不到此案號。請確認案號格式是否正確？(Google 網址不存在)")
                    st.info(f"嘗試過的網址: {result}")
                    st.markdown("💡 提示：試試看補上 `A1` 或 `B2` 等後綴代碼。")
                    
                elif status == "NO_PDF_LINK":
                    st.warning("⚠️ 找到了專利頁面，但程式抓不到 PDF 連結（可能需要登入或有人機驗證）。")
                    st.markdown(f"[點我打開 Google 專利頁]({result})")
                    
                else:
                    st.error(f"發生未知錯誤: {result}")
                
                st.divider()
                time.sleep(1.5) # 稍微休息一下，避免被鎖更久
    else:
        st.warning("請先輸入案號。")
