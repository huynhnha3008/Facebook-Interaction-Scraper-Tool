import pandas as pd

def remove_duplicate_urls(input_file, output_file, column_name="Trùng URL"):
    # Đọc file Excel
    df = pd.read_excel(input_file)

    # Xóa dòng trùng theo cột được chỉ định
    df_unique = df.drop_duplicates(subset=[column_name], keep="first")

    # Ghi lại vào file mới (ghi đè hoặc tên khác)
    df_unique.to_excel(output_file, index=False)
    print(f"Đã lưu file không trùng vào {output_file}")

if __name__ == "__main__":
    input_path = "output1.xlsx"
    output_path = "output.xlsx"
    remove_duplicate_urls(input_path, output_path)
