# fju_scraper.py
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

BASE_URL = "https://www.math.fju.edu.tw"

# 要爬的類別：(tag名稱, 路徑)
CATEGORIES = [
    ("系所公告",     "/zh-hant/news/系所公告"),
    ("課程公告",     "/zh-hant/news/課程公告/學士班"),
    ("碩士班課程",   "/zh-hant/news/課程公告/碩士班"),
    ("演講公告",     "/zh-hant/news/演講公告"),
    ("獎助學金",     "/zh-hant/news/獎助學金公告"),
    ("課外活動",     "/zh-hant/news/課外活動與徵才"),
    ("服務學習",     "/zh-hant/news/服務學習"),
]

PAGES_PER_CATEGORY = 2   # 每類抓 2 頁 = 20 筆
ITEMS_PER_PAGE     = 10


def scrape_category(driver, tag, path):
    """爬單一類別的多頁，回傳 list of dict"""
    results = []

    for page in range(PAGES_PER_CATEGORY):
        start = page * ITEMS_PER_PAGE
        url   = f"{BASE_URL}{path}?start={start}" if start > 0 else f"{BASE_URL}{path}"

        try:
            driver.get(url)
            time.sleep(2)

            rows = driver.find_elements(By.CSS_SELECTOR, "table.category tbody tr")
            if not rows:
                break   # 這頁沒資料就停

            for row in rows:
                try:
                    date_text = row.find_element(By.CSS_SELECTOR, "td.list-date").text.strip()
                    date_parts = date_text.split('/')
                    # 原始格式 yyyy/mm/dd → 存成 yyyy-mm-dd
                    if len(date_parts) == 3:
                        formatted_date = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]}"
                    else:
                        formatted_date = date_text

                    title_el   = row.find_element(By.CSS_SELECTOR, "td.list-title a")
                    title_text = title_el.text.strip()
                    link_href  = title_el.get_attribute("href")

                    results.append({
                        "date":  formatted_date,
                        "tag":   tag,
                        "title": title_text,
                        "link":  link_href,
                        "sort_key": date_text,   # 原始 yyyy/mm/dd 用來排序
                    })
                except Exception as e:
                    print(f"  ⚠️ 單筆解析失敗，略過：{e}")
                    continue

        except Exception as e:
            print(f"  ❌ 頁面載入失敗 {url}：{e}")
            break

    return results


def run_scraper(db, News, app_context):
    print("🚀 啟動瀏覽器，準備多類別爬取...")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = webdriver.Chrome(options=options)

    try:
        all_items = []

        for tag, path in CATEGORIES:
            print(f"📂 爬取類別：{tag}")
            items = scrape_category(driver, tag, path)
            print(f"   取得 {len(items)} 筆")
            all_items.extend(items)

        # 依日期新到舊排序（sort_key 格式 yyyy/mm/dd 可直接字串排序）
        all_items.sort(key=lambda x: x["sort_key"], reverse=True)

        with app_context:
            new_count = 0
            for item in all_items:
                existing = News.query.filter_by(link=item["link"]).first()
                if not existing:
                    db.session.add(News(
                        date=item["date"],
                        tag=item["tag"],
                        title=item["title"],
                        link=item["link"],
                    ))
                    new_count += 1

            db.session.commit()
            print(f"✅ 爬蟲完成，新增 {new_count} 筆，資料庫更新完畢")

    except Exception as e:
        print(f"❌ 爬蟲整體失敗：{e}")
    finally:
        driver.quit()
