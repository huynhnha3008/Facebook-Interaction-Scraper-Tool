import time
import json
import cv2
import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from collections import Counter
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
# Cấu hình Selenium (Chrome)
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")  # Chạy nền để không mở trình duyệt
chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Tránh bị Facebook phát hiện
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)
service = Service(ChromeDriverManager().install())  # Cập nhật ChromeDriver tự động
def load_cookies(driver, cookie_file):
    """Tải cookie từ file JSON và gán vào trình duyệt"""
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        driver.get("https://www.facebook.com")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        for cookie in cookies:
            cookie.pop("storeId", None)
            cookie.pop("id", None)

            if "sameSite" in cookie and cookie["sameSite"].lower() in ["no_restriction", "unspecified"]:
                cookie["sameSite"] = "None"

            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"[WARNING] Không thể thêm cookie {cookie.get('name', 'UNKNOWN')}: {e}")

        print("[INFO] Đã tải cookie thành công! 🔥")
        driver.refresh()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        return True
    except Exception as e:
        print(f"[ERROR] Lỗi khi tải cookie: {e}")
        return False

def login_with_cookies(driver, post_link, cookie_file="facebook_test.json"):
    """Tự động đăng nhập Facebook bằng cookie"""
    print("[INFO] Đang thử đăng nhập bằng cookie...")

    if not load_cookies(driver, cookie_file):
        print("[ERROR] Không thể tải cookie. Vui lòng kiểm tra lại!")
        return False

    driver.get(post_link)
    
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except:
        print("[ERROR] Không thể tải bài viết! Có thể tài khoản bị chặn.")
        return False

    if "login" in driver.current_url:
        print("[ERROR] Cookie hết hạn hoặc sai! 🚨 Vui lòng cập nhật cookie mới.")
        return False

    print("[INFO] Đăng nhập thành công bằng cookie! ✅")
    return True

# Đọc danh sách tài khoản từ file Excel
def read_accounts_from_excel(file_path):
    df = pd.read_excel(file_path)
    return df["Link User"].tolist()
def check_blur(image_url):
    try:
        resp = requests.get(image_url, stream=True)
        if resp.status_code != 200:
            print(f"[ERROR] Không thể tải ảnh: {image_url}")
            return False

        image = np.asarray(bytearray(resp.raw.read()), dtype="uint8")
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        if image is None:
            print(f"[ERROR] Không thể giải mã ảnh: {image_url}")
            return False

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        return variance < 100
    except Exception as e:
        print(f"[ERROR] Không thể kiểm tra độ mờ của ảnh: {e}")
        return False
    
def check_duplicate_full_names(driver):
    try:
        friend_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'friend_name')]")
        friend_names = [friend.text.strip() for friend in friend_elements if friend.text.strip()]
        
        if not friend_names:
            return 0
        
        name_counts = Counter(friend_names)
        duplicate_ratio = sum(count for count in name_counts.values() if count > 1) / len(friend_names)
        
        return -10 if duplicate_ratio > 0.3 else 0
    except Exception as e:
        print(f"[ERROR] Không thể kiểm tra trùng lặp họ tên: {e}")
        return 0

foreign_keywords = ["Kumar", "Singh", "Ali", "Hussain", "Patel"]

def check_foreign_friends(driver):
    try:
        friend_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'friend_name')]")
        friend_names = [friend.text.strip().lower() for friend in friend_elements if friend.text.strip()]
        
        if not friend_names:
            return 0
        
        foreign_friends = sum(1 for name in friend_names if any(keyword.lower() in name for keyword in foreign_keywords))
        foreign_ratio = foreign_friends / len(friend_names)
        
        return -10 if foreign_ratio > 0.5 else 0
    except Exception as e:
        print(f"[ERROR] Không thể kiểm tra bạn bè nước ngoài: {e}")
        return 0

def check_interactions(driver):
    try:
        posts = driver.find_elements(By.XPATH, "//div[@role='article']")
        if not posts:
            return -10  # Không có bài viết → trừ điểm

        total_likes = 0
        total_comments = 0 

        for post in posts[:5]:  # Kiểm tra 5 bài viết gần nhất
            like_elements = post.find_elements(By.XPATH, ".//span[contains(@aria-label, 'like') or contains(@innerText, 'likes')]")
            comment_elements = post.find_elements(By.XPATH, ".//span[contains(@aria-label, 'comment') or contains(@innerText, 'comments')]")

            if like_elements:
                total_likes += int(''.join(filter(str.isdigit, like_elements[0].get_attribute("innerText"))))
            if comment_elements:
                total_comments += int(''.join(filter(str.isdigit, comment_elements[0].get_attribute("innerText"))))

        if total_likes + total_comments < 5:
            return -10  # Ít hơn 5 lượt tương tác → trừ điểm
        return 0
    except Exception as e:
        print(f"[ERROR] Không thể kiểm tra tương tác: {e}")
        return 0

def count_photos(driver):
    """Đếm số lượng ảnh trên trang Facebook Photos bằng cách cuộn xuống"""
    photos_count = 0
    try:
        # Tìm và click vào link Photos
        photos_link = driver.find_element(By.XPATH, "//a[contains(@href, 'photos')]")
        photos_link.click()
        time.sleep(3)  # Chờ trang load

        # Lấy phần thân của trang để cuộn
        body = driver.find_element(By.TAG_NAME, "body")

        last_count = 0
        retries = 3  # Số lần thử nếu không có ảnh mới

        while retries > 0:
            # Lấy danh sách ảnh hiện tại
            photos_elements = driver.find_elements(By.XPATH, "//img[contains(@src, 'scontent')]")
            photos_count = len(photos_elements)

            if photos_count > last_count:
                last_count = photos_count
                retries = 3  # Reset lại retries nếu có ảnh mới
            else:
                retries -= 1  # Giảm số lần thử nếu không có ảnh mới

            # Cuộn xuống để tải thêm ảnh
            body.send_keys(Keys.END)
            time.sleep(2)  # Chờ ảnh tải

    except Exception as e:
        print(f"[ERROR] Không thể kiểm tra số ảnh: {e}")

    print(f"[INFO] Số ảnh: {photos_count}")
    return photos_count


def check_account(driver, url):
    driver.get(url)
    time.sleep(5)
    try:
        # 1. Lấy tên và check profile khóa
        name = driver.find_element(By.TAG_NAME, "h1").text.strip()
        locked_profile = (
            "locked his profile" in driver.page_source
            or "has locked their profile" in driver.page_source
            or "đã khóa bảo vệ trang cá nhân" in driver.page_source
        )
        if locked_profile:
            return {"url": url, "name": name, "locked_profile": True, "score": 0}
        
        mutual_count = 0
        try:
            mutual_elem = driver.find_element(
                By.XPATH,
                "//a[contains(@href, '/friends_mutual/')]"
            )
            mutual_text = mutual_elem.text
            digits_m = ''.join(filter(str.isdigit, mutual_text))
            mutual_count = int(digits_m) if digits_m else 0
        except NoSuchElementException:
            mutual_count = 0
        print(f"[INFO] Số bạn chung: {mutual_count}")
        details = {
            "Mutualfriends": mutual_count,
            "HasStories": bool(driver.find_elements(By.XPATH, "//a[contains(@href, '/stories/')]")),
            "Email_verified": bool(driver.find_elements(By.XPATH,"//a[starts-with(@href,'mailto:')] | //span[contains(text(),'@') and contains(text(),'.')]")),
            "Youtube": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'youtube.com')]")),
            "Twitter_X": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'twitter.com') or contains(@href, 'x.com')]")),
            "Linktree": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'linktr.ee')]")),
            "Behance": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'behance.net')]")),
            "Medium": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'medium.com')]")),
            "Discord": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'discord.gg') or contains(@href, 'discord.com')]")),
            "Telegram": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 't.me')]")),
            "Reddit": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'reddit.com')]")),
            "SoundCloud": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'soundcloud.com')]")),
            "Work": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Works at') or contains(text(), 'Làm việc tại')]") ),
            # "Education": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Studied at') or contains(text(), 'Học tại')]") ),
            "Lives": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Lives in') or contains(text(), 'Sống tại')]") ),
            "Birthday": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Born on') or contains(text(), 'Sinh nhật')]") ),
            "Checkins": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Check-ins') or contains(text(), 'Đã ghé thăm')]") ),
            "Instagram": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'instagram.com')]") ),
            "Phone_verified": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Phone number') or contains(text(), 'Số điện thoại')]") ),
            "Goes_to": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Goes to') or contains(text(), 'Học ở')]") ),
            "Studied": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Studied') or contains(text(), 'Học')]") ),
            "Went_to": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Went to') or contains(text(), 'Đã học tại')]") ),
            "Chu_tich_at": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Chu tich at') or contains(text(), 'Chu tich tại')]") ),
            "Tông_giam_đôc_at": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Tông giam đôc at') or contains(text(), 'Tông giam đôc tại')]") ),
            "Relationship": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'In a relationship') or contains(text(), 'Đang hẹn hò') or contains(text(), 'Single') or contains(text(), 'Độc thân') or contains(text(), 'Married') or contains(text(), 'Đã kết hôn')]") ),
            "Followed by": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Followed by') or contains(text(), 'theo dõi')]") ),
            "followers": bool(driver.find_elements(By.XPATH,"//a[contains(@href, '/followers/') and (contains(., 'followers') or contains(., 'người theo dõi'))]")),
            "following": bool(driver.find_elements(By.XPATH,"//a[contains(@href, '/following/') and (contains(., 'following') or contains(., 'đang theo dõi'))]")),
            "From": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'From') or contains(text(), 'Đến Từ')]") ),
            "Manager_at": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Manager at') or contains(text(), 'Manager tại')]") ),
            "Joined_on": bool(driver.find_elements(By.XPATH, "//span[contains(text(), 'Joined on') or contains(text(), 'Tham gia vào')]") ),
            "Github": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'github.com')]") ),
            "TikTok": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'tiktok.com')]") ),
            "Vercel": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'vercel.app')]") ),
            "PlayerDuo": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'playerduo.com')]") ),
            "Threads": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'threads.net')]") ),
            "Spotify": bool(driver.find_elements(By.XPATH, "//a[contains(@href, 'open.spotify.com')]") )
        }
        youtube_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'youtube.com')]")
        print(f"[DEBUG] YouTube Elements Found: {len(youtube_elements)}")
        youtube_link = youtube_elements[0].get_attribute("href") if youtube_elements else None
        print(f"[DEBUG] YouTube Link: {youtube_link}")

        twitter_x_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'twitter.com') or contains(@href, 'x.com')]")
        print(f"[DEBUG] Twitter/X Elements Found: {len(twitter_x_elements)}")
        twitter_x_link = twitter_x_elements[0].get_attribute("href") if twitter_x_elements else None
        print(f"[DEBUG] Twitter/X Link: {twitter_x_link}")

        linktree_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'linktr.ee')]")
        print(f"[DEBUG] Linktree Elements Found: {len(linktree_elements)}")
        linktree_link = linktree_elements[0].get_attribute("href") if linktree_elements else None
        print(f"[DEBUG] Linktree Link: {linktree_link}")

        behance_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'behance.net')]")
        print(f"[DEBUG] Behance Elements Found: {len(behance_elements)}")
        behance_link = behance_elements[0].get_attribute("href") if behance_elements else None
        print(f"[DEBUG] Behance Link: {behance_link}")

        medium_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'medium.com')]")
        print(f"[DEBUG] Medium Elements Found: {len(medium_elements)}")
        medium_link = medium_elements[0].get_attribute("href") if medium_elements else None
        print(f"[DEBUG] Medium Link: {medium_link}")

        discord_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'discord.gg') or contains(@href, 'discord.com')]")
        print(f"[DEBUG] Discord Elements Found: {len(discord_elements)}")
        discord_link = discord_elements[0].get_attribute("href") if discord_elements else None
        print(f"[DEBUG] Discord Link: {discord_link}")

        telegram_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 't.me')]")
        print(f"[DEBUG] Telegram Elements Found: {len(telegram_elements)}")
        telegram_link = telegram_elements[0].get_attribute("href") if telegram_elements else None
        print(f"[DEBUG] Telegram Link: {telegram_link}")

        reddit_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'reddit.com')]")
        print(f"[DEBUG] Reddit Elements Found: {len(reddit_elements)}")
        reddit_link = reddit_elements[0].get_attribute("href") if reddit_elements else None
        print(f"[DEBUG] Reddit Link: {reddit_link}")

        soundcloud_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'soundcloud.com')]")
        print(f"[DEBUG] SoundCloud Elements Found: {len(soundcloud_elements)}")
        soundcloud_link = soundcloud_elements[0].get_attribute("href") if soundcloud_elements else None
        print(f"[DEBUG] SoundCloud Link: {soundcloud_link}")

        github_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'github.com')]")
        print(f"[DEBUG] GitHub Elements Found: {len(github_elements)}")
        github_link = github_elements[0].get_attribute("href") if github_elements else None
        print(f"[DEBUG] GitHub Link: {github_link}")

        tiktok_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'tiktok.com')]")
        print(f"[DEBUG] TikTok Elements Found: {len(tiktok_elements)}")
        tiktok_link = tiktok_elements[0].get_attribute("href") if tiktok_elements else None
        print(f"[DEBUG] Tiktok Link: {tiktok_link}")

        Vercel_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'vercel.app')]")
        print(f"[DEBUG] Vercel Elements Found: {len(Vercel_elements)}")
        Vercel_link = Vercel_elements[0].get_attribute("href") if Vercel_elements else None
        print(f"[DEBUG] Vercel Link: {Vercel_link}")

        PlayerDuo_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'playerduo.com')]")
        print(f"[DEBUG] PlayerDuo Elements Found: {len(PlayerDuo_elements)}")
        PlayerDuo_link = PlayerDuo_elements[0].get_attribute("href") if PlayerDuo_elements else None
        print(f"[DEBUG] PlayerDuo Link: {PlayerDuo_link}")

        Threads_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'threads.net')]")
        print(f"[DEBUG] Threads Elements Found: {len(Threads_elements)}")
        Threads_link = Threads_elements[0].get_attribute("href") if Threads_elements else None
        print(f"[DEBUG] Thread Link: {Threads_link}")

        Spotify_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'open.spotify.com')]")
        print(f"[DEBUG] Spotify Elements Found: {len(Spotify_elements)}")
        Spotify_link = Spotify_elements[0].get_attribute("href") if Spotify_elements else None
        print(f"[DEBUG] Spotify Link: {Spotify_link}")

        friends_count = 0
        try:
            friends_element = driver.find_element(By.XPATH, "//a[contains(@href, 'friends')]")
            friends_text = friends_element.get_attribute("innerText")
            friends_count = int(''.join(filter(str.isdigit, friends_text))) if friends_text else 0
        except:
            pass
        
        friends_count = 0
        try:
            friends_element = driver.find_element(By.XPATH, "//a[contains(@href, '/friends/') and (contains(normalize-space(.), 'friends') or contains(normalize-space(.), 'người bạn'))]")
            friends_text = friends_element.get_attribute("innerText")
            friends_count = int(''.join(filter(str.isdigit, friends_text))) if friends_text else 0
        except:
            pass 

        posts = driver.find_elements(By.XPATH, "//div[@role='article']")
        posts_count = len(posts)
        
        avatar_element = driver.find_elements(By.XPATH, "//img[contains(@src, 'https://')]")
        has_avatar = bool(avatar_element)
        avatar_blurry = check_blur(avatar_element[0].get_attribute("src")) if has_avatar else False
        
        has_custom_url = "profile.php?id=" not in url
        has_name_changes = "changed their name" in driver.page_source
        reported_spam = "reported this account" in driver.page_source
        flagged_by_fb = "Your account has been flagged" in driver.page_source
        
        
        
        # Khởi tạo score
        score = 0

        
        

        # Tiếp tục cộng các điểm khác (luôn chạy, nằm chung mức indent với if/else ở trên)
        score += 5 if details["Mutualfriends"] else 0
        score += 10 if details["HasStories"] else 0
        score += 5 if details["Work"] else 0
        score += 5 if details["Lives"] else 0
        score += 5 if details["Goes_to"] else 0
        score += 5 if details["Studied"] else 0
        score += 10 if details["Relationship"] else 0
        score += 5 if details["Birthday"] else 0
        score += 5 if details["Checkins"] else 0
        score += 5 if details["Followed by"] else 0
        score += 5 if details["following"] else 0
        score += 5 if details["followers"] else 0
        score += 5 if details["From"] else 0
        score += 5 if details["Manager_at"] else 0
        score += 5 if details["Joined_on"] else 0
        score += 5 if details["Chu_tich_at"] else 0
        score += 5 if details["Tông_giam_đôc_at"] else 0
        score += 20 if posts_count >= 3 else -10
        score += 5 if details["Went_to"] else 0
        score += 20 if friends_count > 100 else 0
        score += 5 if has_avatar else -10
        score += 5 if not avatar_blurry else 0
        score += 10 if details["Email_verified"] else 0
        score += 10 if details["Phone_verified"] else 0
        score += 10 if details["Instagram"] else 0
        score += 30 if has_custom_url else -20
        score += 5 if not has_name_changes else -15
        score += 5 if not reported_spam else -20
        score += 5 if not flagged_by_fb else -25
        score += 10 if github_link else 0
        score += 10 if tiktok_link else 0
        score += 10 if Vercel_link else 0
        score += 10 if PlayerDuo_link else 0
        score += 10 if Threads_link else 0
        score += 10 if Spotify_link else 0
        score += 10 if youtube_link else 0
        score += 10 if twitter_x_link else 0
        score += 10 if linktree_link else 0
        score += 10 if behance_link else 0
        score += 10 if medium_link else 0
        score += 10 if discord_link else 0
        score += 10 if telegram_link else 0
        score += 10 if reddit_link else 0
        score += 10 if soundcloud_link else 0
        


        photo_count = count_photos(driver)

        print(f"[INFO] Số ảnh: {photo_count}")
        score += 10 if photo_count >= 5 else 0
        print(f"[INFO] Account Details: {json.dumps({**{k: int(v) for k, v in details.items()}, 'name': name, 'friends': friends_count, 'posts': posts_count, 'avatar': int(has_avatar), 'blurry_avatar': int(avatar_blurry), 'score': score,**details, 'github_link': github_link}, indent=4, ensure_ascii=False)}")

        
        return {
    "url": url,
    "name": name,
    "locked_profile": False,
    "score": score
}

    except Exception as e:
        print(f"[ERROR] Failed to check {url}: {e}")
        return None
def process_accounts(input_file, output_file):
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Đăng nhập vào Facebook bằng cookie
    if not login_with_cookies(driver, "https://www.facebook.com"):
        driver.quit()
        return

    urls = read_accounts_from_excel(input_file)
    results = []

    for url in urls:
        print(f"🔍 Checking account: {url}...")
        data = check_account(driver, url)
        if data:
            results.append(data)
    
    driver.quit()

    # Lưu kết quả ra file Excel
    if results:
        df_results = pd.DataFrame(results)
        df_filtered = df_results[df_results["score"] >= 70]  # Lọc tài khoản đáng tin cậy

        if not os.path.exists(output_file):
            df_filtered.to_excel(output_file, index=False)
        else:
            existing_df = pd.read_excel(output_file)
            df_combined = pd.concat([existing_df, df_filtered], ignore_index=True).drop_duplicates()
            df_combined.to_excel(output_file, index=False)

        print(f"✅ Results saved to {output_file} - Trusted accounts: {len(df_filtered)}")

if __name__ == "__main__":
    process_accounts("testclone.xlsx", "filtered_accounts.xlsx")