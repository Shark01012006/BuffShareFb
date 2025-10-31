import os
import random
import requests
import time
import json
import threading
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
# Lưu ý: Cần cài đặt thư viện fake_useragent: pip install fake-useragent
from fake_useragent import UserAgent

# Thư viện giao diện GUI hiện đại
# Lưu ý: Cần cài đặt thư viện customtkinter: pip install customtkinter
try:
    import customtkinter as ctk
except ImportError:
    # Đây là thông báo để người dùng cài đặt thư viện nếu chưa có
    print("Vui lòng cài đặt thư viện customtkinter: pip install customtkinter")
    # Sử dụng exit(1) để dừng chương trình nếu không có thư viện GUI cần thiết
    sys.exit(1)

# --- CẤU HÌNH VÀ HÀM LÕI (SHARKISMEXD) ---

user_agents = UserAgent()

CAU_HINH = {
    'DELAY_TOI_THIEU': 0.5,
    'DELAY_TOI_DA': 2.0,
    'SO_LAN_THU_LAI': 3,
    'THOI_GIAN_CHO_REQUEST': 30,
    'XOAY_USER_AGENT': True,
    'TOOL_OWNER': 'SharkIsMexD'
}

def lay_user_agent_ngau_nhien():
    """Lấy một User-Agent ngẫu nhiên."""
    if CAU_HINH['XOAY_USER_AGENT']:
        try:
            return user_agents.random
        except Exception:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def kiem_tra_cookie(cookie):
    """Kiểm tra định dạng cơ bản của cookie."""
    return all(f'{truong}=' in cookie for truong in ['c_user', 'xs'])

def lay_user_id_tu_cookie(cookie_string):
    """Trích xuất c_user ID từ chuỗi cookie (sau khi làm sạch)."""
    if 'c_user=' in cookie_string:
        try:
            # Tách c_user=...; hoặc c_user=... cuối chuỗi
            return cookie_string.split('c_user=')[1].split(';')[0].strip()
        except IndexError:
            pass # Vẫn trả về UNKNOWN nếu có lỗi tách chuỗi
    return "UNKNOWN"

def lam_sach_cookie(cookie_string):
    """
    Lọc và làm sạch chuỗi cookie để chỉ giữ lại các trường quan trọng nhất
    (c_user, xs, datr, sb, fr) nhằm tăng độ ổn định khi lấy token.
    """
    
    # Loại bỏ các ký tự đặc biệt (ví dụ: \xa0, khoảng trắng thừa, v.v.)
    cookie_string = cookie_string.replace(' ', '').replace('\xa0', '').replace('\t', '')
    
    # Các trường cookie tối thiểu cần thiết cho độ ổn định cao
    essential_keys = ['c_user', 'xs', 'datr', 'sb', 'fr']
    
    # Phân tách cookie thành các cặp key=value
    cookie_pairs = cookie_string.split(';')
    
    clean_pairs = {}
    for pair in cookie_pairs:
        if not pair:
            continue
        try:
            # Tách key và value (chỉ tách ở dấu '=' đầu tiên)
            key, value = pair.split('=', 1)
            # Dùng .strip() để loại bỏ khoảng trắng dư thừa quanh key
            key = key.strip() 
            if key in essential_keys:
                clean_pairs[key] = value
        except ValueError:
            # Bỏ qua các cặp không đúng định dạng
            continue
            
    # Xây dựng lại chuỗi cookie sạch
    clean_cookie = "; ".join([f"{k}={v}" for k, v in clean_pairs.items()])
    return clean_cookie

def lay_token(cookie, log_func, so_lan_thu=0):
    """Lấy access token (EAAG token) từ cookie bằng endpoint business.facebook.com/content_management."""
    
    # B1: LÀM SẠCH COOKIE ĐỂ TĂNG ĐỘ ỔN ĐỊNH
    clean_cookie = lam_sach_cookie(cookie)
    user_id = lay_user_id_tu_cookie(clean_cookie)

    if not kiem_tra_cookie(clean_cookie):
        log_func(f"❌ THẤT BẠI | ID: {user_id}. Cookie không hợp lệ (thiếu c_user/xs).", 'error')
        return None
        
    if so_lan_thu == 0:
        log_func(f"Đang thử lấy token | ID: {user_id} (Đã làm sạch cookie)", 'info')

    # B2: CẢI THIỆN HEADERS ĐỂ GIẢ LẬP TRÌNH DUYỆT TỐT HƠN
    headers = {
        'cookie': clean_cookie, # SỬ DỤNG COOKIE ĐÃ LÀM SẠCH
        'user-agent': lay_user_agent_ngau_nhien(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Upgrade-Insecure-Requests': '1',
        # Thêm các header giả lập trình duyệt
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    }
    
    TOKEN_URL = 'https://business.facebook.com/content_management'

    try:
        response = requests.get(
            TOKEN_URL,
            headers=headers,
            timeout=CAU_HINH['THOI_GIAN_CHO_REQUEST']
        )
        response.raise_for_status()
        
        import re
        ket_qua = re.search(r'EAAG\w+', response.text)
        
        if ket_qua:
            token = ket_qua.group(0)
            log_func(f"✅ Token thành công | ID: {user_id}", 'success')
            return f'{clean_cookie}|{token}' # TRẢ VỀ COOKIE ĐÃ LÀM SẠCH VÀ TOKEN
        else:
            log_func(f"⚠️ Không tìm thấy EAAG token | ID: {user_id}. Cookie có thể bị checkpoint.", 'warn')

    except requests.exceptions.RequestException as e:
        if so_lan_thu < CAU_HINH['SO_LAN_THU_LAI']:
            time.sleep(random.uniform(1, 3))
            log_func(f"Đang thử lại lấy token ({so_lan_thu + 1}/{CAU_HINH['SO_LAN_THU_LAI']}) | ID: {user_id}", 'info')
            return lay_token(cookie, log_func, so_lan_thu + 1)
        log_func(f"❌ THẤT BẠI HOÀN TOÀN | ID: {user_id}. Lỗi Request: {e}", 'error')
    except Exception as e:
        log_func(f"❌ THẤT BẠI HOÀN TOÀN | ID: {user_id}. Lỗi không xác định: {e}", 'error')
        
    log_func(f"❌ THẤT BẠI HOÀN TOÀN | ID: {user_id}. Cookie bị loại khỏi chiến dịch.", 'error')
    return None

def chia_se(tach, id_chia_se, log_func, so_lan_thu=0):
    """Thực hiện hành động share bài viết lên tường bằng Graph API."""
    if not tach or '|' not in tach:
        log_func(f"Share thất bại: Cookie/Token bị lỗi.", 'error')
        return False
        
    cookie, token = tach.split('|', 1)
    user_id = lay_user_id_tu_cookie(cookie)
    
    headers = {
        'cookie': cookie,
        'user-agent': lay_user_agent_ngau_nhien()
    }
    
    link = f'https://www.facebook.com/{id_chia_se}'
    
    params = {
        'link': link,
        'published': 0, 
        'access_token': token,
        'fields': 'id'
    }
    
    try:
        res = requests.post(
            'https://graph.facebook.com/v15.0/me/feed', 
            headers=headers,
            params=params,
            timeout=CAU_HINH['THOI_GIAN_CHO_REQUEST']
        )
        data = res.json()
        
        if res.status_code == 200 and data.get('id'):
            log_func(f"✅ Share thành công | ID: {user_id}", 'success')
            return True
        else:
            loi_msg = data.get('error', {}).get('message', f'Lỗi không xác định ({res.status_code}).')
            log_func(f"❌ Share thất bại | ID: {user_id}. Lỗi: {loi_msg}", 'warn')
    except requests.exceptions.RequestException as e:
        if so_lan_thu < CAU_HINH['SO_LAN_THU_LAI']:
            time.sleep(random.uniform(1, 3))
            log_func(f"Đang thử lại share ({so_lan_thu + 1}) | ID: {user_id}. Lỗi: {e}", 'info')
            return chia_se(tach, id_chia_se, log_func, so_lan_thu + 1)
        log_func(f"❌ Share thất bại sau nhiều lần thử | ID: {user_id}. Lỗi Request: {e}", 'error')
    except Exception as e:
        log_func(f"❌ Share thất bại | ID: {user_id}. Lỗi không xác định: {e}", 'error')
        
    return False

# --- LỚP ỨNG DỤNG GUI NÂNG CẤP (SHARKISMEXD) ---

class FacebookShareToolApp(ctk.CTk):
    """Lớp chính tạo ra giao diện và xử lý logic của tool."""
    def __init__(self):
        super().__init__()
        
        # Đổi tên chủ sở hữu tool
        self.title(f"Tool Share Facebook By Shark - {CAU_HINH['TOOL_OWNER']}")
        self.geometry("1200x700")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Biến trạng thái và dữ liệu
        self.isRunning = False
        self.stop_event = threading.Event()
        self.cookie_data = [] # Lưu trữ danh sách cookies
        self.token_list = [] # Lưu trữ danh sách token hợp lệ
        self.sharing_mode = ctk.StringVar(value="Safe Mode") # Biến lưu logic chạy

        # Biến đếm và cấu hình
        self.total_shares_needed = 0
        self.shared_count = 0 # Số lượng tác vụ đã gửi đi (SUBMITTED)
        self.success_count = 0 # Số lượng tác vụ thành công (COMPLETED SUCCESSFULLY)
        self.fail_count = 0
        self.delay = 1.0
        self.thread_pool_size = 5

        # Cấu hình layout (grid) - 3 cột chính
        self.grid_columnconfigure(0, weight=2)  # Cấu hình (20%)
        self.grid_columnconfigure(1, weight=3)  # Cookie List (30%)
        self.grid_columnconfigure(2, weight=5)  # Log (50%)
        self.grid_rowconfigure(0, weight=1)

        # --- CỘT 1: CẤU HÌNH VÀ TIẾN TRÌNH ---
        self.config_frame = ctk.CTkFrame(self, fg_color="#1f2937", corner_radius=15)
        self.config_frame.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        self.config_frame.grid_columnconfigure(0, weight=1)
        # 6 rows total + Nút Start
        self.config_frame.grid_rowconfigure(5, weight=1) # Khung Progress sẽ chiếm phần lớn không gian

        ctk.CTkLabel(self.config_frame, text="⚙️ CẤU HÌNH BUFF SHARE", font=ctk.CTkFont(size=18, weight="bold"), text_color="#60a5fa").grid(row=0, column=0, pady=(15, 20), sticky="n")

        # 1. ID Bài Viết
        id_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        id_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        id_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(id_frame, text="🔗 ID Bài Viết:", anchor="w").pack(pady=(5, 0), fill="x")
        self.entry_post_id = ctk.CTkEntry(id_frame, placeholder_text="Ví dụ: 1234567890 (Chỉ cần ID bài viết)", height=35)
        self.entry_post_id.pack(pady=(0, 10), fill="x")

        # 2. Số Lượt Share Mong Muốn
        share_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        share_frame.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        share_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(share_frame, text="🎯 Lượt Share Mong Muốn:", anchor="w").pack(pady=(5, 0), fill="x")
        self.entry_total_share = ctk.CTkEntry(share_frame, placeholder_text="Mặc định: 50", height=35)
        self.entry_total_share.insert(0, "50")
        self.entry_total_share.pack(pady=(0, 10), fill="x")

        # 3. Thông số kỹ thuật (Delay & Thread)
        tech_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        tech_frame.grid(row=3, column=0, padx=15, pady=10, sticky="ew")
        tech_frame.grid_columnconfigure(0, weight=1)
        tech_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(tech_frame, text="⏱️ Delay (giây):", anchor="w").grid(row=0, column=0, padx=5, pady=(5, 0), sticky="w")
        self.entry_delay = ctk.CTkEntry(tech_frame, placeholder_text="1.0", height=35)
        self.entry_delay.insert(0, "1.0")
        self.entry_delay.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(tech_frame, text="🧵 Số Thread:", anchor="w").grid(row=0, column=1, padx=5, pady=(5, 0), sticky="w")
        self.entry_threads = ctk.CTkEntry(tech_frame, placeholder_text="5", height=35)
        self.entry_threads.insert(0, "5")
        self.entry_threads.grid(row=1, column=1, padx=5, pady=(0, 10), sticky="ew")
        
        # 4. Chọn Logic Chia Sẻ (Safe Mode / Fast Mode)
        logic_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        logic_frame.grid(row=4, column=0, padx=15, pady=10, sticky="ew")
        ctk.CTkLabel(logic_frame, text="🧠 Chọn Logic Tốc Độ:", font=ctk.CTkFont(weight="bold"), anchor="w").pack(pady=(5, 5), fill="x")
        
        radio_safe = ctk.CTkRadioButton(logic_frame, text="Safe Mode (Ổn định, có delay giữa mỗi share)", variable=self.sharing_mode, value="Safe Mode")
        radio_safe.pack(pady=3, fill="x")
        
        radio_fast = ctk.CTkRadioButton(logic_frame, text="Risk Mode (Nhanh, Dễ Die Cookie Acc!)", variable=self.sharing_mode, value="Fast Mode")
        radio_fast.pack(pady=3, fill="x")

        # Khung Tiến trình (Đã chuyển xuống row 5)
        self.progress_container = ctk.CTkFrame(self.config_frame, fg_color="#374151")
        self.progress_container.grid(row=5, column=0, padx=15, pady=15, sticky="ew")
        self.progress_container.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.progress_container, text="📊 TIẾN TRÌNH THỰC HIỆN", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        
        # FIX CỦA LẦN NÀY: Sử dụng self.shared_count (Đã Gửi) để hiển thị tiến trình
        self.progress_text = ctk.CTkLabel(self.progress_container, text="0 / 0", font=ctk.CTkFont(size=24, weight="bold"), text_color="#34d399")
        self.progress_text.pack(pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_container, orientation="horizontal", height=20, fg_color="#6b7280")
        self.progress_bar.set(0)
        self.progress_bar.pack(padx=10, pady=10, fill="x")
        
        # SỬA: Thêm ký tự rõ ràng để hiển thị kết quả cuối cùng
        self.status_label = ctk.CTkLabel(
            self.progress_container, 
            text="✅ Thành công: 0 | ❌ Thất bại: 0 | 🍪 Accounts: 0", 
            text_color="#d1d5db",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=(5, 10))

        # Nút BẮT ĐẦU / DỪNG (Đã chuyển xuống row 6)
        self.btn_start = ctk.CTkButton(self.config_frame, text="🚀 BẮT ĐẦU CHIA SẺ", command=self.toggle_sharing, 
                                       font=ctk.CTkFont(size=18, weight="bold"), fg_color="#34d399", hover_color="#059669", height=50)
        self.btn_start.grid(row=6, column=0, padx=15, pady=(15, 15), sticky="ew")

        # --- CỘT 2: DANH SÁCH COOKIE (Cải thiện thẩm mỹ) ---
        self.cookie_frame = ctk.CTkFrame(self, fg_color="#1f2937", corner_radius=15)
        self.cookie_frame.grid(row=0, column=1, padx=10, pady=20, sticky="nsew")
        self.cookie_frame.grid_columnconfigure(0, weight=1)
        self.cookie_frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self.cookie_frame, text="🍪 QUẢN LÝ TÀI KHOẢN (COOKIES)", 
                     font=ctk.CTkFont(size=18, weight="bold"), text_color="#60a5fa").grid(row=0, column=0, pady=(15, 15), padx=10, sticky="w")

        # Khu vực nhập cookie mới
        add_cookie_frame = ctk.CTkFrame(self.cookie_frame, fg_color="transparent")
        add_cookie_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        add_cookie_frame.grid_columnconfigure(0, weight=1)

        self.entry_new_cookie = ctk.CTkEntry(add_cookie_frame, placeholder_text="Paste Cookie Facebook vào đây", height=35, fg_color="#374151")
        self.entry_new_cookie.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")
        
        ctk.CTkButton(add_cookie_frame, text="➕ Thêm", command=self.add_cookie, width=80, height=35, fg_color="#4f46e5", hover_color="#4338ca").grid(row=0, column=1, padx=(5, 0), pady=5)
        
        # Khu vực hiển thị danh sách cookie
        self.cookie_list_frame = ctk.CTkScrollableFrame(self.cookie_frame, label_text="Tài khoản đã thêm:", label_font=ctk.CTkFont(weight="bold"), fg_color="#1f2937") 
        self.cookie_list_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.cookie_list_frame.grid_columnconfigure(0, weight=1)
        
        # Nút tiện ích
        util_frame = ctk.CTkFrame(self.cookie_frame, fg_color="transparent")
        util_frame.grid(row=3, column=0, padx=10, pady=(5, 15), sticky="ew")
        util_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkButton(util_frame, text="❌ Xóa Tất cả", command=self.clear_cookies, fg_color="#ef4444", hover_color="#dc2626", height=40).grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")
        ctk.CTkButton(util_frame, text="📤 Import (TBA)", command=lambda: self.log("Chức năng Import chưa được cài đặt!", 'warn'), height=40, state="disabled", fg_color="#4b5563", hover_color="#374151").grid(row=0, column=1, padx=(5, 0), pady=5, sticky="ew")
        
        self.update_cookie_list_ui()

        # --- CỘT 3: NHẬT KÝ HOẠT ĐỘNG (LOG) ---
        self.log_frame = ctk.CTkFrame(self, fg_color="#1f2937", corner_radius=15)
        self.log_frame.grid(row=0, column=2, padx=(10, 20), pady=20, sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.log_frame, text="📜 NHẬT KÝ HOẠT ĐỘNG", 
                     font=ctk.CTkFont(size=18, weight="bold"), text_color="#60a5fa").grid(row=0, column=0, pady=(15, 15), padx=10, sticky="w")
        
        self.log_textbox = ctk.CTkTextbox(self.log_frame, width=350, state="disabled", fg_color="#374151")
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        self.log(f"Sẵn sàng. Tool by {CAU_HINH['TOOL_OWNER']}", 'info')

    # --- HÀM XỬ LÝ COOKIE & UI ---

    def update_cookie_list_ui(self):
        """Cập nhật giao diện danh sách cookies (card view) và hiển thị ID người dùng."""
        for widget in self.cookie_list_frame.winfo_children():
            widget.destroy()

        if not self.cookie_data:
            ctk.CTkLabel(self.cookie_list_frame, text="Chưa có tài khoản nào được thêm.", text_color="#a1a1a1").pack(padx=10, pady=10)
            return

        for index, cookie in enumerate(self.cookie_data):
            # Lấy c_user ID từ cookie thô (đã được làm sạch)
            cleaned_cookie = lam_sach_cookie(cookie)
            user_id = lay_user_id_tu_cookie(cleaned_cookie)
            
            # Cải tiến thẩm mỹ: Border màu nổi bật hơn
            cookie_card = ctk.CTkFrame(self.cookie_list_frame, fg_color="#1f2937", corner_radius=8, border_width=2, border_color="#60a5fa")
            cookie_card.pack(fill="x", padx=10, pady=5)
            cookie_card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(cookie_card, text=f"👤 ID: {user_id}", anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")
            
            ctk.CTkButton(cookie_card, text="Xóa", command=lambda i=index: self.remove_cookie(i), 
                          width=50, fg_color="#f87171", hover_color="#ef4444").grid(row=0, column=1, padx=10, pady=5, sticky="e")
            
        self.status_label.configure(text=f"✅ Thành công: {self.success_count} | ❌ Thất bại: {self.fail_count} | 🍪 Accounts: {len(self.cookie_data)}")

    def add_cookie(self):
        """Thêm cookie mới từ ô nhập liệu."""
        cookie = self.entry_new_cookie.get().strip()
        if not cookie:
            self.log("Vui lòng nhập cookie trước khi thêm.", 'warn')
            return
            
        # Kiểm tra cookie đã làm sạch
        if not kiem_tra_cookie(lam_sach_cookie(cookie)):
            self.log("Cookie không hợp lệ (thiếu c_user hoặc xs).", 'error')
            return
            
        if cookie in self.cookie_data:
            self.log("Cookie này đã tồn tại trong danh sách.", 'warn')
            return

        self.cookie_data.append(cookie)
        self.entry_new_cookie.delete(0, "end")
        self.update_cookie_list_ui()
        self.after(0, self.update_progress_ui)
        self.log(f"Đã thêm 1 cookie mới. Tổng số: {len(self.cookie_data)}", 'info')

    def remove_cookie(self, index):
        """Xóa cookie theo index."""
        try:
            del self.cookie_data[index]
            self.update_cookie_list_ui()
            self.after(0, self.update_progress_ui)
            self.log(f"Đã xóa 1 cookie. Tổng số: {len(self.cookie_data)}", 'info')
        except IndexError:
            self.log("Lỗi: Không tìm thấy cookie để xóa.", 'error')

    def clear_cookies(self):
        """Xóa toàn bộ cookies."""
        self.cookie_data = []
        self.update_cookie_list_ui()
        self.after(0, self.update_progress_ui)
        self.log("Đã xóa toàn bộ danh sách cookies.", 'info')

    # --- HÀM CẬP NHẬT UI (Log và Tiến trình) ---
    
    def log(self, message, type='info'):
        """Ghi log vào textbox và cuộn xuống cuối."""
        color_map = {
            'info': '#9ca3af',
            'success': '#34d399',
            'error': '#f87171',
            'warn': '#facc15',
            'start': '#60a5fa'
        }
        timestamp = time.strftime("[%H:%M:%S]")
        formatted_message = f"{timestamp} {message}\n"

        self.log_textbox.configure(state="normal")
        tag_name = type
        self.log_textbox.tag_config(tag_name, foreground=color_map.get(type, '#9ca3af'))
        self.log_textbox.insert("end", formatted_message, tag_name)
        
        self.log_textbox.see("end") 
        self.log_textbox.configure(state="disabled")

    def update_progress_ui(self):
        """
        Cập nhật thanh tiến trình và các số liệu.
        SỬA LỖI UI: self.progress_text hiển thị số lượng tác vụ đã gửi (self.shared_count)
        thay vì số lượng thành công (self.success_count) để người dùng thấy tiến trình tăng ngay.
        """
        # Sửa: Hiển thị ĐÃ GỬI / MỤC TIÊU
        self.progress_text.configure(text=f"{self.shared_count} / {self.total_shares_needed}") 
        
        # Sửa: Hiển thị thông tin chi tiết Thành công / Thất bại
        self.status_label.configure(text=f"✅ Thành công: {self.success_count} | ❌ Thất bại: {self.fail_count} | 🍪 Accounts: {len(self.cookie_data)}")
        
        if self.total_shares_needed > 0:
            # Thanh progress bar vẫn dựa trên success count để phản ánh kết quả thực
            progress_value = self.success_count / self.total_shares_needed
            self.progress_bar.set(progress_value)
        else:
            self.progress_bar.set(0)

    def toggle_sharing(self):
        """Bắt đầu hoặc Dừng quá trình chia sẻ."""
        if self.isRunning:
            self.stop_sharing()
        else:
            self.start_sharing()

    def start_sharing(self):
        """Chuẩn bị và bắt đầu quá trình chia sẻ trong một thread mới."""
        
        post_id = self.entry_post_id.get().strip()
        selected_mode = self.sharing_mode.get()
        
        try:
            self.total_shares_needed = int(self.entry_total_share.get())
            self.delay = float(self.entry_delay.get())
            self.thread_pool_size = int(self.entry_threads.get())
            if self.thread_pool_size > 50:
                self.thread_pool_size = 50
                self.log("Cảnh báo: Số Thread đã được giới hạn tối đa là 50.", 'warn')
        except ValueError:
            self.log("Lỗi: Số lượng share, Delay hoặc Thread phải là số hợp lệ.", 'error')
            return

        if not post_id:
            self.log("Lỗi: Vui lòng nhập ID Bài Viết.", 'error')
            return
            
        if not self.cookie_data:
            self.log("Lỗi: Vui lòng thêm Cookies vào danh sách.", 'error')
            return
            
        # Reset trạng thái
        self.isRunning = True
        self.stop_event.clear()
        self.shared_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.update_progress_ui() # Cập nhật UI ban đầu (0 / Target)

        # Cập nhật UI
        self.btn_start.configure(text="🔴 ĐANG CHẠY - BẤM ĐỂ DỪNG", fg_color="#f87171", hover_color="#ef4444")
        self.log("-----------------------------------------", 'start')
        self.log("BẮT ĐẦU CHIẾN DỊCH CHIA SẺ...", 'start')
        self.log(f"Mục tiêu: {self.total_shares_needed} lượt share | Post ID: {post_id}", 'start')
        self.log(f"Số lượng tài khoản (cookies): {len(self.cookie_data)}", 'start')
        self.log(f"Cấu hình Thread: {self.thread_pool_size} | Delay: {self.delay}s", 'start')
        self.log(f"LOGIC ĐANG CHẠY: {selected_mode}", 'start')
        self.log("-----------------------------------------", 'start')

        # Chạy logic chính trong một thread riêng
        threading.Thread(target=self._sharing_worker_thread, args=(post_id, selected_mode), daemon=True).start()

    def stop_sharing(self):
        """Dừng quá trình chia sẻ."""
        if self.isRunning:
            self.stop_event.set()
            self.isRunning = False
            self.log("Đang chờ các tác vụ hoàn thành. Vui lòng chờ...", 'warn')
            self.btn_start.configure(text="ĐANG DỪNG...", state="disabled")
            
    def _finalize(self):
        """Dọn dẹp sau khi chiến dịch kết thúc hoặc bị dừng."""
        self.isRunning = False
        self.btn_start.configure(text="🚀 BẮT ĐẦU CHIA SẺ", fg_color="#34d399", hover_color="#059669", state="normal")
        self.log("-----------------------------------------", 'start')
        self.log(f"KẾT THÚC | Thành công: {self.success_count} / Thất bại: {self.fail_count}", 'start')
        self.log("-----------------------------------------", 'start')
        
    def _sharing_worker_thread(self, post_id, selected_mode):
        """Thread chính thực hiện lấy token và chia sẻ theo logic đã chọn."""
        
        # Giai đoạn 1: Lấy Token cho tất cả cookies
        self.log("--- Bắt đầu lấy token cho các tài khoản ---", 'info')
        self.token_list = []
        token_futures = []
        
        with ThreadPoolExecutor(max_workers=self.thread_pool_size) as token_executor:
            for cookie in self.cookie_data:
                if self.stop_event.is_set():
                    break
                # Gửi cookie GỐC vào hàm lay_token, hàm này sẽ tự động làm sạch
                token_futures.append(token_executor.submit(lay_token, cookie, self.log))

            for future in as_completed(token_futures):
                if self.stop_event.is_set():
                    break
                result = future.result()
                if result:
                    self.token_list.append(result)

        if not self.token_list:
            self.log("Không lấy được token nào hợp lệ. Dừng chiến dịch.", 'error')
            self._finalize()
            return
            
        self.log(f"✅ Hoàn thành lấy token. Tài khoản hợp lệ: {len(self.token_list)}", 'success')
        
        # Giai đoạn 2: Thực hiện Chia sẻ
        self.log(f"--- Bắt đầu Chia sẻ ({selected_mode}) ---", 'info')
        
        share_futures = []
        
        # Executor cho việc chia sẻ
        with ThreadPoolExecutor(max_workers=self.thread_pool_size) as share_executor:
            i = 0
            
            # Vòng lặp chính dựa trên số lượng tác vụ đã gửi (shared_count)
            while self.shared_count < self.total_shares_needed and not self.stop_event.is_set():
                
                # --- LOGIC SAFE MODE (Chậm và An toàn) ---
                if selected_mode == "Safe Mode":
                    # Delay cho mỗi lần gửi tác vụ
                    delay_time = self.delay * random.uniform(CAU_HINH['DELAY_TOI_THIEU'], CAU_HINH['DELAY_TOI_DA'])
                    time.sleep(delay_time)
                
                if self.stop_event.is_set():
                    break

                # Lấy token theo vòng lặp
                token_to_use = self.token_list[i % len(self.token_list)]
                
                # 2. Gửi tác vụ chia sẻ
                future = share_executor.submit(chia_se, token_to_use, post_id, self.log)
                share_futures.append(future)

                self.shared_count += 1 # Tăng số lượng đã gửi (giúp UI tăng ngay)
                i += 1
                
                self.after(0, self.update_progress_ui) # Cập nhật UI ngay sau khi gửi tác vụ

                # --- LOGIC FAST MODE (Nhanh, không delay) ---
                if selected_mode == "Fast Mode":
                    
                    # CẬP NHẬT: Xử lý kết quả ngay trong vòng lặp để tránh lỗi lặp lại và quản lý queue
                    
                    # Lấy kết quả đã hoàn thành (không chặn)
                    done_futures = [f for f in share_futures if f.done()]
                    for f in done_futures:
                        if f.result():
                            self.success_count += 1
                        else:
                            self.fail_count += 1
                        share_futures.remove(f) # Xóa khỏi list để không xử lý lại
                    
                    self.after(0, self.update_progress_ui)
                    
                    # Kiểm tra và chờ nếu số lượng future đang chạy quá lớn
                    while len(share_futures) >= self.thread_pool_size * 2: # Cho phép gấp đôi số thread tối đa
                        time.sleep(0.1) 
                        # Trong khi chờ, tiếp tục kiểm tra và xử lý các future đã done
                        done_futures = [f for f in share_futures if f.done()]
                        for f in done_futures:
                            if f.result():
                                self.success_count += 1
                            else:
                                self.fail_count += 1
                            share_futures.remove(f)
                        self.after(0, self.update_progress_ui)
                        
                        if self.stop_event.is_set(): break
            
            # --- Xử lý kết quả còn lại sau khi vòng lặp chính dừng ---
            self.log("Đang chờ các tác vụ cuối cùng hoàn thành...", 'info')
            # Tạo một list mới cho các future chưa được tính kết quả (dù có thể đã hoàn thành)
            remaining_futures = share_futures
            
            # Lặp qua tất cả các future còn lại
            for future in as_completed(remaining_futures):
                if self.stop_event.is_set():
                    break
                    
                # Tính toán kết quả
                if future.result():
                    self.success_count += 1
                else:
                    self.fail_count += 1
                
                self.after(0, self.update_progress_ui) 
        
        self._finalize()


if __name__ == "__main__":
    try:
        app = FacebookShareToolApp()
        app.mainloop()
    except Exception as e:
        print(f"Lỗi khởi động ứng dụng GUI: {e}")