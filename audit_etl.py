"""
Script phân tích: Tìm tất cả các file PDF mà pdfplumber KHÔNG extract được bảng nào.
So sánh với CSV hiện tại để xác định data gap.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pdfplumber
import os
import pandas as pd

data_folders = [
    r'data\DATS_2025\1. DATS Năm 2025',
    r'data\DATS_2024\2. DATS Năm 2024',
]

results = []

for folder in data_folders:
    if not os.path.exists(folder):
        print(f"⚠️ Folder not found: {folder}")
        continue
    
    pdf_files = [f for f in os.listdir(folder) if f.lower().endswith('.pdf')]
    print(f"\n📁 {folder}: {len(pdf_files)} PDF files")
    
    for pdf_file in sorted(pdf_files):
        pdf_path = os.path.join(folder, pdf_file)
        school_name = pdf_file.split('_')[0] if '_' in pdf_file else pdf_file.replace('.pdf', '')
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_tables = 0
                total_rows = 0
                for page in pdf.pages:
                    tables = page.extract_tables()
                    total_tables += len(tables)
                    for t in tables:
                        total_rows += len(t)
                
                results.append({
                    'folder': os.path.basename(folder),
                    'file': pdf_file,
                    'school': school_name,
                    'pages': len(pdf.pages),
                    'tables': total_tables,
                    'rows': total_rows,
                    'status': 'OK' if total_tables > 0 else 'NO_TABLES'
                })
        except Exception as e:
            results.append({
                'folder': os.path.basename(folder),
                'file': pdf_file,
                'school': school_name,
                'pages': 0,
                'tables': 0,
                'rows': 0,
                'status': f'ERROR: {str(e)[:50]}'
            })

df = pd.DataFrame(results)
print(f"\n{'='*80}")
print(f"📊 TỔNG KẾT:")
print(f"  - Tổng số PDF: {len(df)}")
print(f"  - Extract OK (có bảng): {len(df[df['status']=='OK'])}")
print(f"  - KHÔNG có bảng (NO_TABLES): {len(df[df['status']=='NO_TABLES'])}")
print(f"  - Lỗi: {len(df[~df['status'].isin(['OK','NO_TABLES'])])}")

no_tables = df[df['status'] == 'NO_TABLES']
if not no_tables.empty:
    print(f"\n{'='*80}")
    print(f"❌ CÁC FILE KHÔNG EXTRACT ĐƯỢC BẢNG ({len(no_tables)} files):")
    for _, row in no_tables.iterrows():
        print(f"  [{row['folder']}] {row['school']} ({row['pages']} pages) - {row['file']}")

errors = df[~df['status'].isin(['OK', 'NO_TABLES'])]
if not errors.empty:
    print(f"\n{'='*80}")
    print(f"⚠️ CÁC FILE BỊ LỖI ({len(errors)} files):")
    for _, row in errors.iterrows():
        print(f"  [{row['folder']}] {row['file']}: {row['status']}")

# Save full report
df.to_csv('data/etl_audit_report.csv', index=False, encoding='utf-8-sig')
print(f"\n💾 Report saved to data/etl_audit_report.csv")
