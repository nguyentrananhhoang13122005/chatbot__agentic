# Script tao GitHub Issues cho du an chatbot__agentic
# Yeu cau: Da cai dat GitHub CLI (gh) va dang nhap (gh auth login)

$REPO = "nguyentrananhhoang13122005/chatbot__agentic"

Write-Host "Bat dau tao Issues cho Phase 1: Backend (Assignee: nguyentrananhhoang13122005)..."
gh issue create --repo $REPO --title "[Phase 1] Task 1: Khoi tao FastAPI va Cau hinh Architecture" --body "Chuyen doi entrypoint tu app.py (Streamlit) sang FastAPI. Cau hinh CORS. Cau truc thu muc routers, schemas." --assignee "nguyentrananhhoang13122005"
gh issue create --repo $REPO --title "[Phase 1] Task 2: Xay dung REST API cho Module Tinh Diem" --body "Viet endpoint /api/v1/scores/calculate. Tao Pydantic Models. Tai su dung logic core/score_calculator.py." --assignee "nguyentrananhhoang13122005"
gh issue create --repo $REPO --title "[Phase 1] Task 3: Xay dung REST API cho Module OCR Hoc Ba" --body "Viet endpoint /api/v1/ocr/upload. Tich hop agents/counselor.py boc tach diem. Tra ket qua JSON." --assignee "nguyentrananhhoang13122005"
gh issue create --repo $REPO --title "[Phase 1] Task 4: Xay dung REST API cho Module Match Maker" --body "Viet endpoint /api/v1/schools/match. Tich hop agents/match_maker.py va agents/recommender.py." --assignee "nguyentrananhhoang13122005"

Write-Host "Bat dau tao Issues cho Phase 2: Frontend Next.js (Assignee: thinhlai06)..."
gh issue create --repo $REPO --title "[Phase 2] Task 5: Khoi tao Project Next.js va Design System" --body "Khoi tao Next.js App Router. Cai dat TailwindCSS va shadcn/ui. Xay dung base components." --assignee "thinhlai06"
gh issue create --repo $REPO --title "[Phase 2] Task 6: Xay dung Landing Page va Form Nhap Diem" --body "Thiet ke UI man hinh chinh. Form nhap diem thi nang dong co validation." --assignee "thinhlai06"
gh issue create --repo $REPO --title "[Phase 2] Task 7: Xay dung Giao dien Upload va Kiem tra OCR" --body "Component keo-tha PDF. Bang du lieu (Data Table) cho phep edit ket qua AI OCR truoc khi gui." --assignee "thinhlai06"
gh issue create --repo $REPO --title "[Phase 2] Task 8: Xay dung Dashboard Hien thi Ket qua" --body "Man hinh ket qua tra cuu. Bieu do ty le do, cards phan loai Safe/Target/Reach." --assignee "thinhlai06"

Write-Host "Bat dau tao Issues cho Phase 3: DevOps va Integration (Assignee: hhuong103)..."
gh issue create --repo $REPO --title "[Phase 3] Task 9: Tich hop API (Frontend goi Backend)" --body "Dung fetch API goi FastAPI endpoint. Xu ly loading, error, luong data." --assignee "hhuong103"
gh issue create --repo $REPO --title "[Phase 3] Task 10: Cap nhat Dockerfile va docker-compose" --body "Cau hinh Docker chay 2 container (FastAPI va Next.js). Cap nhat README deploy." --assignee "hhuong103"

Write-Host "Hoan tat tao tat ca Issues!"
