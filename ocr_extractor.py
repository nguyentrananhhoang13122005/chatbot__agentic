import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import fitz
import easyocr
import pandas as pd
import numpy as np
import cv2
import time

print("Initializing OCR (this may take a moment)...")
reader = easyocr.Reader(['vi', 'en'], gpu=False)

def process_image(img):
    # Run OCR
    results = reader.readtext(img)
    if not results:
        return []
    
    # Group by Y coordinate to form rows
    # results format: (bbox, text, prob)
    # bbox: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
    
    lines = []
    for bbox, text, prob in results:
        y_center = (bbox[0][1] + bbox[2][1]) / 2
        x_center = (bbox[0][0] + bbox[1][0]) / 2
        lines.append({
            'y': y_center,
            'x': x_center,
            'text': text
        })
    
    # Sort by Y
    lines.sort(key=lambda item: item['y'])
    
    # Group into rows with a tolerance
    rows = []
    current_row = []
    current_y = None
    tolerance = 15  # pixels
    
    for item in lines:
        if current_y is None:
            current_row.append(item)
            current_y = item['y']
        elif abs(item['y'] - current_y) <= tolerance:
            current_row.append(item)
            # Update average Y
            current_y = sum(i['y'] for i in current_row) / len(current_row)
        else:
            # Sort current row by X before saving
            current_row.sort(key=lambda i: i['x'])
            rows.append(" | ".join([i['text'] for i in current_row]))
            current_row = [item]
            current_y = item['y']
            
    if current_row:
        current_row.sort(key=lambda i: i['x'])
        rows.append(" | ".join([i['text'] for i in current_row]))
        
    return rows

def main():
    audit_path = 'data/etl_audit_report.csv'
    if not os.path.exists(audit_path):
        print("Audit report not found.")
        return
        
    df_audit = pd.read_csv(audit_path)
    no_table_files = df_audit[df_audit['status'] == 'NO_TABLES']
    total_files = len(no_table_files)
    
    print(f"Found {total_files} files requiring OCR.")
    
    # Sort files to prioritize "Bưu chính" so the user can test it immediately
    no_table_files['priority'] = no_table_files['school'].apply(lambda x: 0 if 'Bưu chính' in str(x) or 'BCVT' in str(x) else 1)
    no_table_files = no_table_files.sort_values('priority')
    
    output_csv = 'data/data_tuyensinh.csv'
    
    processed = 0
    for _, row in no_table_files.iterrows():
        folder = row['folder']
        file_name = row['file']
        school_name = row['school']
        
        # In audit_etl.py, folder was just the basename. We need to construct full path.
        # It's either in DATS_2025 or DATS_2024
        base_path = 'data/DATS_2025/1. DATS Năm 2025' if '2025' in folder else 'data/DATS_2024/2. DATS Năm 2024'
        pdf_path = os.path.join(base_path, file_name)
        
        if not os.path.exists(pdf_path):
            print(f"File not found: {pdf_path}")
            continue
            
        print(f"\n[{processed+1}/{total_files}] Processing: {school_name} ({file_name})")
        
        try:
            doc = fitz.open(pdf_path)
            new_rows = []
            
            # To speed up, we only process max 15 pages per document (usually tables are in the first few pages)
            max_pages = min(20, len(doc))
            
            for page_num in range(max_pages):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=150)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                if img.shape[2] == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
                
                page_lines = process_image(img)
                for line in page_lines:
                    new_rows.append([school_name, line])
                    
            if new_rows:
                # Read existing to find max columns
                df_existing = pd.read_csv(output_csv, low_memory=False)
                max_cols = len(df_existing.columns)
                
                # Pad new rows
                padded_rows = [r + [""] * (max_cols - len(r)) for r in new_rows]
                df_new = pd.DataFrame(padded_rows, columns=df_existing.columns)
                
                # Append to CSV
                df_new.to_csv(output_csv, mode='a', header=False, index=False, encoding='utf-8-sig')
                print(f"  -> Added {len(new_rows)} rows to CSV.")
                
        except Exception as e:
            print(f"  -> Error: {e}")
            
        processed += 1

if __name__ == '__main__':
    main()
