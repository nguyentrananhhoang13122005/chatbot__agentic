"""
ETL Pipeline: Chuyển đổi dữ liệu DATS năm 2024 & 2025 (PDF) thành CSV
cho Recommender Agent.

Cách tiếp cận:
  1. Ưu tiên PyMuPDF (fitz) trích xuất text từ PDF text-based (nhanh)
  2. Nếu text rỗng (PDF scan) → fallback dùng EasyOCR (chậm hơn nhưng chính xác)
  3. Trích xuất tên trường từ filename
  4. Lưu thành CSV cùng schema với data_tuyensinh_2026.csv

Usage:
  python etl_pdf_to_db.py --year 2024
  python etl_pdf_to_db.py --year 2025
  python etl_pdf_to_db.py --year all
"""
import os
import re
import sys
import argparse
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ Cần cài PyMuPDF: pip install PyMuPDF")
    sys.exit(1)

# === Đường dẫn thư mục PDF ===
DATA_DIRS = {
    2024: os.path.join(
        "data",
        "2. DATS Năm 2024-20260507T080130Z-3-001-20260507T131506Z-3-001",
        "2. DATS Năm 2024-20260507T080130Z-3-001",
        "2. DATS Năm 2024"
    ),
    2025: os.path.join(
        "data",
        "1. DATS Năm 2025-20260507T075426Z-3-001-20260507T131251Z-3-001",
        "1. DATS Năm 2025-20260507T075426Z-3-001",
        "1. DATS Năm 2025"
    ),
}

OUTPUT_CSVS = {
    2024: os.path.join("data", "data_tuyensinh_2024.csv"),
    2025: os.path.join("data", "data_tuyensinh_2025_dats.csv"),
}

# === Giới hạn nội dung ===
MAX_CONTENT_CHARS = 60000  # 60K ký tự/trường (bao phủ đầy đủ cả PDF dài)
MAX_PAGES_TEXT = 50        # Tối đa 50 trang cho text extraction
MAX_PAGES_OCR = 15         # Tối đa 15 trang cho OCR (chậm hơn)


def extract_school_name(filename: str) -> str:
    """Trích xuất tên trường từ tên file PDF."""
    name = os.path.splitext(filename)[0]
    name = re.sub(r'^\d+[\.\-\s]+', '', name)
    if '_' in name:
        name = name.split('_')[0]
    name = re.sub(r'\s*\d{4}\s*$', '', name)
    name = re.sub(r'\s*-\s*$', '', name)
    return name.strip() or filename


def extract_text_pymupdf(pdf_path: str, max_pages: int = MAX_PAGES_TEXT) -> str:
    """Trích xuất text từ PDF bằng PyMuPDF (nhanh, cho PDF text-based)."""
    try:
        doc = fitz.open(pdf_path)
        pages_to_read = min(len(doc), max_pages)
        all_text = []
        for i in range(pages_to_read):
            page = doc[i]
            text = page.get_text()
            if text.strip():
                all_text.append(text.strip())
        doc.close()
        full_text = "\n\n".join(all_text)
        return full_text[:MAX_CONTENT_CHARS] if full_text else ""
    except Exception as e:
        print(f"  ⚠️ PyMuPDF error: {e}")
        return ""


def extract_text_ocr(pdf_path: str, max_pages: int = MAX_PAGES_OCR) -> str:
    """Trích xuất text từ PDF scan bằng EasyOCR (fallback)."""
    try:
        import easyocr
        import numpy as np
        reader = easyocr.Reader(['vi', 'en'], gpu=False, verbose=False)
    except ImportError:
        print("  ⚠️ EasyOCR chưa cài. Bỏ qua file scan.")
        return ""
    try:
        doc = fitz.open(pdf_path)
        pages_to_read = min(len(doc), max_pages)
        all_text = []
        for i in range(pages_to_read):
            page = doc[i]
            pix = page.get_pixmap(dpi=150)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            if img.shape[2] == 4:
                import cv2
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
            results = reader.readtext(img)
            page_text = " ".join([text for _, text, _ in results])
            if page_text.strip():
                all_text.append(page_text.strip())
        doc.close()
        full_text = "\n\n".join(all_text)
        return full_text[:MAX_CONTENT_CHARS] if full_text else ""
    except Exception as e:
        print(f"  ⚠️ OCR error: {e}")
        return ""


def process_pdf(pdf_path: str, filename: str, year: int) -> dict:
    """Xử lý 1 file PDF: text extraction → OCR fallback → metadata."""
    school_name = extract_school_name(filename)
    content = extract_text_pymupdf(pdf_path)
    if len(content) < 50:
        print(f"  📸 PDF scan → đang OCR...")
        content = extract_text_ocr(pdf_path)
    if not content or len(content) < 30:
        return None
    return {
        "Trường": school_name,
        "Năm": year,
        "Mã văn bản": "",
        "Ngày ban hành": "",
        "File gốc": filename,
        "Nội dung": content,
    }


def run_etl(year: int):
    """Chạy ETL cho 1 năm cụ thể."""
    data_dir = DATA_DIRS.get(year)
    output_csv = OUTPUT_CSVS.get(year)
    if not data_dir or not output_csv:
        print(f"❌ Chưa cấu hình cho năm {year}")
        return
    print(f"\n{'=' * 60}")
    print(f"📋 ETL Pipeline: DATS năm {year}")
    print(f"{'=' * 60}")
    if not os.path.isdir(data_dir):
        print(f"❌ Không tìm thấy thư mục: {data_dir}")
        return
    pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.pdf')]
    print(f"📁 Tìm thấy {len(pdf_files)} file PDF")
    records = []
    skipped = 0
    for i, f in enumerate(sorted(pdf_files)):
        pdf_path = os.path.join(data_dir, f)
        school_name = extract_school_name(f)
        print(f"  [{i+1}/{len(pdf_files)}] {school_name}...", end=" ")
        result = process_pdf(pdf_path, f, year)
        if result:
            records.append(result)
            print(f"✅ ({len(result['Nội dung'])} chars)")
        else:
            skipped += 1
            print(f"⏭️ SKIP (không trích được text)")
    if records:
        df = pd.DataFrame(records)
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        print(f"\n{'=' * 60}")
        print(f"✅ Hoàn thành ETL năm {year}!")
        print(f"  📊 Thành công: {len(records)} trường | Bỏ qua: {skipped}")
        print(f"  💾 Lưu tại: {output_csv}")
        print(f"  📏 Kích thước: {os.path.getsize(output_csv) / 1024:.0f} KB")
    else:
        print(f"\n❌ Không trích được dữ liệu nào cho năm {year}")


def main():
    parser = argparse.ArgumentParser(description="ETL DATS PDF → CSV")
    parser.add_argument("--year", type=str, default="all",
                        help="Năm cần ETL: 2024, 2025, hoặc all")
    parser.add_argument("--no-ocr", action="store_true",
                        help="Bỏ qua OCR, chỉ dùng PyMuPDF")
    args = parser.parse_args()
    if args.no_ocr:
        global extract_text_ocr
        extract_text_ocr = lambda *a, **kw: ""
        print("⚡ Chế độ nhanh: Bỏ qua OCR cho PDF scan")
    if args.year == "all":
        for y in [2024, 2025]:
            run_etl(y)
    else:
        run_etl(int(args.year))


if __name__ == "__main__":
    main()
