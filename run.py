import time
import os

import Crawl_post
import Crawl_link_post
import Crawl
import ConvertToTestClone
import CheckClone
import MatchUrl
import classify
import CheckDuplicate

def method_1():
    # Cào theo cách 1: Crawl_post + Crawl_link_post
    Crawl_post.main()
    print("Đã lấy xong link các bài post")
    time.sleep(30)

    Crawl_link_post.main()
    print("Đã lấy xong dữ liệu")
    time.sleep(30)

    ConvertToTestClone.merge_facebook_links("data_scrapping.xlsx", "testclone.xlsx")
    print("Đã đưa vào danh sách test clone")
    time.sleep(30)

    CheckClone.process_accounts("testclone.xlsx", "filtered_accounts.xlsx")
    print("Đã check xong nhưng acc clone và loại chúng")
    time.sleep(30)

    MatchUrl.main()
    print("Đã lấy xong đường link bài viết")
    time.sleep(30)

    classify.classify_accounts("matched_urls.xlsx", "facebook_test.json")
    print("Đã phân loại xong người mua và bán")
    time.sleep(15)

    CheckDuplicate.remove_duplicate_urls("output1.xlsx","output.xlsx")

    files_to_delete = [
        "data_scrapping.xlsx",
        "testclone.xlsx",
        "filtered_accounts.xlsx",
        "matched_urls.xlsx",
        "post_scrapping.xlsx",
        "output1.xlsx"
    ]

    clean_up(files_to_delete)

def method_2():
    # Cào theo cách 2: chỉ dùng Crawl
    Crawl.main()
    print("Đã lấy xong dữ liệu")
    time.sleep(30)

    ConvertToTestClone.merge_facebook_links("data_scrapping.xlsx", "testclone.xlsx")
    print("Đã đưa vào danh sách test clone")
    time.sleep(30)

    CheckClone.process_accounts("testclone.xlsx", "filtered_accounts.xlsx")
    print("Đã check xong nhưng acc clone và loại chúng")
    time.sleep(30)

    MatchUrl.main()
    print("Đã lấy xong đường link bài viết")
    time.sleep(30)

    classify.classify_accounts("matched_urls.xlsx", "facebook_test.json")
    print("Đã phân loại xong người mua và bán")

    CheckDuplicate.remove_duplicate_urls("output1.xlsx","output.xlsx")

    files_to_delete = [
        "data_scrapping.xlsx",
        "testclone.xlsx",
        "filtered_accounts.xlsx",
        "matched_urls.xlsx",
        "output1.xlsx"
    ]

    clean_up(files_to_delete)

def clean_up(files):
    for file_path in files:
        try:
            os.remove(file_path)
            # print(f"Đã xóa file: {file_path}")
        except FileNotFoundError:
            print(f"[WARNING] Không tìm thấy file để xóa: {file_path}")
        except Exception as e:
            print(f"[ERROR] Lỗi khi xóa file {file_path}: {e}")
    print("Kết thúc quy trình")

if __name__ == "__main__":
    print("Chọn phương thức cào:")
    print("1. Cào bằng link group")
    print("2. Cào bằng link quảng cáo")

    choice = input("Nhập 1 hoặc 2: ").strip()

    if choice == "1":
        method_1()
    elif choice == "2":
        method_2()
    else:
        print("Lựa chọn không hợp lệ. Kết thúc chương trình.")
