import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import zipfile
import io
import random
import urllib.parse
import re

st.set_page_config(page_title="專利 PDF 終極下載器 v5.0", page_icon="🚀")

st.title("🚀 Google Patents 終極下載器 v5.0")
st.markdown("""
**功能更新：**
1. 針對 `18/671705` 等申請號進行強化搜尋。
2. 顯示搜尋到的「真實身分」案號。
""")

# 1. 使用者輸入區
patent_ids = st.text_area(
    "在此輸入專利案號 (一行一個)", 
    height=150, 
    placeholder="18/671705 (申請號)\nUS20240088000A1 (公開號)"
)

def get_headers():
    """隨機切換身分，避免被 Google 認定是機器人"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) Chrome/118.0.0.0 Safari/537.36"
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    }

def search_google_for_correct_url(query):
    """
    當直接下載失敗時，去 Google 搜尋「真實案號」
    """
    # 針對申請號的特殊優化：加上 "patent" 關鍵字讓 Google 知道我們在找專利
    search_query = f"{query} patent site:patents.google.com"
    google_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}"
    
    try:
        # 隨機延遲，模擬真人思考
        time.sleep(random.uniform(1.5, 3.0))
        resp = requests.get(google_url, headers=get_headers(), timeout=10)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 尋找搜尋結果中的連結
            # Google 的搜尋結果通常包含在 <a href="..."> 中，且連結指向 patents.google.com/patent/
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if "patents.google.com/patent/" in href:
                    # 清理連結 (有時候會包含 /url?q=...)
                    if "/url?q=" in href:
                        href = href.split("/url?q=")[1].split("&")[0]
                    return href
    except Exception as e:
        print(f"Search Error: {e}")
    return None

def get_pdf_data(patent_id):
    """
    主邏輯：
    1. 嘗試直接猜測 (快)
    2. 失敗則去 Google 搜尋 (慢但準)
    3. 下載 PDF
    """
    clean_id = patent_id.strip()
    status_msg = ""
    
    # --- 階段一：獲取正確的網址 ---
    target_url = None
    
    # 1. 先試試看直接拼網址 (適合標準公開號)
    guess_url = f"https://patents.google.com/patent/{clean_id.replace('/', '').replace('-', '')}/en"
    try:
        if requests.get(guess_url, headers=get_headers(), timeout=5).status_code == 200:
            target_url = guess_url
    except:
        pass

    # 2. 如果直連失敗，啟動 Google 搜尋 (適合申請號 18/671705)
    if not target_url:
        found_url = search_google_for_correct_url(clean_id)
        if found_url:
            target_url = found_url
            status_msg = f"(透過搜尋找到對應網頁)"

    if not target_url:
        return "NOT_FOUND", None, None, "找不到對應網頁"

    # --- 階段二：從網頁中抓 PDF ---
    try:
        resp = requests.get(target_url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 抓取真實案號 (從網頁標題或網址分析)
        real_id = target_url.split("/patent/")[-1].split("/")[0]
        
        pdf_link = None
        # 方法 A: 找連結
        for link in soup.find_all('a', href=True):
            if link['href'].endswith('.pdf'):
                pdf_link = link['href']
                break
        
        # 方法 B: 找 Meta 標籤
        if not pdf_link:
            meta = soup.find("meta", {"name": "citation_pdf_url"})
            if meta: pdf_link = meta['content']

        if pdf_link:
            # 下載檔案
            file_resp = requests.get(pdf_link, headers=get_headers(), timeout=15)
            if file_resp.status_code == 200:
                return "SUCCESS", f"{real_id}.pdf", file_resp.content, f"成功！(對應公開號: {real_id})"
            else:
                return "FAIL", None, None, "找到連結但下載失敗"
        else:
            return "NO_LINK", None, None, f"找到網頁 ({real_id}) 但沒有 PDF 下載點"
            
    except Exception as e:
        return "ERROR", None, None, str(e)

# 2. 按鈕邏輯
if st.button("🚀 啟動終極搜尋"):
    if patent_ids:
        raw_list = [x.strip() for x in patent_ids.split('\n') if x.strip()]
        
        zip_buffer = io.BytesIO()
        results_log = []
        success_count = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, pid in enumerate(raw_list):
                status_text.text(f"正在偵探調查 ({i+1}/{len(raw_list)}): {pid} ...")
                
                # 執行搜尋
                code, filename, content, msg = get_pdf_data(pid)
                
                if code == "SUCCESS":
                    zf.writestr(filename, content)
                    success_count += 1
                    results_log.append(f"✅ **{pid}** -> {msg}")
                elif code == "NOT_FOUND":
                    results_log.append(f"❌ **{pid}**: Google 搜尋也找不到，請確認號碼。")
                else:
                    results_log.append(f"⚠️ **{pid}**: {msg}")
                
                progress_bar.progress((i + 1) / len(raw_list))
                # 搜尋需要一點時間休息，避免被 Google 懷疑
                time.sleep(random.uniform(2.0, 4.0))

        status_text.text("處理完成！")
        st.divider()
        
        if success_count > 0:
            zip_buffer.seek(0)
            st.success(f"🎉 成功下載 {success_count} 個檔案！")
            st.download_button(
                label="📥 下載打包檔案 (.zip)",
                data=zip_buffer,
                file_name="ultimate_patents.zip",
                mime="application/zip",
                type="primary"
            )
        
        with st.expander("查看詳細偵探報告", expanded=True):
            for log in results_log:
                st.markdown(log)
    else:
        st.warning("請先輸入案號")
