"""
ETL Pipeline: Chuyển đổi dữ liệu DATS năm 2024 & 2025 (PDF/DOCX) thành CSV
cho Recommender Agent.

Cách tiếp cận:
  1. Ưu tiên PyMuPDF (fitz) trích xuất text từ PDF text-based (nhanh)
  2. PDF scan (không có lớp text) mặc định BỊ BỎ QUA và được liệt kê trong báo cáo; OCR chỉ chạy khi thêm --ocr
     (Tesseract qua PyMuPDF, dự phòng EasyOCR)
  3. File .docx đọc bằng python-docx (đoạn văn + bảng)
  4. Trích xuất & chuẩn hoá tên trường từ filename
  5. Lưu thành CSV cùng schema với data_tuyensinh_2026.csv và cập nhật các dòng của năm đó trong master
  6. Ghi báo cáo data/dats_etl_report.json (file scan / ít chữ / trùng trường) để người phụ trách rà soát

KHÔNG còn cắt nội dung: bản cũ cắt 60.000 ký tự/50 trang nên nhiều văn bản mất phần cuối (chỉ tiêu, học phí...).
Recommender đã chunk theo câu hỏi lúc truy vấn nên lưu đầy đủ không làm phình context LLM.
Có thể giới hạn bằng biến môi trường DATS_MAX_CHARS / DATS_MAX_PAGES (0 = không giới hạn).

Usage:
  python etl_pdf_to_db.py --year 2024
  python etl_pdf_to_db.py --year 2025
  python etl_pdf_to_db.py --year all
  python etl_pdf_to_db.py --year 2025 --src "D:/pdfs/2025"
"""
import os
import re
import sys
import json
import argparse
import unicodedata
import pandas as pd

# === Đường dẫn thư mục nguồn (PDF/DOCX). Mặc định: data/_dats_src/<năm>; vẫn hỗ trợ đường dẫn cũ nếu còn ===
DATA_DIRS = {
    2024: [
        os.path.join("data", "_dats_src", "2024"),
        os.path.join("data", "2. DATS Năm 2024-20260507T080130Z-3-001", "2. DATS Năm 2024"),
    ],
    2025: [
        os.path.join("data", "_dats_src", "2025"),
        os.path.join("data", "1. DATS Năm 2025-20260507T075426Z-3-001", "1. DATS Năm 2025"),
    ],
}

OUTPUT_CSVS = {
    2024: os.path.join("data", "data_tuyensinh_2024.csv"),
    2025: os.path.join("data", "data_tuyensinh_2025_dats.csv"),
}
MASTER_CSV = os.path.join("data", "data_tuyensinh_master.csv")
REPORT_JSON = os.path.join("data", "dats_etl_report.json")

# === Giới hạn (0 = không giới hạn) ===
MAX_CONTENT_CHARS = int(os.getenv("DATS_MAX_CHARS", "0"))
MAX_PAGES_TEXT = int(os.getenv("DATS_MAX_PAGES", "0"))
MAX_PAGES_OCR = 15         # OCR chậm nên vẫn giới hạn 15 trang
LOW_TEXT_CHARS_PER_PAGE = 300  # dưới ngưỡng này nhiều khả năng là PDF scan / bảng dạng ảnh

_ABBREVIATIONS = [
    (r"(?<!\w)(?:đh|dh)(?!\w)", "Đại học"),
    (r"(?<!\w)hv(?!\w)", "Học viện"),
    (r"(?<!\w)cđ(?!\w)", "Cao đẳng"),
]


def extract_school_name(filename: str) -> str:
    """Trích xuất & chuẩn hoá tên trường từ tên file.

    Ví dụ: "221. DH công nghệ - ĐH Quốc gia 2025-QHI.pdf" → "Đại học công nghệ - Đại học Quốc gia".
    Chuẩn hoá để cùng một trường ở các năm khác nhau có tên giống nhau (matcher dựa vào tên).
    """
    name = os.path.splitext(filename)[0]
    name = unicodedata.normalize("NFC", name)
    name = re.sub(r"^\d+[\.\-\s]+", "", name)            # số thứ tự đầu file
    if "_" in name:
        name = name.split("_")[0]                         # phần sau "_" thường là tên văn bản gốc
    name = re.sub(r"\(\s*\d{4}\s*\)", " ", name)          # (2025)
    name = re.sub(r"(?<!\d)(?:19|20)\d{2}(?!\d)(?:\.\d+)*", " ", name)  # năm đứng lẻ/dính chữ: 2024, mã2024, 2025.07.07
    name = re.sub(r"[-–]\s*[A-Z]{2,4}\s*$", "", name)     # mã trường cuối tên: "-QHI"
    for pattern, repl in _ABBREVIATIONS:
        name = re.sub(pattern, repl, name, flags=re.IGNORECASE)
    name = re.sub(r"\s*[-–]\s*$", "", name)
    name = re.sub(r"\s+", " ", name).strip(" -–._")
    return name or filename


def _read_limit(value: int, default_none=None):
    return value if value and value > 0 else default_none


def extract_text_pymupdf(pdf_path: str, max_pages: int = MAX_PAGES_TEXT):
    """Trích xuất text từ PDF bằng PyMuPDF. Trả về (text, số_trang)."""
    import fitz  # PyMuPDF (import lười để module vẫn import được khi chưa cài, vd. trong test)
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        pages_to_read = min(total_pages, _read_limit(max_pages, total_pages))
        all_text = []
        for i in range(pages_to_read):
            text = doc[i].get_text()
            if text.strip():
                all_text.append(text.strip())
        doc.close()
        full_text = "\n\n".join(all_text)
        if MAX_CONTENT_CHARS:
            full_text = full_text[:MAX_CONTENT_CHARS]
        return full_text, total_pages
    except Exception as e:
        print(f"  ⚠️ PyMuPDF error: {e}")
        return "", 0


def extract_text_docx(docx_path: str):
    """Đọc .docx: đoạn văn + bảng (bảng là nơi thường chứa chỉ tiêu/tổ hợp). Trả về (text, 0)."""
    try:
        import docx
        document = docx.Document(docx_path)
        parts = [p.text.strip() for p in document.paragraphs if p.text.strip()]
        for table in document.tables:
            for row in table.rows:
                cells = []
                for cell in row.cells:
                    text = cell.text.strip().replace("\n", " ")
                    if text and (not cells or cells[-1] != text):  # ô gộp bị lặp lại → bỏ
                        cells.append(text)
                if cells:
                    parts.append(" | ".join(cells))
        full_text = "\n".join(parts)
        if MAX_CONTENT_CHARS:
            full_text = full_text[:MAX_CONTENT_CHARS]
        return full_text, 0
    except Exception as e:
        print(f"  ⚠️ DOCX error: {e}")
        return "", 0


OCR_MAX_PAGES = int(os.getenv("DATS_OCR_MAX_PAGES", "40"))
OCR_WORKERS = int(os.getenv("DATS_OCR_WORKERS", str(min(8, os.cpu_count() or 2))))


def _ocr_tesseract(pdf_path: str, max_pages: int) -> str:
    """OCR bằng Tesseract (qua PyMuPDF). Cần cài tesseract-ocr + tesseract-ocr-vie; ném lỗi nếu thiếu."""
    import fitz
    doc = fitz.open(pdf_path)
    try:
        parts = []
        for i in range(min(len(doc), max_pages)):
            page = doc[i]
            textpage = page.get_textpage_ocr(language="vie+eng", dpi=150, full=True)
            text = page.get_text(textpage=textpage).strip()
            if text:
                parts.append(text)
        return "\n\n".join(parts)
    finally:
        doc.close()


def _ocr_easyocr(pdf_path: str, max_pages: int) -> str:
    """OCR bằng EasyOCR (dự phòng, rất chậm trên CPU)."""
    try:
        import easyocr
        import numpy as np
        import fitz
        reader = easyocr.Reader(['vi', 'en'], gpu=False, verbose=False)
    except ImportError:
        print("  ⚠️ Không có Tesseract lẫn EasyOCR. Bỏ qua file scan.")
        return ""
    doc = fitz.open(pdf_path)
    all_text = []
    for i in range(min(len(doc), max_pages)):
        pix = doc[i].get_pixmap(dpi=150)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        if img.shape[2] == 4:
            import cv2
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        results = reader.readtext(img)
        page_text = " ".join([text for _, text, _ in results])
        if page_text.strip():
            all_text.append(page_text.strip())
    doc.close()
    return "\n\n".join(all_text)


def extract_text_ocr(pdf_path: str, max_pages: int = OCR_MAX_PAGES) -> str:
    """Trích xuất text từ PDF scan: Tesseract trước, EasyOCR làm dự phòng."""
    try:
        full_text = _ocr_tesseract(pdf_path, max_pages)
    except Exception as e:
        print(f"  ⚠️ Tesseract không dùng được ({e}); thử EasyOCR")
        try:
            full_text = _ocr_easyocr(pdf_path, min(max_pages, MAX_PAGES_OCR))
        except Exception as e2:
            print(f"  ⚠️ OCR error: {e2}")
            return ""
    return full_text[:MAX_CONTENT_CHARS] if (full_text and MAX_CONTENT_CHARS) else full_text


def _text_layer(path: str, filename: str):
    """Lớp text sẵn có (nhanh). Trả về (content, pages, method). PDF scan → content rỗng, method='text'."""
    if filename.lower().endswith(".docx"):
        content, pages = extract_text_docx(path)
        return content, pages, "docx"
    content, pages = extract_text_pymupdf(path)
    return content, pages, "text"


def _make_record(filename: str, year: int, content: str, pages: int, method: str):
    if not content or len(content) < 30:
        return None
    low_text = pages > 0 and len(content) / pages < LOW_TEXT_CHARS_PER_PAGE
    return {
        "Trường": extract_school_name(filename),
        "Năm": year,
        "Mã văn bản": "",
        "Ngày ban hành": "",
        "File gốc": filename,
        "Nội dung": content,
        "_meta": {"pages": pages, "method": method, "low_text": low_text},
    }


def process_file(path: str, filename: str, year: int) -> dict:
    """Xử lý 1 file tuần tự: text extraction → OCR fallback → metadata. Trả về dict hoặc None."""
    content, pages, method = _text_layer(path, filename)
    if len(content) < 50 and not filename.lower().endswith(".docx"):
        print("  📸 PDF scan → đang OCR...")
        content = extract_text_ocr(path)
        method = "ocr"
    return _make_record(filename, year, content, pages, method)


def _ocr_job(args):
    """Worker song song cho OCR (top-level để multiprocessing pickle được)."""
    os.environ["OMP_THREAD_LIMIT"] = "1"  # mỗi tiến trình 1 luồng Tesseract, song song ở mức file
    path, filename = args
    return filename, extract_text_ocr(path)


def merge_same_school(records: list) -> tuple:
    """Cùng một trường + năm có nhiều file → gộp nội dung (tránh recommender chỉ đọc dòng đầu). Trả về (records, danh_sách_gộp)."""
    merged: dict = {}
    notes = []
    for rec in records:
        key = (rec["Trường"].casefold(), rec["Năm"])
        if key not in merged:
            merged[key] = dict(rec)
            continue
        base = merged[key]
        notes.append({"school": rec["Trường"], "files": [base["File gốc"], rec["File gốc"]]})
        base["Nội dung"] += f"\n\n===== {rec['File gốc']} =====\n\n" + rec["Nội dung"]
        base["File gốc"] += " + " + rec["File gốc"]
    return list(merged.values()), notes


def resolve_data_dir(year: int, override: str = ""):
    candidates = [override] if override else DATA_DIRS.get(year, [])
    for candidate in candidates:
        if candidate and os.path.isdir(candidate):
            return candidate
    return None


def update_master(df: pd.DataFrame, year: int) -> None:
    """Thay các dòng của `year` trong master bằng dữ liệu mới (giữ nguyên các năm khác)."""
    if not os.path.exists(MASTER_CSV):
        return
    master = pd.read_csv(MASTER_CSV)
    master = master[master["Năm"] != year]
    master = pd.concat([master, df], ignore_index=True)
    master.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
    print(f"  ✅ Đã cập nhật {len(df)} dòng {year} trong {MASTER_CSV} (tổng {len(master)})")


def run_etl(year: int, src: str = "") -> dict:
    """Chạy ETL cho 1 năm cụ thể. Trả về báo cáo."""
    output_csv = OUTPUT_CSVS.get(year)
    if not output_csv:
        print(f"❌ Chưa cấu hình cho năm {year}")
        return {}
    data_dir = resolve_data_dir(year, src)
    print(f"\n{'=' * 60}")
    print(f"📋 ETL Pipeline: DATS năm {year}")
    print(f"{'=' * 60}")
    if not data_dir:
        print(f"❌ Không tìm thấy thư mục nguồn cho năm {year}")
        return {}
    files = [f for f in os.listdir(data_dir) if f.lower().endswith((".pdf", ".docx"))]
    print(f"📁 {data_dir}: {len(files)} file")
    records, skipped, pending_ocr = [], [], []
    # Pha 1: lớp text sẵn có (nhanh). File không có text → xếp hàng OCR.
    for i, f in enumerate(sorted(files)):
        path = os.path.join(data_dir, f)
        content, pages, method = _text_layer(path, f)
        if len(content) < 50 and not f.lower().endswith(".docx"):
            pending_ocr.append((path, f, pages))
            print(f"  [{i+1}/{len(files)}] {extract_school_name(f)} 📸 scan → xếp hàng OCR")
            continue
        result = _make_record(f, year, content, pages, method)
        if result:
            records.append(result)
            flag = " ⚠️ ít chữ (nghi scan)" if result["_meta"]["low_text"] else ""
            print(f"  [{i+1}/{len(files)}] {extract_school_name(f)} ✅ ({len(content)} chars){flag}")
        else:
            skipped.append(f)
            print(f"  [{i+1}/{len(files)}] {extract_school_name(f)} ⏭️ SKIP (không trích được text)")
    # Pha 2: OCR song song cho các file scan
    if pending_ocr and os.getenv("DATS_NO_OCR") == "1":
        skipped.extend(f for _, f, _ in pending_ocr)
        pending_ocr = []
    if pending_ocr:
        print(f"\n📸 OCR {len(pending_ocr)} file scan (tối đa {OCR_MAX_PAGES} trang/file, {OCR_WORKERS} tiến trình)...")
        pages_by_file = {f: p for _, f, p in pending_ocr}
        import multiprocessing as mp
        done = 0
        with mp.get_context("spawn").Pool(processes=OCR_WORKERS) as pool:
            for filename, text in pool.imap_unordered(_ocr_job, [(p, f) for p, f, _ in pending_ocr]):
                done += 1
                result = _make_record(filename, year, text, pages_by_file.get(filename, 0), "ocr")
                if result:
                    records.append(result)
                    print(f"  OCR [{done}/{len(pending_ocr)}] {extract_school_name(filename)} ✅ ({len(text)} chars)", flush=True)
                else:
                    skipped.append(filename)
                    print(f"  OCR [{done}/{len(pending_ocr)}] {extract_school_name(filename)} ⏭️ SKIP", flush=True)
    records.sort(key=lambda r: r["File gốc"])
    report = {"year": year, "source_dir": data_dir, "files": len(files), "skipped": skipped}
    if not records:
        print(f"\n❌ Không trích được dữ liệu nào cho năm {year}")
        return report
    report["low_text_files"] = [r["File gốc"] for r in records if r["_meta"]["low_text"]]
    report["ocr_files"] = [r["File gốc"] for r in records if r["_meta"]["method"] == "ocr"]
    merged, merge_notes = merge_same_school(records)
    report["merged_duplicates"] = merge_notes
    df = pd.DataFrame([{k: v for k, v in r.items() if k != "_meta"} for r in merged])
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    report.update({"schools": len(df), "avg_chars": int(df["Nội dung"].str.len().mean()),
                   "max_chars": int(df["Nội dung"].str.len().max())})
    print(f"\n{'=' * 60}")
    print(f"✅ Hoàn thành ETL năm {year}!")
    print(f"  📊 Thành công: {len(df)} trường | Bỏ qua: {len(skipped)} | Nghi scan: {len(report['low_text_files'])}")
    print(f"  💾 Lưu tại: {output_csv} ({os.path.getsize(output_csv) / 1024:.0f} KB)")
    update_master(df, year)
    return report


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description="ETL DATS PDF/DOCX → CSV")
    parser.add_argument("--year", type=str, default="all",
                        help="Năm cần ETL: 2024, 2025, hoặc all")
    parser.add_argument("--src", type=str, default="",
                        help="Thư mục chứa PDF/DOCX (ghi đè đường dẫn mặc định; chỉ dùng khi --year là một năm cụ thể)")
    parser.add_argument("--ocr", action="store_true",
                        help="Bật OCR cho PDF scan (mặc định TẮT: dự án không dùng OCR; file scan sẽ được liệt kê trong báo cáo)")
    args = parser.parse_args()
    if not args.ocr:
        os.environ["DATS_NO_OCR"] = "1"
        print("⚡ Bỏ qua PDF scan (không OCR). Dùng --ocr nếu muốn đọc cả file scan.")
    years = [2024, 2025] if args.year == "all" else [int(args.year)]
    reports = [run_etl(y, args.src if len(years) == 1 else "") for y in years]
    with open(REPORT_JSON, "w", encoding="utf-8") as fh:
        json.dump(reports, fh, ensure_ascii=False, indent=2)
    print(f"\n📝 Báo cáo: {REPORT_JSON}")


if __name__ == "__main__":
    main()
