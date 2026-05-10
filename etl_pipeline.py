import os
import pdfplumber
import pandas as pd
from tqdm import tqdm

def extract_pdf_tables_to_csv(base_folder, output_csv="data/data_tuyensinh.csv"):
    """
    Script quét toàn bộ thư mục chứa các file PDF Đề án tuyển sinh, 
    trích xuất dữ liệu Bảng (Table) và gộp lại thành 1 file CSV.
    """
    all_extracted_rows = []
    
    # Liệt kê tất cả các file PDF trong các thư mục con
    pdf_files = []
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))
                
    print(f"🔍 Tìm thấy {len(pdf_files)} file PDF. Bắt đầu trích xuất...")
    
    # Lặp qua từng file PDF để cào bảng
    for pdf_path in tqdm(pdf_files, desc="Đang xử lý PDF"):
        # Lấy tên trường từ tên file (Ví dụ: "1. ĐH Bách Khoa_qd-phe-duyet.pdf" -> "ĐH Bách Khoa")
        filename = os.path.basename(pdf_path)
        school_name = filename.split('_')[0] if '_' in filename else filename.replace('.pdf', '')
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Trích xuất bảng trên từng trang
                    tables = page.extract_tables()
                    for table in tables:
                        # Đi qua từng dòng trong bảng
                        for row in table:
                            # Xóa các dòng rỗng hoàn toàn nil/None/rỗng
                            cleaned_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                            if any(cleaned_row):
                                # Lưu dòng, đính kèm tên trường để dễ phân biệt
                                all_extracted_rows.append([school_name] + cleaned_row)
        except Exception as e:
            print(f"⚠️ Bỏ qua file: {filename} do lỗi: {str(e)}")

    # Ghi dữ liệu ra CSV
    if all_extracted_rows:
        # Chuyển thành DataFrame, vì format bảng mỗi PDF khác nhau 
        # nên ban đầu ta lưu dưới dạng các cột ẩn danh (Col_1, Col_2...)
        max_cols = max(len(row) for row in all_extracted_rows)
        columns = ["Tên Trường"] + [f"Col_{i}" for i in range(1, max_cols)]
        
        # Bù thêm các cột trống cho các dòng ngắn
        normalized_rows = [row + [""] * (max_cols - len(row)) for row in all_extracted_rows]
        
        df = pd.DataFrame(normalized_rows, columns=columns)
        
        # Đường dẫn output nằm trong thư mục data/
        out_path = os.path.join(os.getcwd(), output_csv)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        df.to_csv(out_path, index=False, encoding='utf-8-sig')
        print(f"✅ Đã trích xuất thành công {len(df)} dòng dữ liệu vào file: {output_csv}")
        print("💡 LƯU Ý: Vì form PDF mỗi trường là khác nhau, bạn cần dùng LLM hoặc code thêm logic để 'lược bớt' các dòng/bảng nhiễu trong file CSV này!")
    else:
        print("❌ Không tìm thấy dữ liệu bảng nào trong các file PDF.")

if __name__ == "__main__":
    # Chỉ định quét trong thư mục data chứa các file PDF đã giải nén
    data_folder = "data"
    extract_pdf_tables_to_csv(data_folder)
