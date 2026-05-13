"""
Deep audit of the current ingestion pipeline.
Checks how many PDFs succeed, how many fail, and diagnoses exactly why.
"""
import sys, os, glob
sys.stdout.reconfigure(encoding='utf-8')

import fitz  # PyMuPDF
from agents.recommender import extract_text_with_ocr

pdf_files = glob.glob('./data/**/*.pdf', recursive=True)

total = len(pdf_files)
success = 0
failed_open = 0
empty_after_extract = 0
total_pages_extracted = 0
total_pages_raw = 0
failed_files = []
empty_files = []

for i, path in enumerate(pdf_files, 1):
    if i % 20 == 0:
        print(f"\rAuditing: {i}/{total}...", end="", flush=True)
    
    # First: can we even open the file?
    try:
        with open(path, "rb") as f:
            pdf_bytes = f.read()
        doc = fitz.open("pdf", pdf_bytes)
        raw_pages = len(doc)
        total_pages_raw += raw_pages
        doc.close()
    except Exception as e:
        failed_open += 1
        failed_files.append((path, str(e)))
        continue
    
    # Second: does extract_text_with_ocr return any content?
    docs = extract_text_with_ocr(path)
    if docs:
        success += 1
        total_pages_extracted += len(docs)
    else:
        empty_after_extract += 1
        empty_files.append(path)

print(f"\n\n{'='*60}")
print(f"AUDIT RESULTS")
print(f"{'='*60}")
print(f"Total PDF files found: {total}")
print(f"Successfully extracted: {success}")
print(f"Failed to open:        {failed_open}")
print(f"Opened but empty:      {empty_after_extract}")
print(f"Total raw pages:       {total_pages_raw}")
print(f"Pages with content:    {total_pages_extracted}")
print(f"Pages lost:            {total_pages_raw - total_pages_extracted}")

if failed_files:
    print(f"\n--- FAILED FILES ({len(failed_files)}) ---")
    for path, err in failed_files[:10]:
        print(f"  {os.path.basename(path)}: {err[:80]}")
        
if empty_files:
    print(f"\n--- EMPTY FILES ({len(empty_files)}) ---")
    for path in empty_files[:10]:
        print(f"  {os.path.basename(path)}")

# Now check current DB
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
db = FAISS.load_local('vector_db_tuyensinh', embeddings, allow_dangerous_deserialization=True)

print(f"\n--- CURRENT DB STATUS ---")
print(f"Vectors in DB:         {db.index.ntotal}")

# Check unique source files in DB
sources = set()
for doc in db.docstore._dict.values():
    sources.add(doc.metadata.get('source', 'unknown'))
print(f"Unique source files:   {len(sources)}")
print(f"Missing from DB:       {total - len(sources)} files")
