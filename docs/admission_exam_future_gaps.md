# Những phần tính năng Tư vấn nguyện vọng theo điểm thi THPT chưa cover

Ngày rà soát: 2026-05-27

Tài liệu này ghi lại các khoảng trống còn lại sau khi hoàn tất backend, frontend, Phase 6 và FINAL cross-review theo `implementation_plan.md`. Mục tiêu là giúp các phase sau biết rõ phần nào hệ thống đang hỗ trợ, phần nào đang loại bảo thủ, và phần nào cần bổ sung để tính năng hoàn thiện hơn.

## Trạng thái hiện tại

Hệ thống hiện đã cover các phần chính:

- SQLite là nguồn dữ liệu chính cho pipeline điểm thi THPT.
- Có repository, parser, eligibility evaluator, combo validator, score calculator và matcher riêng cho exam mode.
- Hỗ trợ 4 mode tính điểm: `normal_30`, `weighted_40`, `weighted_convert_30`, `weighted_40_range`.
- Loại khỏi Top K các rule `unsupported`, `regex_fail`, điều kiện fail/unknown, combo thiếu điểm hoặc môn học sinh xác nhận không thi.
- UI đã có mode điểm thi/học bạ tách nhau, input điểm dạng textbox + checkbox "Không thi", input chứng chỉ, học lực/ĐTB lớp 12, annotation, popup missing data.
- Real-data benchmark trên 6,049 rows điểm thi: cache warm Top K=15 khoảng 0.75s.
- Security scan Bandit hiện pass sau khi đánh dấu false-positive SQL placeholder bằng `# nosec B608`.

## Gaps cần cải thiện

### P1. Điều kiện thứ tự nguyện vọng `TTNV`

Hiện chưa có input và evaluator cho thứ tự nguyện vọng. Trong DB thật có các note như:

- `TTNV<=4`
- `TTNV<=1`
- `NK3>=6.25, TTNV <= 4`

Hiện trạng:

- Dòng có `NK3>=6.25, TTNV <= 4` đang rơi vào `regex_fail`.
- Hai dòng chỉ có `TTNV<=4` / `TTNV<=1` có thể bị xem như `normal_30` nếu không bổ sung rule.

Hướng hoàn thiện:

- Thêm field vào `StudentProfile`, ví dụ `aspiration_order: int | None`.
- Thêm input UI "Thứ tự nguyện vọng dự kiến" hoặc ít nhất checkbox "Chưa xét điều kiện TTNV".
- Parser nhận dạng `TTNV <= N`, `TTNV<=N`, `thứ tự nguyện vọng <= N`.
- Nếu chưa có input UI thì nên parse thành `unsupported_reason="aspiration_order_condition"` để loại khỏi Top K, tránh gợi ý sai.
- Nếu có input thì evaluate như hard condition.

Acceptance criteria:

- Row có `TTNV<=N` không được vào Top K khi chưa có dữ liệu.
- Khi user nhập thứ tự nguyện vọng, row chỉ pass nếu `aspiration_order <= N`.
- Missing popup hiển thị "Thứ tự nguyện vọng dự kiến" khi cần.

### P1. Các thành phần xét tuyển ngoài điểm thi THPT

Một số ghi chú đang được loại bảo thủ bằng `unsupported`:

- `ĐGNL`, `ĐGNL BCA`, đánh giá năng lực.
- `CCNNQT` hoặc chứng chỉ ngoại ngữ quốc tế nhưng không có threshold rõ.
- `Học bạ lớp 12 theo tổ hợp 3 môn`.
- `năng lực TA` / `năng lực tiếng Anh`.
- `thang điểm 35`.

Hiện trạng:

- Các rule này bị loại khỏi Top K để tránh tính sai.
- Đây là hành vi an toàn, nhưng chưa phải hỗ trợ đầy đủ.

Hướng hoàn thiện:

- Thiết kế model cho điểm ĐGNL/BCA, điểm thi riêng hoặc các bài đánh giá ngoài THPT.
- Thêm input UI tương ứng: điểm ĐGNL, điểm BCA, chứng chỉ quốc tế, điểm thành phần năng lực tiếng Anh.
- Bổ sung score calculator riêng hoặc converter theo từng loại phương thức.
- Nếu một ngành dùng công thức kết hợp THPT + ĐGNL, cần rule mode mới thay vì ép vào 4 mode điểm thi hiện tại.

Acceptance criteria:

- Rule có `ĐGNL` được tính hoặc bị block có lý do rõ.
- Không có dòng kết hợp external assessment bị auto `normal_30`.
- Annotation hiển thị rõ thành phần ngoài THPT.

### P1. Tiêu chí phụ và ngưỡng môn viết theo dạng tự nhiên

Parser hiện đã hỗ trợ nhiều dạng ngưỡng như `>=`, `>`, `đạt từ`, `tối thiểu`, nhưng vẫn còn các dạng nên bổ sung:

- `Điểm môn Toán: 7.25`
- `Môn Toán/Ngữ văn từ 6 điểm`
- `Toán hoặc Ngữ văn từ 6.0 trở lên`
- `kết hợp tiêu chí phụ: điểm thi môn Lịch sử > 9,25`
- `Tổng điểm 03 môn: 23.75`

Hướng hoàn thiện:

- Mở rộng parser cho toán tử dạng `từ N`, `: N`, `từ N trở lên`.
- Hỗ trợ subject alternatives với dấu `/`.
- Phân biệt tiêu chí phụ tie-breaker và hard condition.
- Với "Tổng điểm 03 môn", cần xác định đây là cutoff/tie-breaker hay rule điều kiện riêng.

Acceptance criteria:

- Các note trên không bị bỏ qua im lặng.
- Nếu chưa evaluate được thì chuyển `regex_fail` hoặc `unsupported`, không auto high confidence.

### P1. `weighted_40_range` vẫn là ước lượng bảo thủ

Với thang 40 nhưng không rõ môn nhân hệ số, hệ thống dùng:

- `score_min`: nhân thêm môn thấp nhất.
- `score_max`: nhân thêm môn cao nhất.
- `ranking_score`: lower bound.

Đây là đúng hướng an toàn, nhưng chưa tối ưu.

Hướng hoàn thiện:

- Suy luận môn nhân từ ngành, tổ hợp hoặc note lân cận nếu có pattern ổn định.
- Cho phép user chọn môn chính nếu trường công bố nhưng note không rõ.
- Lưu `range_reason` chi tiết hơn để UI giải thích vì sao đang xếp hạng bảo thủ.

Acceptance criteria:

- Các dòng thang 40 không rõ môn nhân vẫn không nâng tier bằng upper bound.
- Nếu xác định được môn nhân thì chuyển sang `weighted_40` thay vì `weighted_40_range`.

### P2. Chứng chỉ ngoại ngữ mới chỉ hỗ trợ threshold trực tiếp

Hiện hệ thống hỗ trợ điều kiện kiểu:

- `IELTS >= 5.5`
- `TOEFL >= 60`
- `TOEIC >= 500`

Chưa cover đầy đủ:

- Quy đổi giữa các chứng chỉ.
- `CCNNQT` không nêu rõ loại/chỉ số.
- Điều kiện "IELTS hoặc tương đương".
- Chứng chỉ khác ngoài IELTS/TOEFL/TOEIC.

Hướng hoàn thiện:

- Tạo bảng quy đổi chứng chỉ ngoại ngữ theo quy định/nguồn trường.
- Thêm model `LanguageCertificate`.
- UI cho phép chọn loại chứng chỉ và điểm tương ứng.
- Parser nhận dạng "hoặc tương đương" và map sang bảng quy đổi.

### P2. Điều kiện học bạ/học lực mới cover một phần

Hiện đã có:

- `gpa_12`
- `gpa_subject_12`
- `academic_rank_12`

Chưa cover:

- `điểm xét tốt nghiệp THPT từ 6.5 trở lên`.
- Điều kiện OR đầy đủ: "Học lực lớp 12 khá trở lên hoặc điểm xét tốt nghiệp THPT từ 6.5 trở lên".
- Học bạ theo tổ hợp 3 môn trong exam note.

Hướng hoàn thiện:

- Thêm input `graduation_exam_score` hoặc `high_school_graduation_score`.
- Parser điều kiện `điểm xét tốt nghiệp THPT`.
- Evaluator OR branch đầy đủ giữa học lực và điểm xét tốt nghiệp.

### P2. Parser coverage và taxonomy unresolved

Kết quả real-data gần nhất:

- 6,049 rows exam.
- 557 note không rỗng.
- Deterministic classification khoảng 96.95%.
- 17 note `regex_fail`.
- 160 note `unsupported`.

Hiện còn cần cải thiện:

- Phân loại `unsupported_reason` chi tiết hơn để dễ ưu tiên.
- Tạo report tổng hợp theo reason, trường, ngành, số lượng.
- Tách "không hỗ trợ vì thiếu input" khỏi "không hỗ trợ vì công thức chưa biết".

Hướng hoàn thiện:

- Mở rộng `unresolved_admission_rules.csv` hoặc thêm report JSON/Markdown.
- Thêm dashboard/admin view để xem các note bị loại.
- Bổ sung test snapshot cho top unresolved reasons từ DB thật.

### P2. Cache hiện lazy, chưa có build/prewarm job riêng

Implementation plan có nhắc các function dạng:

- `build_rule_cache(repo)`
- `save_rule_cache`
- `load_rule_cache`
- `get_cached_rule`

Hiện implementation dùng lazy cache trong matcher và repository. Warm cache đạt target, nhưng cold cache trên DB thật có thể mất khoảng 29s.

Hướng hoàn thiện:

- Thêm script CLI `python scripts/build_admission_rule_cache.py`.
- Prewarm cache sau migration hoặc trong deploy.
- Xuất thống kê parse coverage ngay khi build cache.

Acceptance criteria:

- Cold user request đầu tiên không phải parse toàn bộ 6,049 rows.
- Deploy/migration có bước build cache rõ ràng.

### P2. `MatchResult` dataclass chưa được dùng trong matcher output

`MatchResult` đã tồn tại trong model, nhưng matcher hiện trả dict/DataFrame để tiện UI.

Hướng hoàn thiện:

- Dùng `MatchResult` làm intermediate internal result.
- Chỉ convert sang DataFrame ở layer output.
- Giữ DataFrame contract cho UI để không regression.

Lợi ích:

- Dễ test từng row/combo.
- Ít phụ thuộc vào tên cột tiếng Việt trong business logic.

### P2. Method/data access legacy chưa được refactor toàn bộ

Theo plan, chỉ exam pipeline bắt buộc đi qua `AdmissionRepository`; các luồng khác giữ legacy là out of scope.

Chưa cover:

- Transcript mode vẫn dùng logic legacy.
- `recommender.py`, `counselor.py` còn đọc trực tiếp CSV/SQLite theo pattern cũ.

Hướng hoàn thiện:

- Refactor transcript mode sang repository riêng.
- Gom data access vào layer thống nhất.
- Giảm duplicate query/normalization giữa recommender và admission matcher.

### P3. UI verification tự động còn hạn chế

Đã smoke bằng `streamlit.testing.v1`:

- Home light/dark không crash.
- Score analysis page không crash.
- Profile guest không crash.

Chưa cover đầy đủ bằng browser automation:

- Click flow hoàn chỉnh input điểm -> chọn mode -> phân tích -> xem popup.
- Dark mode visual contrast bằng screenshot.
- Responsive desktop/mobile.
- Scroll/anchor "Nhập thêm" trong dialog.

Hướng hoàn thiện:

- Thêm Playwright hoặc một tool E2E tương đương.
- Screenshot baseline cho light/dark.
- Test case cho missing popup và checkbox "Không thi".

### P3. Một số input UI có thể polish thêm

Hiện điểm môn học dùng textbox + checkbox "Không thi", thay cho selectbox trong plan. Đây là thay đổi có chủ đích.

Có thể cải thiện:

- Format lỗi nhập điểm theo từng môn rõ hơn.
- Hỗ trợ paste bảng điểm nhiều dòng.
- Dùng stepper/mask numeric tốt hơn nếu Streamlit hỗ trợ ổn định.
- Thêm "xóa toàn bộ điểm" hoặc "reset môn không thi".

### P3. COMBINATIONS và subject normalization cần audit định kỳ

Các tổ hợp chính đã được bổ sung, gồm cả nhóm năng khiếu. Tuy nhiên vẫn có missing inputs từ real-data smoke như:

- `Khoa học xã hội`
- `Khoa học tự nhiên`
- Một số môn năng khiếu chi tiết như `Vẽ HHMT`, `Vẽ TTM`, `Năng khiếu SKĐA 1`.

Hướng hoàn thiện:

- Quyết định cách quy đổi `Khoa học tự nhiên` / `Khoa học xã hội` sang môn thành phần hoặc điểm bài thi tổ hợp.
- Chuẩn hóa chi tiết môn năng khiếu theo từng trường.
- Thêm fixtures từ dữ liệu thật cho các combo hiếm.

## Backlog gợi ý theo thứ tự ưu tiên

1. Parse/block `TTNV` để tránh lọt Top K sai điều kiện.
2. Tạo prewarm cache script cho production.
3. Mở rộng parser cho `từ N điểm`, `: N`, subject alternative bằng `/`.
4. Thêm input/evaluator cho điểm xét tốt nghiệp THPT.
5. Thiết kế hỗ trợ ĐGNL/BCA và CCNNQT thay vì chỉ unsupported.
6. Thêm Playwright/browser E2E cho score analysis và dark mode.
7. Refactor matcher dùng `MatchResult` internal.
8. Refactor transcript/recommender data access sang repository layer.

## Ghi chú vận hành

- `logs/` đã được đưa vào `.gitignore`; các report runtime không nên commit.
- `PARSER_VERSION` hiện là `regex-v2`; cache cũ `regex-v1` sẽ không được reuse.
- Nếu thêm rule parser mới, cần bump `PARSER_VERSION` khi thay đổi semantics.
- Nếu thêm input mới vào `StudentProfile`, cần cập nhật cả UI payload, combo validator, eligibility evaluator và tests.
