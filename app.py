import streamlit as st
import sys
import importlib

# Bắt buộc reload lại các module để tránh lỗi cache của Streamlit (trả về None do code cũ)
if "router" in sys.modules:
    import router
    importlib.reload(router)
if "agents.recommender" in sys.modules:
    from agents import recommender
    importlib.reload(recommender)
if "agents.counselor" in sys.modules:
    from agents import counselor
    importlib.reload(counselor)

from router import route_query

# 1. CẤU HÌNH TRANG (Bắt buộc phải đứng đầu)
st.set_page_config(page_title="UniSearch AI", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# 2. XỬ LÝ CSS ĐỂ ÉP MÀU THEO THIẾT KẾ UI (UI Customization)
def load_custom_css():
    st.markdown("""
    <style>
        /* Tùy chỉnh Sidebar background */
        [data-testid="stSidebar"] {
            background-color: #F8FAFC;
        }
        /* Class tiêu đề chính mềm mại */
        .title-main {
            color: #1E293B;
            font-weight: 800;
            text-align: center;
            font-size: 2.8rem;
            margin-bottom: 5px;
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }
        .title-highlight {
            color: #2563EB; /* Xanh dương hiện đại (Blue-600) thay cho màu cam */
        }
        /* Class mô tả phụ */
        .subtitle {
            text-align: center;
            color: #64748B;
            font-size: 1.15rem;
            margin-bottom: 40px;
            font-weight: 400;
        }
        /* Nút Primary bo góc mềm, đổi từ Cam sang Xanh dương Trustworthy */
        div.stButton > button[kind="primary"] {
            background-color: #2563EB;
            color: white;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #1D4ED8;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
            transform: translateY(-2px);
        }
        /* Nút secondary bo góc viên trong suốt */
        div.stButton > button[kind="secondary"] {
            border-radius: 12px;
            background-color: white;
            color: #334155;
            border: 1px solid #E2E8F0;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        div.stButton > button[kind="secondary"]:hover {
            border-color: #2563EB;
            color: #2563EB;
            background-color: #EFF6FF;
        }
        /* Custom UI Cards - Tạo thẻ đổ bóng thay vì viền cứng ngắc */
        .feature-card {
            background: white;
            padding: 24px;
            border-radius: 16px;
            border: 1px solid #E2E8F0;
            text-align: center;
            transition: all 0.3s ease;
            height: 100%;
        }
        .feature-card:hover {
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
            transform: translateY(-5px);
            border-color: #BFDBFE;
        }
        .feature-icon {
            font-size: 2.8rem;
            margin-bottom: 15px;
        }
        .feature-title {
            color: #0F172A;
            font-weight: 700;
            font-size: 1.25rem;
            margin-bottom: 10px;
        }
        .feature-desc {
            color: #64748B;
            font-size: 0.95rem;
            line-height: 1.5;
        }
        /* Card đặc biệt làm điểm nhấn */
        .feature-card.highlight {
            background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
            border-color: #BFDBFE;
        }
        .feature-card.highlight .feature-title {
            color: #1E3A8A;
        }
    </style>
    """, unsafe_allow_html=True)

# 3. QUẢN LÝ TRẠNG THÁI (Session State) ĐỂ ĐIỀU HƯỚNG MÀN HÌNH
if "page" not in st.session_state:
    st.session_state.page = "home" # "home" là màn Landing, "chat" là màn trò chuyện
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. KHỐI HIỂN THỊ SIDEBAR (Thanh bên trái)
def render_sidebar():
    with st.sidebar:
        # Profile giả lập
        st.write("👦 **Học sinh lớp 12**")
        st.caption("Phiên bản hỗ trợ tra cứu ĐH")
        st.divider()
        
        # Nút điều hướng
        if st.button("➕ Phiên tư vấn mới", use_container_width=True, type="primary"):
            st.session_state.page = "home"
            st.session_state.messages = []
            st.rerun()
            
        if st.button("💬 Trò chuyện hiện tại", use_container_width=True, type="secondary"):
            st.session_state.page = "chat"
            st.rerun()
            
        # Lịch sử giả lập
        st.markdown("<br><p style='color:gray; font-size:14px; font-weight:bold;'>Lịch sử tìm kiếm</p>", unsafe_allow_html=True)
        st.button("🕒 Bách Khoa vs KHTN", use_container_width=True)
        st.button("🕒 Ngành Marketing", use_container_width=True)
        st.button("🔖 Lịch sử đã lưu", use_container_width=True)
        
        # Setting / Help phần dưới cùng
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.button("⚙️ Cài đặt", use_container_width=True)
        st.button("❓ Trợ giúp", use_container_width=True)

# 5. KHỐI HIỂN THỊ MÀN HÌNH CHÍNH (Landing Page)
def render_home_page():
    # Tiêu đề được canh chỉnh font hiện đại hơn
    st.markdown("<h1 class='title-main'>Chào mừng đến với <span class='title-highlight'>UniSearch AI!</span></h1>", unsafe_allow_html=True)
    st.markdown("<p class='title-main' style='font-size: 2rem; margin-top:-10px; margin-bottom: 10px;'>Ngôi trường mơ ước đang chờ đón bạn.</p>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Trợ lý thông minh giúp bạn tra cứu điểm chuẩn, tìm ngành học và phân tích CV chuyên sâu.</p>", unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    
    # Chia 3 cột chứa 3 thẻ (Custom Cards không dùng border cứng của Streamlit)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <div class="feature-title">Định hướng ngành</div>
            <div class="feature-desc">Khám phá và phân tích các lựa chọn ngành nghề thực sự phù hợp với thế mạnh của bạn.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Tra cứu điểm chuẩn</div>
            <div class="feature-desc">Dữ liệu tuyển sinh cập nhật chính xác, giúp dự báo cơ hội trúng tuyển an toàn.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="feature-card highlight">
            <div class="feature-icon">✨</div>
            <div class="feature-title">Phân tích CV AI</div>
            <div class="feature-desc">Tải Profile/CV lên, AI sẽ đánh giá năng lực ngoại khóa & đưa ra điểm mạnh điểm yếu.</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("<br><br>", unsafe_allow_html=True)
    
    # Bố trí nút "Bắt đầu" nằm ngay ngắn ở chính giữa (Cột tỷ lệ 1:2:1)
    col_empty1, col_center, col_empty3 = st.columns([1, 1, 1])
    with col_center:
        if st.button("🚀 Bắt đầu trò chuyện ngay", use_container_width=True, type="primary"):
            st.session_state.page = "chat"
            st.rerun()

# 6. KHỐI HIỂN THỊ MÀN HÌNH CHAT (Giao tiếp với Bot)
def render_chat_page():
    st.markdown("<h2 style='color:#003399;'>💬 Trợ lý Tuyển sinh AI</h2>", unsafe_allow_html=True)
    
    # Hiển thị lời chào và Gợi ý (Chips) nếu chưa có tin nhắn nào
    if len(st.session_state.messages) == 0:
        with st.chat_message("assistant", avatar="🤖"):
            st.write("Chào bạn! Bạn muốn tìm hiểu về trường đại học hay ngành học nào hôm nay? Tôi có thể giúp bạn so sánh các trường hoặc dự báo khả năng đậu đại học dựa trên điểm số / CV của bạn.")
            # Nút gợi ý (Suggestion chips)
            st.write("")
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("Top 5 trường CNTT", type="secondary"): st.session_state.messages.append({"role": "user", "content": "Top 5 trường CNTT"})
            if c2.button("Điểm chuẩn Ngoại thương", type="secondary"): st.session_state.messages.append({"role": "user", "content": "Điểm chuẩn Ngoại thương"})
            if c3.button("Học phí RMIT", type="secondary"): st.session_state.messages.append({"role": "user", "content": "Học phí RMIT"})
            if c4.button("So sánh HUST vs KHTN", type="secondary"): st.session_state.messages.append({"role": "user", "content": "So sánh Bách Khoa và KHTN"})

    # In ra toàn bộ lịch sử trò chuyện
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
            st.write(msg["content"])
            
    # Thêm Widget Tải file CV trực tiếp ở khối Chat
    uploaded_cv = st.file_uploader("📥 Tải lên CV / Hồ sơ cá nhân (PDF) tại đây:", type=["pdf"])
    has_file = uploaded_cv is not None
            
    # Ô nhập liệu chat ở dưới cùng
    if prompt := st.chat_input("Nhập câu hỏi của bạn... (Ví dụ: Em có thể thi NEU không?)"):
        # Lưu tin nhắn người dùng
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # In ngay lên màn hình dòng user
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
        
        # Phần cốt lõi (Kết nối tới Router/AI)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("AI đang suy nghĩ và phân tích..."):
                # GỌI ĐẾN ROUTER BỘ NÃO TRUNG TÂM (kèm lịch sử hội thoại gần nhất)
                chat_history = st.session_state.messages[-4:]  # Lấy 4 tin nhắn gần nhất
                final_response = route_query(user_query=prompt, has_file=has_file, uploaded_file=uploaded_cv, chat_history=chat_history)
                st.write(final_response)
                
        # Lưu câu trả lời của Trợ lý
        st.session_state.messages.append({"role": "assistant", "content": final_response})


# ================= KÍCH HOẠT ỨNG DỤNG =================
load_custom_css()
render_sidebar()

if st.session_state.page == "home":
    render_home_page()
else:
    render_chat_page()
