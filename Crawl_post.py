import time
import json
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin
from bs4 import BeautifulSoup
# ------------------- COOKIE -------------------

def load_cookies(driver, cookie_file):
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        driver.get("https://www.facebook.com")
        time.sleep(3)

        for cookie in cookies:
            cookie.pop("storeId", None)
            cookie.pop("id", None)

            if "sameSite" in cookie:
                if cookie["sameSite"].lower() in ["no_restriction", "unspecified"]:
                    cookie["sameSite"] = "None"

            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"[⚠️] Không thể thêm cookie {cookie.get('name', '')}: {e}")

        print("[✅] Cookie đã được tải thành công.")
        driver.refresh()
        time.sleep(5)
        return True
    except Exception as e:
        print(f"[❌] Lỗi khi tải cookie: {e}")
        return False


def login_with_cookies(driver, post_link, cookie_file="facebook_test.json"):
    print("[INFO] Đang đăng nhập bằng cookie...")
    if not load_cookies(driver, cookie_file):
        print("[❌] Cookie không hợp lệ hoặc bị lỗi.")
        return False

    driver.get(post_link)
    time.sleep(5)
    if "login" in driver.current_url:
        print("[❌] Cookie hết hạn! Cần cập nhật cookie mới.")
        return False

    print("[✅] Đăng nhập thành công bằng cookie!")
    return True

# ------------------- SCROLL -------------------

def scroll_to_bottom(driver, max_scrolls=2):
    try:
        last_height = driver.execute_script("return document.body.scrollHeight")
        total_scrolls = 0

        while True:
            for _ in range(10):
                driver.execute_script(f"window.scrollBy(0, {last_height/10});")
                time.sleep(2)

            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                print("[✅] Đã cuộn hết nội dung.")
                break

            last_height = new_height
            total_scrolls += 1

            if max_scrolls and total_scrolls >= max_scrolls:
                print("[⚠️] Đã đạt giới hạn cuộn.")
                break

    except Exception as e:
        print(f"[❌] Lỗi khi cuộn trang: {e}")

# ------------------- SHARE LINK EXTRACTION via DOM -------------------
def extract_post_links_with_hover(driver, target_links: int, scroll_pause=1):
    """
    Trích xuất link bài viết sau khi hover vào phần tử span, dừng khi đủ target_links
    """
    # Inject override setAttribute để bắt các href thay đổi
    driver.execute_script("""
        window.collectedHrefs = [];
        const origSet = Element.prototype.setAttribute;
        Element.prototype.setAttribute = function(name, value) {
          if (this.tagName.toLowerCase() === 'a' && name === 'href') {
            window.collectedHrefs.push(value);
          }
          return origSet.apply(this, arguments);
        };
    """)
    time.sleep(0.5)

    links = []
    scrolls = 0

    while len(links) < target_links:
        scrolls += 1
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)

        # Bước 1: Hover vào các phần tử span có aria-labelledby
        try:
            span_xpath = "//a[contains(@href, '?')]//span[contains(@aria-labelledby, '«')]"
            span_elements = driver.find_elements(By.XPATH, span_xpath)
            
            for span in span_elements:
                try:
                    ActionChains(driver).move_to_element(span).pause(0.3).perform()
                    time.sleep(0.2)
                except:
                    continue
        except Exception as e:
            print(f"[⚠️] Lỗi khi hover: {str(e)}")

        # Bước 2: Thu thập các href đã được kích hoạt
        raw = driver.execute_script("return window.collectedHrefs") or []

        # Bước 3: Xử lý và lọc link
        processed_links = set()  # Dùng set để tránh trùng lặp
        for h in raw:
            if not isinstance(h, str):
                continue

            # Chuẩn hóa link
            if h.startswith("?"):
                h = urljoin("https://www.facebook.com", h)
            h = h.split("?", 1)[0]

            # Lọc link bài viết hợp lệ
            if "/groups/" in h and "/posts/" in h:
                processed_links.add(h)

        # Thêm các link mới vào kết quả
        new_links = [link for link in processed_links if link not in links]
        links.extend(new_links)

        # In thông báo cho các link mới
        for link in new_links:
            print(f"[✅] Thu thập link: {link}")

        # Kiểm tra đủ số lượng
        if len(links) >= target_links:
            print(f"[INFO] Đã đủ {target_links} link sau {scrolls} lần scroll")
            break

        # Fail-safe để tránh lặp vô hạn
        if scrolls >= 100:
            print("[WARNING] Đã scroll 100 lần nhưng chưa đủ link")
            break

    print(f"[🔗] Tổng cộng thu được {len(links)} link bài viết")
    return links[:target_links]  # Trả về đúng số lượng yêu cầu
# def extract_post_links_via_override(driver,
#                                      max_scrolls=20,
#                                      scroll_pause=1):
#     print("[INFO] Inject override setAttribute để bắt href…")
#     driver.execute_script("""
#         window.collectedHrefs = [];
#         const origSet = Element.prototype.setAttribute;
#         Element.prototype.setAttribute = function(name, value) {
#           if (this.tagName.toLowerCase() === 'a' && name === 'href') {
#             window.collectedHrefs.push(value);
#           }
#           return origSet.apply(this, arguments);
#         };
#     """)
#     time.sleep(0.2)

#     print("[INFO] Bắt đầu scroll + hover để Facebook render href…")
#     for i in range(max_scrolls):
#         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#         time.sleep(scroll_pause)
#         elems = driver.find_elements(By.XPATH, "//a[@role='link']")
#         for a in elems:
#             try:
#                 ActionChains(driver).move_to_element(a).perform()
#             except:
#                 pass

#     print("[INFO] Lấy mảng raw hrefs từ page…")
#     raw = driver.execute_script("return window.collectedHrefs") or []

#     # Normalize và lọc unique group/post links
#     links = []
#     for h in raw:
#         if not isinstance(h, str):
#             continue
#         # nếu là query string thì nối với domain
#         if h.startswith("?"):
#             h = urljoin("https://www.facebook.com", h)
#         # chỉ lấy link có /groups/ và /posts/
#         if "/groups/" in h and "/posts/" in h and h not in links:
#             links.append(h)

#     print(f"[🔗] Đã thu được {len(links)} link bài viết:")
#     for link in links:
#         print("  ", link)

#     return links
#usder find
# def extract_share_links(driver):
#     print("[INFO] Bắt đầu trích xuất các link bài viết từ DOM...")
#     links = []
#     pattern = r"https://www\.facebook\.com/(groups|posts|permalink|share|p)/"

#     # Tải lại DOM sau khi cuộn
#     anchors = driver.find_elements(By.XPATH, "//a[@role='link']")
#     for a in anchors:
#         href = a.get_attribute('href')
#         if href and re.match(pattern, href):
#             if href not in links:
#                 links.append(href)
#                 print(f"[✅] Phát hiện link: {href}")

#     print(f"[🔗] Tổng cộng tìm được {len(links)} link bài viết.")
#     return links

# def extract_share_links(driver):
#     print("[INFO] Bắt đầu phân tích DOM với BeautifulSoup...")
#     links = []
#     pattern = r"https://www\\.facebook\\.com/(groups|posts|permalink|share|watch|story\\.php|\\?fbid=|\\?story_fbid=)"

#     html = driver.page_source
#     soup = BeautifulSoup(html, "html.parser")

#     for a in soup.find_all("a", href=True):
#         href = a['href']
#         print(f"🔗 <a>: {href}")
#         if "/user/" in href or "/media/" in href:
#             continue  # Bỏ qua user và media
#         if re.search(pattern, href) and href.startswith("https://www.facebook.com"):
#             if href not in links:
#                 links.append(href)
#                 print(f"[✅] Link hợp lệ: {href}")

#     print(f"[🔗] Tổng cộng tìm được {len(links)} link bài viết.")
#     return links

# ------------------- SAVE TO EXCEL -------------------

def save_links_to_excel(post_links, filename="post_scrapping.xlsx"):
    new_df = pd.DataFrame(post_links, columns=["Link Bài Viết"])

    try:
        existing_df = pd.read_excel(filename, engine='openpyxl')
        final_df = pd.concat([existing_df, new_df], ignore_index=True)
    except FileNotFoundError:
        final_df = new_df

    with pd.ExcelWriter(filename, engine='openpyxl', mode='w') as writer:
        final_df.to_excel(writer, index=False)

    print(f"[💾] Đã lưu {len(post_links)} link vào: {filename}")

# ------------------- MAIN -------------------

def main():
    post_link = input("🔗 Nhập link nhóm Facebook cần quét: ")

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless=new")
    options.add_argument("--lang=vi-VN")
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        if not login_with_cookies(driver, post_link):
            driver.quit()
            return

        print("[🚀] Bắt đầu cuộn trang và lấy liên kết...")
        scroll_to_bottom(driver)

        post_links = extract_post_links_with_hover(driver, target_links=15)
        save_links_to_excel(post_links)
    finally:
        driver.quit()
        print("[✅] Đã hoàn tất toàn bộ quá trình!" )

if __name__ == "__main__":
    main()
