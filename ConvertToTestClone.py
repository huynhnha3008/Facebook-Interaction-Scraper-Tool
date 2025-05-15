import pandas as pd

def merge_facebook_links(input_file: str, output_file: str):
    # Đọc file Excel gốc (data_scrapping)
    df = pd.read_excel(input_file)

    # Lấy dữ liệu từ hai cột react và comment, loại bỏ ô trống nếu có
    links_react = df['Link User React'].dropna()
    links_comment = df['Link User Comment'].dropna()

    # Gộp 2 cột thành 1 danh sách duy nhất
    combined_links = pd.concat([links_react, links_comment], ignore_index=True)

    # Tạo DataFrame mới có 1 cột tên là "Link User"
    result_df = pd.DataFrame({'Link User': combined_links})

    # Ghi ra file Excel mới
    result_df.to_excel(output_file, index=False)
    print(f"✅ Đã tạo file {output_file} với {len(result_df)} dòng.")

# Gọi hàm:
# merge_facebook_links("data_scrapping.xlsx", "testclone.xlsx")
if __name__ == "__main__":
    pass