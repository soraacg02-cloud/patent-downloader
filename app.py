import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import zipfile
import io
import random
import urllib.parse

st.set_page_config(page_title="專利 PDF 萬能下載器 v4.0", page_icon="🦾")

st.title("🦾 Google Patents 萬能下載器 v4.0")
st.markdown("支援 **公開號** 與 **申請號** (自動反查對應專利)。")

# 1. 使用者輸入區
patent_ids = st.text_area(
    "在此輸入專利案號 (一行一個)", 
    height=150, 
    placeholder="US20240088000A1 (公開號 - 最快)\n18/671705 (美國申請號)\n2022-11738495 (中國申請號)"
)

# 偽裝標頭 (隨機切換，降低被鎖機率)
def get_headers():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept-Language": "en-US,en;q=0.9",
    }

def search_google_for_url(query):
    """
    當直接猜測失敗時，利用 Google 搜尋來找真正的專利頁面
    指令: site:patents.google.com [案號]
    """
    # 限制搜尋範圍在 patents.google.com
    search_query = f"site:patents.google.com {query}"
    google_search_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}"
    
    try:
        # 搜尋時要稍微等待，模擬人類行為
        time.sleep(random.uniform(1.0, 2.0))
        resp = requests.get(google_search_url, headers=get_headers(), timeout=10)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # 在搜尋結果中找第一個連結
            # Google 搜尋結果的連結通常在 'a' 標籤中，且 href 包含 'patents.google.com/patent/'
            for link in soup.find_all('a', href=True):
                href = link['href']
                if "patents.google.com/patent/" in href:
                    # 抓到了！這就是 Google 幫我們找到的正確頁面
                    # 有時候連結會包含多餘的 Google 參數，這裡做個簡單清理
                    if "/url?q=" in href:
                        href = href.split("/url?q=")[1].split("&")[0]
                    return href
    except Exception as e:
        print(f"Search failed: {e}")
    return None

def get_pdf_data(patent_id):
    """
    主邏輯：先嘗試直接猜測 -> 失敗則嘗試搜尋 -> 下載 PDF
    回傳: (status, filename, content_bytes)
    """
    clean_id = patent_id.strip()
    # 嘗試 1: 直接構造網址 (最快，適合公開號)
    # 我們先假設它是公開號，並嘗試去除非法字元
    guess_id = clean_id.replace(" ", "").replace("-", "").replace("/", "")
    target_url = f"https://patents.google.com/patent/{guess_id}/en"
    
    # 用來記錄最終成功的網址
    final_url = None
    
    # 先試試看直接連
    try:
        check = requests.get(target_url, headers=get_headers(), timeout=5)
        if check.status_code == 200:
            final_url = target_url
        elif check.status_code == 404:
            # 404 代表直接猜測失敗，這可能是「申請號」
            # 啟動 B 計畫：Google 搜尋
            found_url = search_google_for_url(clean_id)
            if found_url:
                final_url = found_url
    except:
        # 如果網路出錯，也嘗試搜尋看看
        found_url = search_google_for_url(clean_id)
        if found_url:
            final_url = found_url

    # 如果經過一番折騰還是沒網址，宣告失敗
    if not final_url:
        return "NOT_FOUND", None, None

    # 嘗試從最終網址抓 PDF 連結
    try:
        resp = requests.get(final_url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        pdf_link = None
        # 找連結
        for link in soup.find_all('a', href=True):
            if link['href'].endswith('.pdf'):
                pdf_link = link['href']
                break
        
        # 找 Meta tag
        if not pdf_link:
            meta = soup.find("meta", {"name": "citation_pdf_url"})
            if meta: pdf_link = meta['content']
            
        if pdf_link:
            # 下載檔案內容
            pdf_resp = requests.get(pdf_link, headers=get_headers(), timeout=15)
            if pdf_resp.status_code == 200:
                # 為了檔名漂亮，我們試著從網址解析真正的專利號 (例如從 URL 中抓取 US123456)
                real_id = final_url.split("/patent/")[-1].split("/")[0]
                return "SUCCESS", f"{real_id}.pdf", pdf_resp.content
            else:
                return "DOWNLOAD_FAIL", None, None
        else:
            return "NO_PDF_LINK", None, None
            
    except Exception as e:
        return "ERROR", None, None

# 2. 執行邏輯
if st.button("🚀 啟動萬能搜尋"):
    if patent_ids:
        raw_list = [x.strip() for x in patent_ids.split('\n') if x.strip()]
        
        zip_buffer = io.BytesIO()
        results_log = []
        success_count = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, pid in enumerate(raw_list):
                status_text.text(f"正在分析 ({i+1}/{len(raw_list)}): {pid} ...")
                
                # 呼叫主邏輯
                status, filename, content = get_pdf_data(pid)
                
                if status == "SUCCESS":
                    zf.writestr(filename, content)
                    success_count += 1
                    results_log.append(f"✅ **{pid}** -> 找到 `{filename}` (成功)")
                elif status == "NOT_FOUND":
                    results_log.append(f"❌ **{pid}**: 搜尋不到對應專利 (請確認號碼)")
                elif status == "NO_PDF_LINK":
                    results_log.append(f"⚠️ **{pid}**: 找到專利頁面但沒有 PDF 下載點")
                else:
                    results_log.append(f"⚠️ **{pid}**: 下載過程發生錯誤")
                
                progress_bar.progress((i + 1) / len(raw_list))
                # 重要：因為用了 Google 搜尋，必須多休息一下避免被鎖 IP
                time.sleep(random.uniform(2.0, 4.0))

        status_text.text("處理完成！")
        st.divider()
        
        if success_count > 0:
            zip_buffer.seek(0)
            st.success(f"🎉 成功下載 {success_count} 筆專利！")
            st.download_button(
                label="📥 下載打包檔案 (.zip)",
                data=zip_buffer,
                file_name="smart_patents_bundle.zip",
                mime="application/zip",
                type="primary"
            )
        else:
            st.error("沒有成功下載任何檔案。")

        with st.expander("查看詳細報告", expanded=True):
            for log in results_log:
                st.markdown(log)
    else:
        st.warning("請輸入案號")
