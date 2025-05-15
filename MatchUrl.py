import pandas as pd

def main():
    # Đọc hai file Excel
    file_urls = "filtered_accounts.xlsx"  # File chứa cột "url"
    file_posts = "data_scrapping.xlsx"  # File chứa "Link Bài Viết", "Link User React", "Link User Comment"

    df_urls = pd.read_excel(file_urls)
    df_posts = pd.read_excel(file_posts)

    # Chuyển đổi dữ liệu thành danh sách
    url_list = df_urls["url"].astype(str).tolist()
    post_links = df_posts["Link Bài Viết"].astype(str).tolist()
    react_users = df_posts["Link User React"].astype(str).tolist()
    comment_users = df_posts["Link User Comment"].astype(str).tolist()

    # Danh sách lưu kết quả
    matched_data = []

    # Duyệt qua từng bài viết và kiểm tra URL trùng khớp
    for i in range(len(post_links)):
        react_list = str(react_users[i]).split("\n")  # Tách nhiều link trong 1 ô (nếu có)
        comment_list = str(comment_users[i]).split("\n")

        for url in url_list:
            if url in react_list or url in comment_list:
                matched_data.append([post_links[i], url])

    # Tạo DataFrame lưu kết quả
    result_df = pd.DataFrame(matched_data, columns=["Link Bài Viết", "Trùng URL"])

    # Xuất ra file Excel mới
    output_file = "matched_urls.xlsx"
    result_df.to_excel(output_file, index=False)

    print(f"Đã lưu kết quả vào {output_file}")

if __name__ == "__main__":
    main()
