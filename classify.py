import json
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

REAL_ESTATE_KEYWORDS = [
    "bất động sản", "nhà đất", "căn hộ", "chung cư", "mua nhà", "bán nhà", "tư vấn nhà đất",
    "vinhomes", "vinhomes grand park", "đầu tư bđs", "môi giới nhà đất", "bán",
    "giá tốt", "giữ chỗ", "chủ đầu tư", "mở bán", "thanh toán", "chiết khấu", "sang nhượng",
    "shophouse", "biệt thự", "đất nền", "dự án", "giỏ hàng", "view sông", "full nội thất",
    "hợp đồng mua bán", "booking", "sở hữu lâu dài", "pháp lý", "thủ tục", "bđs","therainbow","theorigami", 
    "thebeverlyslolari","thebeverly","theopusone","mastericentrepoint","lumiereboulevard","themanhattan","themahattanglory","thegloryheight"
]

AGENT_KEYWORDS = [
    "chuyên viên", "tư vấn", "sale", "saler", "môi giới", "chuyên bán", "nhân viên kinh doanh",
    "giỏ hàng", "căn nội bộ", "ưu đãi", "chiết khấu", "giữ chỗ", "đặt cọc", "đăng ký ngay",
    "phòng kinh doanh", "liên hệ em", "call em", "inbox em", "hỗ trợ vay", "zalo"
]

OWNER_KEYWORDS = [
    "chính chủ", "gia đình", "bán gấp", "không qua trung gian", "cần tiền", "bán nhà riêng",
    "nhà mình", "tôi cần bán", "nhà của tôi", "cần bán gấp"
]

REAL_ESTATE_PATTERN = re.compile(r"\b(" + "|".join(REAL_ESTATE_KEYWORDS) + r")\b", re.IGNORECASE)
AGENT_PATTERN = re.compile(r"\b(" + "|".join(AGENT_KEYWORDS) + r")\b", re.IGNORECASE)
OWNER_PATTERN = re.compile(r"\b(" + "|".join(OWNER_KEYWORDS) + r")\b", re.IGNORECASE)

def classify_user_type(texts):
    combined_text = " ".join(texts).lower()
    if re.search(AGENT_PATTERN, combined_text):
        return ("Người bán bất động sản Vinhomes Grand Park", "Saler / Môi giới")
    elif re.search(OWNER_PATTERN, combined_text):
        return ("Người bán bất động sản Vinhomes Grand Park", "Chính chủ")
    elif re.search(REAL_ESTATE_PATTERN, combined_text):
        return ("Người bán bất động sản Vinhomes Grand Park", "Không rõ (chỉ có từ khóa BĐS)")
    else:
        return ("Người mua", "")

def load_cookies(driver, cookie_file):
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        driver.get("https://www.facebook.com")
        for cookie in cookies:
            cookie.pop("storeId", None)
            cookie.pop("id", None)
            if "sameSite" in cookie and cookie["sameSite"].lower() in ["no_restriction", "unspecified"]:
                cookie["sameSite"] = "None"
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"[WARNING] Không thể thêm cookie {cookie.get('name', 'UNKNOWN')}: {e}")
        driver.refresh()
        time.sleep(3)
        if "login" in driver.current_url:
            print("[ERROR] Cookie hết hạn hoặc sai! 🚨")
            return False
        print("[INFO] Đăng nhập thành công bằng cookie! ✅")
        return True
    except Exception as e:
        print(f"[ERROR] Lỗi khi tải cookie: {e}")
        return False

def scroll_page(driver, scrolls=3):
    for _ in range(scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

def get_facebook_posts(driver, profile_url):
    driver.get(profile_url)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except:
        print(f"[ERROR] Không thể tải trang {profile_url}!")
        return [], []
    scroll_page(driver)

    posts = []
    links = []
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "[data-ad-preview='message']")
        for el in elements:
            post_text = el.text.strip()
            if post_text:
                posts.append(post_text)
            try:
                link_el = el.find_element(By.XPATH, "..//ancestor::div[contains(@data-testid, 'story-subtitle')]//a")
                post_link = link_el.get_attribute("href")
                if post_link and "facebook.com" in post_link:
                    links.append(post_link)
            except:
                pass
    except Exception as e:
        print(f"[WARNING] Không thể lấy bài viết từ {profile_url}: {e}")
    return posts, links

def get_facebook_about(driver, profile_url):
    about_url = profile_url + "/about"
    driver.get(about_url)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except:
        print(f"[ERROR] Không thể tải trang giới thiệu {about_url}!")
        return ""
    time.sleep(3)
    about_text = ""
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "div[data-visualcompletion='ignore-dynamic']")
        for el in elements:
            about_text += el.text + " "
    except Exception as e:
        print(f"[WARNING] Không thể lấy phần giới thiệu từ {about_url}: {e}")
    return about_text.strip()

def classify_accounts(excel_file, cookie_file, output_file="output1.xlsx"):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    if not load_cookies(driver, cookie_file):
        driver.quit()
        raise RuntimeError("[ERROR] Không thể đăng nhập Facebook!")

    df = pd.read_excel(excel_file)
    urls = df["Trùng URL"].dropna().tolist()
    links_bai_viet_goc = df["Link Bài Viết"].tolist()

    results = []
    for i, url in enumerate(urls):
        print(f"[INFO] Đang kiểm tra: {url}...")
        posts, post_links_moi = get_facebook_posts(driver, url)
        about_text = get_facebook_about(driver, url)
        account_type, detail = classify_user_type(posts + [about_text])

        results.append({
            "Trùng URL": url,
            "Link Bài Viết": links_bai_viet_goc[i] if i < len(links_bai_viet_goc) else "",
            "Loại tài khoản": account_type,
            "Phân loại": detail
        })

    driver.quit()
    df_result = pd.DataFrame(results)
    df_result.to_excel(output_file, index=False)
    print(f"[INFO] ✅ Đã lưu kết quả vào {output_file}")

# Chạy tool
# classify_accounts("matched_urls.xlsx", "facebook_cookies.json")
if __name__ == "__main__":
    pass