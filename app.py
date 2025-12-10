import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import zipfile
import io

st.set_page_config(page_title="專利 PDF 批次下載器", page_icon="📦")

st.title("📦 Google Patents 批次下載神器")
st.markdown("輸入多個案號，一次打包下載所有 PDF。")

# 1. 使用者輸入區
patent_ids = st.text_area("在此輸入專利案號 (一行一個)", height=150, placeholder="US20240088000A1\nCN117116910B")

# 偽裝標頭
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def get_pdf_url_only(patent_id):
    """只負責找連結，不下載檔案"""
    url = f"https://patents.google.com/patent/{patent_id}/en"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # 策略 A: 找 .pdf 連結
            for link in soup.find_all('a', href=True):
                if link['href'].endswith('.pdf'):
                    return link['href']
            # 策略 B: 找 meta tag
            meta_pdf = soup.find("meta", {"name": "citation_pdf_url"})
            if meta_pdf:
                 return meta_pdf['content']
    except:
        pass
    return None

def download_file_content(url):
    """從連結下載二進位檔案內容"""
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.content
    except:
        pass
    return None

# 2. 執行邏輯
if st.button("🚀 開始批次搜尋與打包"):
    if patent_ids:
        # 準備資料
        raw_list = [x.strip() for x in patent_ids.split('\n') if x.strip()]
        total_count = len(raw_list)
        
        # 建立一個記憶體內的 ZIP 檔
        zip_buffer = io.BytesIO()
        
        # 用來存放搜尋結果報告的清單
        results_log = []
        success_count = 0
        
        # 進度條
        progress_bar = st.progress(0)
        status_text = st.empty()

        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, pid in enumerate(raw_list):
                # 簡單清理案號
                clean_pid = pid.replace(" ", "").upper()
                status_text.text(f"正在處理 ({i+1}/{total_count}): {clean_pid} ...")
                
                # 步驟 1: 找連結
                pdf_link = get_pdf_url_only(clean_pid)
                
                if pdf_link:
                    # 步驟 2: 如果有連結，嘗試下載內容
                    pdf_content = download_file_content(pdf_link)
                    
                    if pdf_content:
                        # 寫入 ZIP
                        zf.writestr(f"{clean_pid}.pdf", pdf_content)
                        success_count += 1
                        results_log.append(f"✅ **{clean_pid}**: 成功 (已加入壓縮檔)")
                    else:
                        results_log.append(f"⚠️ **{clean_pid}**: 找到連結但下載失敗 (可能被擋)")
                else:
                    results_log.append(f"❌ **{clean_pid}**: 找不到 PDF 連結")
                
                # 更新進度條
                progress_bar.progress((i + 1) / total_count)
                time.sleep(1) # 避免太快被封鎖

        status_text.text("處理完成！")
        
        # 3. 顯示結果區域 (先顯示大按鈕，再顯示報告)
        st.divider()
        
        if success_count > 0:
            # 將指標移回檔案開頭，準備被讀取
            zip_buffer.seek(0)
            
            st.success(f"🎉 成功打包 {success_count} 個檔案！")
            
            # 🔥 這裡就是你要的「單一按鈕」
            st.download_button(
                label="📥 下載所有專利 (.zip)",
                data=zip_buffer,
                file_name="patents_bundle.zip",
                mime="application/zip",
                type="primary" # 讓按鈕變顯眼
            )
        else:
            st.error("很遺憾，沒有成功下載任何檔案。")

        # 4. 在按鈕下方顯示詳細結果
        with st.expander("查看詳細搜尋報告", expanded=True):
            for log in results_log:
                st.markdown(log)
                
    else:
        st.warning("請先輸入案號。")
