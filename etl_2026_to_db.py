"""
ETL Pipeline: Chuyển đổi dữ liệu DATS năm 2026 (file .md.txt) thành cơ sở tri thức 
cho Recommender Agent. 

Dữ liệu 2026 là dạng text phi cấu trúc (thông tin tuyển sinh, phương thức, ngành, 
chỉ tiêu, điều kiện) — khác với dữ liệu 2025 (điểm chuẩn dạng XLSX có cấu trúc).

Cách tiếp cận: Đọc toàn bộ file .md.txt → trích xuất metadata + nội dung → 
lưu thành 1 file CSV tổng hợp (school_name, year, file_path, content_summary, full_content).
Agent sẽ dùng LLM để truy vấn trên content khi cần.
"""
import os
import re
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

# === Đường dẫn ===
DATA_DIR_2026 = os.path.join("data", "5. DATTS năm 2026 chuyển đổi-20260507T080527Z-3-001", "5. DATTS năm 2026 chuyển đổi")
OUTPUT_CSV = os.path.join("data", "data_tuyensinh_2026.csv")

# === Bảng mã trường → tên đầy đủ ===
SCHOOL_CODE_MAP = {
    "BKA": "Đại học Bách khoa Hà Nội",
    "BVH": "Học viện Công nghệ Bưu chính Viễn thông",
    "BPH": "Học Viện Biên Phòng",
    "DBG": "Đại học Nông Lâm Bắc Giang",
    "DCH": "Trường Sĩ Quan Đặc Công",
    "DCN": "Đại Học Công Nghiệp Hà Nội",
    "DCQ": "Đại Học Công Nghệ và Quản Lý Hữu Nghị",
    "DCV": "Đại học Công nghiệp Vinh",
    "DDF": "Đại Học Ngoại Ngữ - Đại Học Đà Nẵng",
    "DDL": "Đại Học Điện Lực",
    "DDQ": "Đại Học Kinh Tế - Đại Học Đà Nẵng",
    "DDS": "Đại Học Sư Phạm - Đại Học Đà Nẵng",
    "DDT": "Đại Học Duy Tân",
    "DFA": "Đại học Tài chính Quản trị kinh doanh",
    "DHY": "Đại Học Y Dược - Đại Học Huế",
    "DKH": "Đại Học Dược Hà Nội",
    "DKS": "Đại học Kiểm Sát Hà Nội",
    "DKY": "Đại Học Kỹ Thuật Y Tế Hải Dương",
    "DLX": "Đại Học Lao Động - Xã Hội (Cơ sở Hà Nội)",
    "DMT": "Đại học Tài Nguyên và Môi Trường Hà Nội",
    "DSK": "Trường Đại học sư phạm kỹ thuật - Đại học Đà Nẵng",
    "DTC": "Đại học CNTT&TT - Đại học Thái Nguyên",
    "DTE": "Đại học Kinh tế Quản trị kinh doanh - Đại học Thái Nguyên",
    "DYH": "Học Viện Quân Y - Hệ Dân sự",
    "ETU": "Đại Học Hòa Bình",
    "GHA": "Đại Học Giao Thông Vận Tải (Cơ sở Phía Bắc)",
    "GNT": "Đại Học Sư Phạm Nghệ Thuật Trung Ương",
    "GTA": "Đại học Công nghệ Giao thông vận tải",
    "HBT": "Học viện Báo chí và Tuyên truyền",
    "HCP": "Học Viện Chính Sách và Phát Triển",
    "HGH": "Trường Sĩ Quan Phòng Hóa",
    "HHA": "Đại Học Hàng Hải Việt Nam",
    "HHT": "Đại Học Hà Tĩnh",
    "HLU": "Đại Học Hạ Long",
    "HNM": "Đại học Thủ đô Hà Nội",
    "HPN": "Học Viện Phụ Nữ Việt Nam",
    "HTC": "Học Viện Tài Chính",
    "HTN": "Học Viện Thanh Thiếu Niên Việt Nam",
    "HVA": "Học Viện Âm Nhạc Huế",
    "HVD": "Học Viện Dân Tộc",
    "HVN": "Học Viện Nông Nghiệp Việt Nam",
    "HVQ": "Học Viện Quản Lý Giáo Dục",
    "KCN": "Đại Học Khoa Học Và Công Nghệ Hà Nội",
    "KHA": "Đại Học Kinh Tế Quốc Dân",
    "KMA": "Học Viện Kỹ Thuật Mật Mã",
    "LDA": "Đại Học Công Đoàn",
    "LNH": "Đại Học Lâm nghiệp",
    "MHN": "Đại Học Mở Hà Nội",
    "NHF": "Đại Học Hà Nội",
    "NHH": "Học Viện Ngân Hàng",
    "NTH": "Đại học Ngoại thương (Cơ sở phía Bắc)",
    "NTU": "Đại Học Nguyễn Trãi",
    "PKA": "Đại Học Phenikaa",
    "PKH": "Học Viện Phòng Không - Không Quân",
    "QHD": "Trường Quản Trị và Kinh Doanh - ĐH Quốc gia Hà Nội",
    "QHE": "Đại Học Kinh Tế - Đại Học Quốc Gia Hà Nội",
    "QHF": "Đại Học Ngoại Ngữ - Đại Học Quốc Gia Hà Nội",
    "QHI": "Đại Học Công Nghệ - Đại Học Quốc Gia Hà Nội",
    "QHK": "Trường Khoa học liên ngành và Nghệ thuật - ĐHQG Hà Nội",
    "QHL": "Đại học Luật - Đại Học Quốc Gia Hà Nội",
    "QHT": "Đại Học Khoa Học Tự Nhiên - Đại Học Quốc Gia Hà Nội",
    "QHX": "Đại Học Khoa Học Xã Hội và Nhân Văn - ĐHQG Hà Nội",
    "SDU": "Đại học Sao Đỏ",
    "SP2": "Đại Học Sư Phạm Hà Nội 2",
    "SPH": "Đại Học Sư Phạm Hà Nội",
    "TDB": "Đại Học Thể Dục Thể Thao Bắc Ninh",
    "TDD": "Đại học Thành Đô",
    "TGH": "Trường Sĩ Quan Tăng - Thiết Giáp",
    "THU": "Đại học Y khoa Tokyo Việt Nam",
    "THV": "Đại Học Hùng Vương",
    "TLA": "Đại Học Thủy Lợi (Cơ sở 1)",
    "TMU": "Đại Học Thương Mại",
    "TQU": "Đại học Tân Trào",
    "TSN": "Đại Học Nha Trang",
    "TTB": "Đại Học Tây Bắc",
    "TTD": "Đại Học Thể Dục Thể Thao Đà Nẵng",
    "TTH": "Trường Sĩ Quan Thông Tin - Đại Học Thông Tin Liên Lạc",
    "UFA": "Đại học Tài Chính Kế Toán",
    "UKH": "Đại học Khánh Hòa",
    "VHD": "Đại Học Công Nghiệp Việt Hung",
    "VJU": "Đại học Việt Nhật - ĐHQG Hà Nội",
    "VKU": "Đại học CNTT và Truyền thông Việt Hàn - ĐH Đà Nẵng",
    "XDA": "Đại Học Xây Dựng Hà Nội",
    "YHB": "Đại Học Y Hà Nội",
    "YQH": "Học Viện Quân Y - Hệ Quân sự",
    "YTC": "Đại Học Y Tế Công Cộng",
}


def extract_school_name_from_filename(filename: str) -> str:
    """Trích xuất tên trường từ tên file, ưu tiên bảng mapping, fallback regex."""
    # Thử match code
    code_match = re.match(r'\d+\.?\s*([A-Z]{2,5})[_\-]', filename)
    if code_match:
        code = code_match.group(1)
        if code in SCHOOL_CODE_MAP:
            return SCHOOL_CODE_MAP[code]
    
    # Fallback: lấy phần sau code
    name_match = re.match(r'\d+\.?\s*[A-Z]{2,5}[_\-](.+?)\.md\.txt$', filename)
    if name_match:
        raw_name = name_match.group(1)
        # Clean up
        raw_name = raw_name.replace('_', ' ').replace('-', ' ')
        raw_name = re.sub(r'(Thong tin tuyen sinh|DATS|nam 2026|final|md|txt)', '', raw_name, flags=re.IGNORECASE)
        raw_name = raw_name.strip(' -_.')
        return raw_name if raw_name else filename
    
    return filename


def process_file(filepath: str, filename: str) -> dict:
    """Đọc 1 file .md.txt và trích xuất metadata + nội dung."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  ⚠️ Lỗi đọc {filename}: {e}")
        return None
    
    school_name = extract_school_name_from_filename(filename)
    
    # Trích xuất metadata từ header YAML
    doc_id = ""
    date = ""
    
    id_match = re.search(r'doc_id\s*:\s*(.+)', content)
    if id_match:
        doc_id = id_match.group(1).strip()
    
    date_match = re.search(r'date\s*:\s*(.+)', content)
    if date_match:
        date = date_match.group(1).strip()
    
    # Giới hạn content để tránh quá lớn (giữ 8000 ký tự đầu)
    content_trimmed = content[:8000]
    
    return {
        "Trường": school_name,
        "Năm": 2026,
        "Mã văn bản": doc_id,
        "Ngày ban hành": date,
        "File gốc": filename,
        "Nội dung": content_trimmed,
    }


def main():
    print("=" * 60)
    print("📋 ETL Pipeline: Dữ liệu tuyển sinh năm 2026")
    print("=" * 60)
    
    if not os.path.isdir(DATA_DIR_2026):
        print(f"❌ Không tìm thấy thư mục: {DATA_DIR_2026}")
        return
    
    files = [f for f in os.listdir(DATA_DIR_2026) if f.endswith('.md.txt') or f.endswith('.txt')]
    print(f"📁 Tìm thấy {len(files)} file")
    
    records = []
    errors = 0
    
    for f in sorted(files):
        filepath = os.path.join(DATA_DIR_2026, f)
        result = process_file(filepath, f)
        if result:
            records.append(result)
            print(f"  ✅ {result['Trường']}")
        else:
            errors += 1
    
    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    print(f"\n{'=' * 60}")
    print(f"✅ Hoàn thành!")
    print(f"  📊 Tổng: {len(records)} trường | Lỗi: {errors}")
    print(f"  💾 Lưu tại: {OUTPUT_CSV}")
    print(f"  📏 Kích thước: {os.path.getsize(OUTPUT_CSV) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
