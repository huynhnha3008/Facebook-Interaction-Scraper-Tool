import time
import csv
import json
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def load_cookies(driver, cookie_file):
    """Tải cookie từ file JSON và gán vào trình duyệt"""
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        driver.get("https://www.facebook.com")
        time.sleep(3)

        for cookie in cookies:
            # Xóa các key không cần thiết
            cookie.pop("storeId", None)
            cookie.pop("id", None)

            # Kiểm tra và sửa sameSite nếu cần
            if "sameSite" in cookie:
                if cookie["sameSite"].lower() in ["no_restriction", "unspecified"]:
                    cookie["sameSite"] = "None"

            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"[WARNING] Không thể thêm cookie {cookie['name']}: {e}")

        print("[INFO] Đã tải cookie thành công! 🔥")
        driver.refresh()
        time.sleep(5)

        return True
    except Exception as e:
        print(f"[ERROR] Lỗi khi tải cookie: {e}")
        return False

def save_cookies(driver, cookie_file):
    """Lưu cookie vào file JSON sau khi đăng nhập thành công"""
    cookies = driver.get_cookies()
    with open(cookie_file, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=4)
    print("[INFO] Đã lưu cookie vào file!")

def login_with_cookies(driver, post_link, cookie_file="facebook_test.json"):
    """Tự động đăng nhập Facebook bằng cookie"""
    print("[INFO] Đang thử đăng nhập bằng cookie...")

    if not load_cookies(driver, cookie_file):
        print("[ERROR] Không thể tải cookie. Vui lòng kiểm tra lại!")
        return False

    # Mở lại bài viết sau khi đã load cookie
    driver.get(post_link)
    time.sleep(10)

    # Kiểm tra nếu vẫn bị chuyển hướng về trang đăng nhập
    if "login" in driver.current_url:
        print("[ERROR] Cookie hết hạn hoặc sai! 🚨 Vui lòng cập nhật cookie mới.")
        return False

    print("[INFO] Đăng nhập thành công bằng cookie! ✅")
    return True

def wait_for_element(driver, by, value, timeout=10):
    """Chờ phần tử hiển thị"""
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))

def scroll_to_bottom(driver, max_scrolls=None):
    try:
        # Kiểm tra xem có phần tử cần cuộn không
        try:
            scrollable_div = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div[1]/div/div[5]/div/div/div[2]/div/div/div/div/div/div/div/div[2]"))
            )
            use_custom_scroll = True
            print("✅ Đã tìm thấy phần tử scroll, sử dụng cuộn trong phần tử này!")
        except:
            use_custom_scroll = False
            print("⚠️ Không tìm thấy phần tử scroll, dùng cách cuộn toàn trang!")

        # Lấy chiều cao ban đầu
        if use_custom_scroll:
            last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
        else:
            last_height = driver.execute_script("return document.body.scrollHeight")

        total_scrolls = 0

        while True:  # Vòng lặp vô hạn, dừng khi không còn nội dung mới
            for i in range(3):  # Cuộn thành 3 bước nhỏ
                if use_custom_scroll:
                    driver.execute_script("arguments[0].scrollBy(0, arguments[0].scrollHeight / 3);", scrollable_div)
                else:
                    driver.execute_script(f"window.scrollBy(0, {last_height/3});")
                time.sleep(1)

            time.sleep(15)  # Đợi nội dung tải xong

            # Kiểm tra chiều cao mới sau khi cuộn
            if use_custom_scroll:
                new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            else:
                new_height = driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                print("✅ Cuộn hoàn tất! Không còn nội dung mới.")
                break  # Dừng cuộn nếu không còn nội dung mới

            last_height = new_height
            total_scrolls += 1

            # Nếu có giới hạn max_scrolls và đã đạt giới hạn thì dừng
            if max_scrolls and total_scrolls >= max_scrolls:
                print("⚠️ Đã đạt giới hạn số lần cuộn!")
                break

    except Exception as e:
        print(f"[ERROR] Lỗi khi cuộn: {e}")

def expand_all_comments(driver):
    """Click tất cả nút 'Xem thêm bình luận' và cuộn xuống nếu cần"""
    print("[INFO] Bắt đầu mở rộng tất cả bình luận...")

    # Tìm container chứa danh sách bình luận (thường là div có scrollable)
    try:
        comment_container = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div[1]/div/div[5]/div/div/div[2]/div/div/div/div/div/div/div/div[2]"))
            )
    except Exception as e:
        print(f"[WARNING] Không tìm thấy container bình luận, sử dụng document.body: {e}")
        comment_container = driver.execute_script("return document.body")

    # Số lần tối đa không tìm thấy nút trước khi dừng
    max_attempts_without_buttons = 3
    attempts_without_buttons = 0

    while True:
        try:
            # Tìm tất cả nút "Xem thêm bình luận" hoặc "bình luận trước"
            buttons = driver.find_elements(By.XPATH, 
                "//span[contains(text(), 'Xem thêm bình luận')] | //span[contains(text(), 'bình luận trước')] | //span[contains(text(), 'Xem thêm trả lời')] | //span[contains(text(), 'View more comments')] ")

            if not buttons:
                attempts_without_buttons += 1
                print(f"[INFO] Không tìm thấy nút mở rộng bình luận (lần {attempts_without_buttons}/{max_attempts_without_buttons}).")
                if attempts_without_buttons >= max_attempts_without_buttons:
                    print("[INFO] Đã thử đủ lần mà không tìm thấy nút nữa, dừng lại.")
                    break
            else:
                attempts_without_buttons = 0  # Reset đếm nếu tìm thấy nút

            for btn in buttons:
                try:
                    # Cuộn đến nút và click
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)  # Đợi ổn định
                    driver.execute_script("arguments[0].click();", btn)
                    print("[INFO] Đã click vào một nút 'Xem thêm bình luận' hoặc 'bình luận trước'.")
                    time.sleep(3)  # Đợi lâu hơn để nội dung tải hoàn toàn
                except Exception as e:
                    print(f"[WARNING] Không thể click vào nút: {e}")

            # Cuộn container chứa bình luận để kích hoạt lazy loading
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", comment_container)
            print("[INFO] Đã cuộn container bình luận đến cuối.")
            time.sleep(3)  # Đợi nội dung mới tải

        except Exception as e:
            print(f"[ERROR] Lỗi khi mở rộng bình luận: {e}")
            break

    print("[INFO] Hoàn thành mở rộng tất cả bình luận.")

def extract_user_links_and_comments(driver):
    """Trích xuất link user và nội dung comment"""
    html_source = driver.page_source
    
    soup = BeautifulSoup(html_source, "html.parser")
    
    comment_blocks = soup.select("div[role='article']")
    print(f"[INFO] Tìm thấy {len(comment_blocks)} khối bình luận.")

    comments_data = []
    
    for block in comment_blocks:
        try:
            user_link = "N/A"
            profile_link_tag = block.find("a", href=re.compile(r"https://www\.facebook\.com/[^?]+"))
            if profile_link_tag and profile_link_tag["href"].startswith("https://www.facebook.com/"):
                user_link = profile_link_tag["href"].split("?")[0]
                if "/profile.php" in user_link or "/groups/" in user_link or "/posts/" in user_link:
                    user_link = "N/A"

            comment_text = "N/A"
            comment_text_tag = block.find("div", {"dir": "auto"})
            if comment_text_tag:
                comment_text = comment_text_tag.get_text(strip=True)

            if user_link != "N/A" or comment_text != "N/A":
                comments_data.append((user_link, comment_text))
        except Exception as e:
            print(f"[ERROR] Lỗi khi trích xuất dữ liệu: {e}")
    
    return comments_data  # Luôn trả về danh sách, ngay cả khi rỗng



#################Start of Code để extract React bài viết #####################
def convert_like_count(like_text: str) -> int:
    """Chuyển đổi số lượt thích từ dạng văn bản (1k, 1.2M) sang số nguyên."""
    like_text = like_text.lower().replace(',', '').strip()

    match = re.match(r'(\d+(\.\d+)?)([kKmM]?)', like_text)
    if match:
        number = float(match.group(1))  # Lấy phần số
        unit = match.group(3)  # Lấy đơn vị (k hoặc M)

        if unit == 'k':  # Nếu có 'k' nghĩa là hàng nghìn
            return int(number * 1000)
        elif unit == 'm':  # Nếu có 'm' nghĩa là hàng triệu
            return int(number * 1000000)
        else:
            return int(number)  # Nếu không có đơn vị, trả về số nguyên

    return 0  # Trả về 0 nếu không thể chuyển đổi

def get_total_likes(driver, scroll_div=None):
    """Lấy tổng số người tương tác từ bài viết, ưu tiên lấy trong vùng scroll_div trước"""
    try:
        like_count_element = None

        if scroll_div:
            try:
                # Tìm số lượt like trong vùng scroll_div
                like_count_element = scroll_div.find_element(By.CSS_SELECTOR, "span.xt0b8zv.x1jx94hy.xrbpyxo.xl423tq span.x1e558r4")
                print("✅ Lấy tổng số likes từ scroll_div!")
            except:
                print("⚠️ Không tìm thấy tổng số likes trong scroll_div, thử tìm toàn trang...")

        if not like_count_element:
            # Nếu không tìm thấy trong scroll_div, tìm trên toàn trang
            like_count_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.xt0b8zv.x1jx94hy.xrbpyxo.xl423tq span.x1e558r4"))
            )
            print("✅ Lấy tổng số likes từ toàn trang!")

        raw_like_text = like_count_element.text  # Lấy text thô
        total_likes = convert_like_count(raw_like_text)  # Chuyển đổi sang số nguyên
        print(f"🔢 Tổng số người tương tác: {total_likes}")
        return total_likes

    except Exception as e:
        print(f"[ERROR] Không thể lấy tổng số likes: {e}")
        return 0  # Trả về 0 nếu không lấy được dữ liệu


def get_reacted_users(driver):
    """Mở danh sách người đã tương tác, thử lăn trước, nếu lăn được thì bấm nút trong scroll_div, nếu không thì nhấn nút toàn trang"""
    print("🔍 Đang thử lăn chuột trước để tìm nút mở danh sách reaction...")

    scroll_success = False
    react_button = None
    scroll_div = None

    try:
        # Tìm vùng cuộn bằng XPath mới
        scroll_div = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[1]/div/div[5]/div/div/div[2]/div/div/div/div/div/div/div/div[2]'))
        )

        for _ in range(3):  # Thử lăn vài lần
            driver.execute_script("arguments[0].scrollTop += 300;", scroll_div)
            time.sleep(2)

        scroll_success = True
        print("✅ Đã lăn chuột thành công!")

        # Sau khi lăn, tìm react_button nhưng chỉ trong scroll_div
        react_button = scroll_div.find_element(By.CSS_SELECTOR, "span.xt0b8zv.x1jx94hy.xrbpyxo.xl423tq")
        print("✅ Đã tìm thấy nút mở danh sách reaction bên trong vùng cuộn!")

    except:
        print("⚠️ Không thể lăn chuột hoặc không tìm thấy vùng cuộn!")

    if not react_button:
        try:
            # Nếu không tìm được trong vùng cuộn, tìm nút toàn trang
            react_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "span.xt0b8zv.x1jx94hy.xrbpyxo.xl423tq"))
            )
            print("✅ Đã tìm thấy nút mở danh sách reaction toàn trang!")
        except:
            print("❌ Không tìm thấy hoặc không thể nhấn nút mở danh sách reaction! Thoát.")
            return []

    # Nếu lăn thành công thì cuộn đến nút trong scroll_div, nếu không thì cuộn đến nút toàn trang
    driver.execute_script("arguments[0].scrollIntoView();", react_button)
    time.sleep(5)

    driver.execute_script("arguments[0].click();", react_button)
    time.sleep(30)  # Đợi danh sách load

    print("✅ Đã mở danh sách người tương tác!")

    print("🔍 Đang kiểm tra danh sách người tương tác...")
    total_likes = get_total_likes(driver, scroll_div)  # Cập nhật: Truyền scroll_div vào

    try:
        users_list_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x78zum5.xdt5ytf.x1iyjqo2.x7ywyr2"))
        )
        print("✅ Danh sách người tương tác đã xuất hiện!")
    except:
        print("❌ Không tìm thấy danh sách người tương tác!")
        return []

    print("🔍 Đang cuộn danh sách để lấy đủ dữ liệu...")
    scroll_likes_section(driver, total_likes)  # Cuộn theo tổng số react

    print("✅ Đã load hết danh sách!")

    # Lấy danh sách link người like
    html_content = driver.page_source
    reacted_users = extract_fixed_links(html_content)

    # 🆕 Đóng danh sách reaction sau khi lấy dữ liệu
    print("🔴 Đang đóng danh sách reaction...")
    try:
        close_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[aria-label='Đóng']"))
        )
        close_button.click()
        print("✅ Đã đóng danh sách reaction!")
    except:
        print("⚠️ Không tìm thấy nút đóng! Thử nhấn ESC...")
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            print("✅ Đã đóng danh sách bằng ESC!")
        except:
            print("❌ Không thể đóng danh sách reaction!")

    return reacted_users



def extract_fixed_links(html_content):
    """Trích xuất tất cả link từ thẻ <a> có class cố định."""
    soup = BeautifulSoup(html_content, "html.parser")

    target_classes = "x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz xkrqix3 x1sur9pj xzsf02u x1pd3egz"

    links = []
    for a_tag in soup.find_all("a", class_=target_classes):
        href = a_tag.get("href")
        if href:
            links.append(href)

    return links


def scroll_likes_section(driver, total_likes, wait_time=15):
    """Cuộn danh sách likes để load hết dữ liệu dựa trên tổng số likes."""
    try:
        print("🔍 Đang tìm phần tử scroll...")

        # CSS Selector của danh sách reaction (bạn cung cấp)
        scroll_selector = "body > div.__fb-light-mode.x1n2onr6.xzkaem6 > div.x9f619.x1n2onr6.x1ja2u2z > div > div.x1uvtmcs.x4k7w5x.x1h91t0o.x1beo9mf.xaigb6o.x12ejxvf.x3igimt.xarpa2k.xedcshv.x1lytzrv.x1t2pt76.x7ja8zs.x1n2onr6.x1qrby5j.x1jfb8zj > div > div > div > div > div > div > div.xb57i2i.x1q594ok.x5lxg6s.x78zum5.xdt5ytf.x6ikm8r.x1ja2u2z.x1pq812k.x1rohswg.xfk6m8.x1yqm8si.xjx87ck.xx8ngbg.xwo3gff.x1n2onr6.x1oyok0e.x1odjw0f.x1iyjqo2.xy5w88m > div.x78zum5.xdt5ytf.x1iyjqo2.x1n2onr6.xaci4zi.x129vozr > div > div"

        scrollable_div = None
        try:
            scrollable_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, scroll_selector))
            )
            print(f"✅ Đã tìm thấy phần tử scroll bằng CSS Selector!")
        except:
            print("❌ Không tìm thấy danh sách scroll, kiểm tra lại giao diện!")
            return []

        print("🔍 Đang cuộn danh sách để lấy đủ dữ liệu...")

        last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
        scanned_users = set()
        scroll_attempts = 0

        while len(scanned_users) < total_likes:
            driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", scrollable_div)
            time.sleep(wait_time)

            html_content = driver.page_source
            new_users = set(extract_fixed_links(html_content))  # Hàm extract_fixed_links lấy user từ HTML
            old_size = len(scanned_users)
            scanned_users.update(new_users)

            print(f"📌 Lần cuộn {scroll_attempts + 1}: {len(scanned_users)} / {total_likes} users")

            if len(scanned_users) == old_size:
                print("✅ Không còn user mới, dừng cuộn!")
                break

            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            if new_height == last_height:
                print("✅ Cuộn hoàn tất hoặc không còn nội dung mới!")
                break

            last_height = new_height
            scroll_attempts += 1

        return list(scanned_users)

    except Exception as e:
        print(f"[ERROR] Lỗi khi cuộn danh sách: {e}")
        return []




#################End of Code để extract React bài viết #####################
# def save_to_csv(data, filename="user_comments.xlsx"):
#     """Lưu dữ liệu vào file Excel (.xlsx) để hiển thị đúng font tiếng Việt"""
#     df = pd.DataFrame(data, columns=["Link User Comment", "Nội dung Comment"])
#     df.to_excel(filename, index=False, engine='openpyxl')
#     print(f"[INFO] Dữ liệu đã được lưu vào {filename}")

def save_to_csv(post_link, param1, param2, filename="data_scrapping.xlsx"):
    """
    Lưu dữ liệu vào file Excel (.xlsx) mà không ghi đè dữ liệu cũ, bao gồm cả đường link bài viết.
    
    post_link: Đường link bài viết cần cào.
    param1: Danh sách link user react (dạng list).
    param2: Danh sách tuple (link user comment, nội dung comment).
    filename: Tên file xuất ra.
    """
    
    # Tạo danh sách dữ liệu mới để ghi thêm
    data = []
    
    # Ghi danh sách user react với đường link bài viết
    for user_react in param1:
        data.append([post_link, user_react, "", "", ""])  # Chỉ có link bài viết và link user react
    
    # Ghi danh sách user comment + nội dung với đường link bài viết
    for user_comment, comment_content in param2:
        data.append([post_link, "", user_comment, comment_content, ""])  # Chỉ có link bài viết, link user comment và nội dung
    
    # Tạo DataFrame mới
    new_df = pd.DataFrame(data, columns=["Link Bài Viết", "Link User React", "Link User Comment", "Nội dung Comment", "Đánh giá User"])
    
    try:
        # Nếu file đã tồn tại, đọc dữ liệu cũ rồi append dữ liệu mới
        existing_df = pd.read_excel(filename, engine='openpyxl')
        final_df = pd.concat([existing_df, new_df], ignore_index=True)
    except FileNotFoundError:
        # Nếu file chưa tồn tại, chỉ cần lưu dữ liệu mới
        final_df = new_df

    # Ghi dữ liệu vào file Excel
    with pd.ExcelWriter(filename, engine='openpyxl', mode='w') as writer:
        final_df.to_excel(writer, index=False)
    
    print(f"[INFO] Dữ liệu đã được thêm vào {filename}")


def main():
    post_link = input("Nhập link bài viết cần cào comment: ")
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    if not login_with_cookies(driver, post_link):
        print("[ERROR] Đăng nhập thất bại!")
        driver.quit()
        return

    print("[INFO] Truy cập bài viết...")
    driver.get(post_link)
    time.sleep(5)

    # Cào danh sách những người đã react bài viết
    reacted_users = get_reacted_users(driver)

    if not reacted_users:
        print("[WARNING] Không có dữ liệu người like! Kiểm tra lại quá trình scroll.")

    print("[INFO] Cuộn xuống và mở rộng comment...")
    scroll_to_bottom(driver)
    
    # Cào bình luận từ bài viết
    comments_data = extract_user_links_and_comments(driver)

    if not comments_data:
        print("[WARNING] Không có dữ liệu comment! Có thể bài viết không có bình luận hoặc không tải được.")

    # Gọi `save_to_csv` với danh sách có thể rỗng, nhưng không gây lỗi
    save_to_csv(post_link, reacted_users, comments_data)

    driver.quit()

if __name__ == "__main__":
    main()