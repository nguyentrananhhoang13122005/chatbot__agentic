import streamlit as st
import json
import io
import datetime
import html
import streamlit.components.v1 as components
from auth import change_password, logout
from auth_db import delete_user_account
from chat_db import (
    new_session_id,
    clear_user_chat_sessions,
    clear_searched_universities,
    export_user_data_csv,
)
from ui.pages.auth import login_dialog


def render_settings_page():
    user = st.session_state.get("user")

    # Guard: yêu cầu đăng nhập
    if not user:
        st.markdown("""
        <div class="profile-login-prompt anim-fade-up">
            <div class="profile-lock-icon" style="font-size: 48px; margin-bottom: 16px; color: var(--text-secondary);">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-lock"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            </div>
            <h2>Vui lòng đăng nhập</h2>
            <p>Bạn cần đăng nhập để quản lý cài đặt tài khoản của mình.</p>
        </div>
        """, unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1, 1, 1])
        with col_c:
            if st.button("Đăng nhập ngay", icon=":material/login:", type="primary", use_container_width=True):
                login_dialog()
        return

    # Header
    col_back, col_title = st.columns([0.15, 0.85])
    with col_back:
        if st.button("Trang chủ", icon=":material/arrow_back:", key="settings_back_home"):
            st.session_state.page = "home"
            st.rerun()
    with col_title:
        st.markdown("## ⚙️ Cài đặt hệ thống")

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── SECTION A: CÀI ĐẶT GIAO DIỆN ───
    st.markdown("""
    <div class="profile-section-header anim-fade-up">
        <span class="profile-section-icon" style="vertical-align: middle; margin-right: 4px;">🎨</span>
        <span class="profile-section-title">Giao diện</span>
    </div>
    """, unsafe_allow_html=True)

    current_theme = st.session_state.get("theme", "light")
    
    col_light, col_dark = st.columns(2)
    with col_light:
        is_light = (current_theme == "light")
        btn_type = "primary" if is_light else "secondary"
        if st.button("☀️ Chế độ sáng (Light Mode)", type=btn_type, use_container_width=True, key="set_theme_light"):
            if current_theme != "light":
                st.session_state.theme = "light"
                _trigger_theme_js("light")
                st.rerun()
    with col_dark:
        is_dark = (current_theme == "dark")
        btn_type = "primary" if is_dark else "secondary"
        if st.button("🌙 Chế độ tối (Dark Mode)", type=btn_type, use_container_width=True, key="set_theme_dark"):
            if current_theme != "dark":
                st.session_state.theme = "dark"
                _trigger_theme_js("dark")
                st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ─── SECTION B: ĐỔI MẬT KHẨU ───
    st.markdown("""
    <div class="profile-section-header anim-fade-up">
        <span class="profile-section-icon" style="vertical-align: middle; margin-right: 4px;">🔒</span>
        <span class="profile-section-title">Đổi mật khẩu</span>
    </div>
    """, unsafe_allow_html=True)

    auth_provider = user.get("auth_provider", "email")
    if auth_provider == "google":
        st.info("Tài khoản của bạn đăng nhập bằng Google. Việc thay đổi mật khẩu trực tiếp không được hỗ trợ đối với hình thức liên kết này.")
    else:
        with st.form("settings_change_pass_form", clear_on_submit=True):
            curr_pass = st.text_input("Mật khẩu hiện tại", type="password", key="settings_curr_pass")
            new_pass = st.text_input("Mật khẩu mới (tối thiểu 8 ký tự)", type="password", key="settings_new_pass")
            conf_pass = st.text_input("Xác nhận mật khẩu mới", type="password", key="settings_conf_pass")
            
            submit_pass = st.form_submit_button("Cập nhật mật khẩu", type="primary", use_container_width=True)
            if submit_pass:
                if not curr_pass or not new_pass or not conf_pass:
                    st.error("Vui lòng điền đầy đủ tất cả các trường.")
                elif new_pass != conf_pass:
                    st.error("Mật khẩu xác nhận không khớp.")
                elif len(new_pass) < 8:
                    st.error("Mật khẩu mới phải có ít nhất 8 ký tự.")
                else:
                    success, error = change_password(user["id"], curr_pass, new_pass)
                    if not success:
                        st.error(error or "Không thể đổi mật khẩu. Vui lòng kiểm tra lại.")
                    else:
                        st.success("Đổi mật khẩu thành công!")
                        st.toast("✅ Đổi mật khẩu thành công!")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ─── SECTION C: QUẢN LÝ DỮ LIỆU CÁ NHÂN ───
    st.markdown("""
    <div class="profile-section-header anim-fade-up">
        <span class="profile-section-icon" style="vertical-align: middle; margin-right: 4px;">📦</span>
        <span class="profile-section-title">Quản lý dữ liệu cá nhân</span>
    </div>
    """, unsafe_allow_html=True)

    # Lấy dữ liệu sẵn sàng để export
    chat_csv, uni_csv = export_user_data_csv(user["id"])

    # Columns cho xuất dữ liệu
    st.markdown("##### 📥 Xuất dữ liệu lưu trữ")
    col_exp_chat, col_exp_uni = st.columns(2)
    with col_exp_chat:
        st.download_button(
            label="📥 Xuất lịch sử chat (CSV)",
            data=chat_csv,
            file_name=f"unisearch_chat_history_{user['email']}.csv",
            mime="text/csv",
            use_container_width=True,
            key="settings_download_chat"
        )
    with col_exp_uni:
        st.download_button(
            label="📥 Xuất lịch sử trường ĐH (CSV)",
            data=uni_csv,
            file_name=f"unisearch_university_history_{user['email']}.csv",
            mime="text/csv",
            use_container_width=True,
            key="settings_download_uni"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Xóa dữ liệu (có confirm)
    st.markdown("##### 🧹 Dọn dẹp lịch sử")
    col_del_chat, col_del_uni = st.columns(2)
    
    with col_del_chat:
        if st.session_state.get("confirm_clear_chats_settings"):
            st.warning("Bạn có chắc chắn muốn xóa toàn bộ lịch sử chat?")
            c1, c2 = st.columns(2)
            if c1.button("Xác nhận xóa chat", key="cf_del_chat_set", type="primary", use_container_width=True):
                clear_user_chat_sessions(user["id"])
                st.session_state.pop("confirm_clear_chats_settings", None)
                st.session_state.session_id = new_session_id()
                st.session_state.messages = []
                st.toast("✅ Đã xóa toàn bộ lịch sử chat.")
                st.rerun()
            if c2.button("Hủy bỏ", key="cc_del_chat_set", use_container_width=True):
                st.session_state.pop("confirm_clear_chats_settings", None)
                st.rerun()
        else:
            if st.button("🧹 Xóa toàn bộ lịch sử chat", key="btn_del_chat_set", use_container_width=True):
                st.session_state.confirm_clear_chats_settings = True
                st.rerun()

    with col_del_uni:
        if st.session_state.get("confirm_clear_unis_settings"):
            st.warning("Bạn có chắc muốn xóa lịch sử các trường đã tra cứu?")
            c1, c2 = st.columns(2)
            if c1.button("Xác nhận xóa trường", key="cf_del_uni_set", type="primary", use_container_width=True):
                clear_searched_universities(user["id"])
                st.session_state.pop("confirm_clear_unis_settings", None)
                st.toast("✅ Đã xóa lịch sử trường đã tra cứu.")
                st.rerun()
            if c2.button("Hủy bỏ", key="cc_del_uni_set", use_container_width=True):
                st.session_state.pop("confirm_clear_unis_settings", None)
                st.rerun()
        else:
            if st.button("🧹 Xóa lịch sử trường đã tra cứu", key="btn_del_uni_set", use_container_width=True):
                st.session_state.confirm_clear_unis_settings = True
                st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ─── VÙNG NGUY HIỂM ───
    st.markdown("""
    <div class="profile-section-header settings-danger-title anim-fade-up">
        <span class="profile-section-icon" style="vertical-align: middle; margin-right: 4px;">⚠️</span>
        <span class="profile-section-title" style="color: var(--danger);">Vùng nguy hiểm</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="settings-danger-card">
        <div style="font-weight: 700; margin-bottom: 8px;">Xóa tài khoản vĩnh viễn</div>
        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 16px;">
            Khi thực hiện hành động này, toàn bộ tài khoản, lịch sử chat và dữ liệu cá nhân của bạn sẽ bị xóa vĩnh viễn khỏi hệ thống UniSearch AI và không thể khôi phục lại.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("confirm_delete_account_step1"):
        st.error("⚠️ CẢNH BÁO QUAN TRỌNG: Dữ liệu bị xóa sẽ KHÔNG THỂ KHÔI PHỤC. Vui lòng nhập chữ 'XÓA' viết hoa vào ô dưới đây để xác nhận.")
        confirm_text = st.text_input("Nhập chữ 'XÓA' để xác nhận", key="acc_del_confirm_input")
        
        c1, c2 = st.columns(2)
        with c1:
            # Chỉ kích hoạt nút xóa thực sự khi đã nhập đúng chữ "XÓA"
            is_valid_confirm = (confirm_text == "XÓA")
            if st.button("🔴 Tôi hiểu, hãy xóa tài khoản", key="cf_del_acc_final", type="primary", disabled=not is_valid_confirm, use_container_width=True):
                delete_user_account(user["id"])
                logout()
                st.session_state.session_id = new_session_id()
                st.session_state.messages = []
                st.session_state.page = "home"
                st.session_state.pop("confirm_delete_account_step1", None)
                st.session_state.auth_toast = "👋 Tài khoản của bạn đã được xóa vĩnh viễn."
                st.rerun()
        with c2:
            if st.button("Hủy bỏ", key="cc_del_acc_final", use_container_width=True):
                st.session_state.pop("confirm_delete_account_step1", None)
                st.rerun()
    else:
        col_del_acc_btn, _ = st.columns([1, 1])
        with col_del_acc_btn:
            if st.button("🗑️ Xóa tài khoản của tôi", key="btn_del_acc_step1", type="secondary", use_container_width=True):
                st.session_state.confirm_delete_account_step1 = True
                st.rerun()


def _trigger_theme_js(new_theme: str):
    components.html(f"""
    <script>
    (function() {{
        try {{
            var doc = window.parent.document;
            var html = doc.documentElement;
            html.classList.add('theme-transitioning');
            html.setAttribute('data-theme', '{new_theme}');
            localStorage.setItem('unisearch-theme', '{new_theme}');
            setTimeout(function() {{
                html.classList.remove('theme-transitioning');
            }}, 400);
        }} catch(e) {{}}
    }})();
    </script>
    """, height=0, scrolling=False)
