# scraper.py
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def run_scraper():
    """負責爬取輔大數學系系所公告，並將結果存入 JSON 檔案"""
    
    print("啟動無頭瀏覽器，準備爬取資料...")
    options = Options()
    options.add_argument("--headless") # 無頭模式，不會跳出視窗
    options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(options=options)
    
    # 這是你要爬的目標網址
    target_url = "https://www.math.fju.edu.tw/zh-hant/news/%E7%B3%BB%E6%89%80%E5%85%AC%E5%91%8A"
    
    try:
        driver.get(target_url)
        time.sleep(2) # 給網頁一點時間載入
        
        scraped_data = []
        
        # 1. 鎖定 tbody 裡面的所有 tr (每一列就是一篇公告)
        # 使用 CSS 選擇器精準定位
        rows = driver.find_elements(By.CSS_SELECTOR, "table.category tbody tr")
        
        # 為了避免抓太多，我們設定只抓最新前 6 筆公告
        for i, row in enumerate(rows[:6]):
            try:
                # 2. 抓取日期 (class 為 list-date)
                # 網頁上的格式是 "2026/05/05"
                date_text = row.find_element(By.CSS_SELECTOR, "td.list-date").text.strip()
                
                # 將 "2026/05/05" 轉換成我們前端要的格式 "05-05"
                date_parts = date_text.split('/')
                if len(date_parts) == 3:
                    formatted_date = f"{date_parts[1]}-{date_parts[2]}"
                else:
                    formatted_date = date_text # 備用防呆
                
                # 3. 抓取標題與連結 (class 為 list-title 裡面的 a 標籤)
                title_element = row.find_element(By.CSS_SELECTOR, "td.list-title a")
                title_text = title_element.text.strip()
                link_href = title_element.get_attribute("href")
                
                # 4. 整理成字典格式
                news_item = {
                    "id": i + 1,
                    "date": formatted_date,
                    "tag": "系所公告", # 統一加上標籤
                    "title": title_text,
                    "link": link_href # 把真實連結也抓下來，以後可以讓前端點擊跳轉
                }
                
                scraped_data.append(news_item)
                print(f"成功抓取: {title_text}")
                
            except Exception as e:
                print(f"抓取單筆資料時發生錯誤略過: {e}")
                continue

        # 5. 寫入 JSON 檔案
        with open("news.json", "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=4)
            
        print("✅ 爬蟲執行完畢，輔大數學系最新消息已更新至 news.json！")
            
    except Exception as e:
        print(f"爬蟲整體執行失敗: {e}")
    finally:
        driver.quit() # 確保關閉瀏覽器

# 測試用：如果直接執行這個檔案，就會跑跑看爬蟲
if __name__ == "__main__":
    run_scraper()