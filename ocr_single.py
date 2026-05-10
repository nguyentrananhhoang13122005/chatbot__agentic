import sys
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
import os
import fitz
import easyocr
import pandas as pd
import numpy as np
import cv2

print("Loading EasyOCR...")
reader = easyocr.Reader(['vi', 'en'], gpu=False)

def process_image(img):
    results = reader.readtext(img)
    if not results: return []
    lines = [{'y': (b[0][1] + b[2][1])/2, 'x': (b[0][0] + b[1][0])/2, 'text': t} for b, t, p in results]
    lines.sort(key=lambda item: item['y'])
    
    rows = []
    current_row = []
    current_y = None
    tolerance = 15
    for item in lines:
        if current_y is None:
            current_row.append(item)
            current_y = item['y']
        elif abs(item['y'] - current_y) <= tolerance:
            current_row.append(item)
            current_y = sum(i['y'] for i in current_row) / len(current_row)
        else:
            current_row.sort(key=lambda i: i['x'])
            rows.append(" | ".join([i['text'] for i in current_row]))
            current_row = [item]
            current_y = item['y']
    if current_row:
        current_row.sort(key=lambda i: i['x'])
        rows.append(" | ".join([i['text'] for i in current_row]))
    return rows

pdf_path = r'data\DATS_2025\1. DATS Năm 2025\3. HV Bưu chính VT_Thong-tin-tuyen-sinh-DHCQ-nam-2025-1.pdf'
school_name = "3. HV Bưu chính VT"
output_csv = 'data/data_tuyensinh.csv'

print(f"Processing: {pdf_path}")
doc = fitz.open(pdf_path)
new_rows = []
for page_num in range(len(doc)):
    print(f"  Page {page_num + 1}/{len(doc)}...")
    page = doc.load_page(page_num)
    pix = page.get_pixmap(dpi=150)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    if img.shape[2] == 4: img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
    
    page_lines = process_image(img)
    for line in page_lines:
        new_rows.append([school_name, line])

if new_rows:
    df_existing = pd.read_csv(output_csv, low_memory=False)
    max_cols = len(df_existing.columns)
    padded_rows = [r + [""] * (max_cols - len(r)) for r in new_rows]
    df_new = pd.DataFrame(padded_rows, columns=df_existing.columns)
    df_new.to_csv(output_csv, mode='a', header=False, index=False, encoding='utf-8-sig')
    print(f"Added {len(new_rows)} rows for PTIT.")
else:
    print("No data extracted.")
