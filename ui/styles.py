import streamlit as st
import streamlit.components.v1 as components

def load_custom_css():
    # === ANTI-FLASH: Blocking script reads localStorage BEFORE any CSS paint ===
    # This runs synchronously on the parent document, setting data-theme
    # AND applying critical inline dark styles before the browser paints anything.
    components.html("""
    <script>
    (function() {
        try {
            var doc = window.parent.document;
            var html = doc.documentElement;
            var saved = localStorage.getItem('unisearch-theme');
            var isDark = (saved === 'dark') ||
                (!saved && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
            if (saved === 'dark' || saved === 'light') {
                html.setAttribute('data-theme', saved);
            } else if (isDark) {
                html.setAttribute('data-theme', 'dark');
            }
            // If dark: apply critical inline styles IMMEDIATELY to prevent any white flash
            if (isDark) {
                html.style.backgroundColor = '#111113';
                html.style.colorScheme = 'dark';
                doc.body.style.backgroundColor = '#111113';
                // Kill the Streamlit header white strip instantly
                var hdr = doc.querySelector('header[data-testid="stHeader"]');
                if (hdr) hdr.style.cssText = 'background:transparent!important;background-color:transparent!important;';
                // Also force the app view container
                var appContainer = doc.querySelector('[data-testid="stAppViewContainer"]') ||
                                   doc.querySelector('.appview-container');
                if (appContainer) appContainer.style.backgroundColor = '#111113';
            }
        } catch(e) {}
    })();
    </script>
    """, height=0, scrolling=False)

    
    import os
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "css", "main.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
    except Exception as e:
        print(f"Error loading css: {e}")
        css = ""
    # Embed Google Fonts via @import inside <style> (works reliably in body, unlike <link>)
    # Also add robust fallback stack for networks that block Google Fonts
    font_import = """
    @import url('https://fonts.googleapis.com/css2?family=Overpass+Mono:wght@400;600;700&family=Space+Grotesk:wght@300;400;500;600;700;800;900&display=swap');
    """
    st.markdown(f"<style>{font_import}\n{css}</style>", unsafe_allow_html=True)

