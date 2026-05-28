import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check():
    conn = sqlite3.connect('data/admissions.db')
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT "Phương thức xét tuyển" FROM diem_chuan_verified')
    rows = cur.fetchall()
    for row in rows:
        print(row[0])

check()
