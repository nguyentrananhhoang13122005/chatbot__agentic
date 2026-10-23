import re
from io import BytesIO
from gtts import gTTS

def clean_markdown_for_speech(text: str) -> str:
    """Xóa bỏ các ký tự Markdown thừa để bot đọc mượt mà hơn."""
    if not text:
        return ""
    # Xóa ký tự in đậm, in nghiêng
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # Xóa link
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # Xóa tiêu đề
    text = re.sub(r'#+\s', '', text)
    # Xóa các gạch đầu dòng Markdown dư thừa (tùy chọn)
    text = re.sub(r'^\s*-\s+', '', text, flags=re.MULTILINE)
    
    return text.strip()

def generate_audio_from_text(text: str, lang: str = 'vi') -> bytes:
    """
    Tạo MP3 từ văn bản và lưu trực tiếp vào bộ nhớ đệm (RAM) dưới dạng Bytes.
    Điều này giúp không ghi rác ra ổ cứng của Server.
    """
    clean_text = clean_markdown_for_speech(text)
    if not clean_text:
        return None
        
    try:
        tts = gTTS(text=clean_text, lang=lang, slow=False)
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        print(f"Error generating TTS: {e}")
        return None
