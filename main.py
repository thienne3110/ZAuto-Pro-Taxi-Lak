import json, os, re, time, traceback
import hashlib
import uuid
import queue
import threading
import gc
import random
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
from collections import OrderedDict
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.core.clipboard import Clipboard
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from kivy.core.window import Window
from kivymd.uix.card import MDCard
from kivymd.uix.list import TwoLineAvatarIconListItem, ImageLeftWidget
from kivy.properties import StringProperty, BooleanProperty
from kivymd.toast import toast

# BẮT BUỘC: Cấu hình đồ họa để giảm lag GPU trên Android yếu
from kivy.config import Config
Config.set('graphics', 'multisamples', '0')

# --- 1. HỆ THỐNG LOG PRODUCTION ---
if platform == 'android':
    BASE_PATH = '/data/data/org.zauto.taxi/files/'
    from android.runnable import run_on_ui_thread
    from jnius import autoclass, cast
    from android.permissions import request_permissions, Permission
    from android.broadcast import BroadcastReceiver
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Settings = autoclass('android.provider.Settings')
    Intent = autoclass('android.content.Intent')
    FrameLayout = autoclass('android.widget.FrameLayout')
else:
    BASE_PATH = './'
    def run_on_ui_thread(func): return func

LOG_DIR = os.path.join(BASE_PATH, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    handlers=[RotatingFileHandler(os.path.join(LOG_DIR, 'system.log'), maxBytes=1024*1024, backupCount=3)],
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 2. CƠ SỞ DỮ LIỆU SQLITE (THAY THẾ JSON) ---
DB_PATH = os.path.join(BASE_PATH, 'zauto_pro.db')
db_lock = threading.Lock()

def init_db():
    with db_lock:
        try:
            # THÊM isolation_level=None (Autocommit) để Worker không bị block "Database is locked"
            conn = sqlite3.connect(DB_PATH, timeout=15.0, isolation_level=None)
            c = conn.cursor()
            c.execute('PRAGMA journal_mode=WAL;') # Chống crash khi đọc/ghi đồng thời
            c.execute('CREATE TABLE IF NOT EXISTS config (key_name TEXT PRIMARY KEY, value_data TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, time REAL, group_name TEXT, msg TEXT)')
            conn.commit()
        except Exception as e:
            logger.error(f"init_db error: {e}")
        finally:
            if 'conn' in locals() and conn: conn.close()

# --- 3. LRU CACHE ANTI-DUPLICATE (CHỐNG TRÀN RAM) ---
class LRUCache(OrderedDict):
    def __init__(self, maxsize=1000, *args, **kwds):
        self.maxsize = maxsize
        super().__init__(*args, **kwds)
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            del self[oldest]

CONFIG_FILE = BASE_PATH + 'config.json' # Giữ biến này để không lỗi code nếu sót
HISTORY_FILE = BASE_PATH + 'history.json'
SUPPORT_PHONE = "0838429999"
LICENSE_FILE = os.path.join(BASE_PATH, 'license.dat')
TRIAL_FILE = os.path.join(BASE_PATH, 'trial_check.dat')
def get_machine_id():
    """Lấy ID máy chuẩn (Logic từ launcher_auto_secure.py)"""
    if platform == 'android':
        try:
            Secure = autoclass('android.provider.Settings$Secure')
            content_resolver = PythonActivity.mActivity.getContentResolver()
            return Secure.getString(content_resolver, Secure.ANDROID_ID)
        except: pass
    return str(uuid.getnode())[:12] #

def verify_license(lic_string, machine_id):
    """Xác thực Key dựa trên SHA256 (Logic từ keygen.py)"""
    try:
        if not lic_string or ":" not in lic_string: return False, 0
        expire_ts_str, key_hash = lic_string.split(':')
        expire_ts = int(expire_ts_str)
        # Khớp logic băm SHA256: f"{machine_id}:{expire}"
        raw_data = f"{machine_id}:{expire_ts}"
        calculated_hash = hashlib.sha256(raw_data.encode()).hexdigest()[:32]
        if calculated_hash == key_hash and expire_ts > int(time.time()):
            return True, expire_ts
    except: pass
    return False, 0
KV = '''
# --- ĐỊNH NGHĨA THẺ CUỐC XE (RIDE CARD) ---
<RideCard>:
    orientation: "vertical"
    padding: "16dp"
    spacing: "12dp"
    size_hint_y: None
    height: self.minimum_height # TỰ ĐỘNG CO CAO THEO NỘI DUNG
    adaptive_height: True        # GOM NỘI DUNG VỪA VẶN
    elevation: 2
    shadow_radius: 6
    radius: [15, 15, 15, 15]
    md_bg_color: 1, 1, 1, 1

    MDBoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: "40dp"
        spacing: "15dp"
        FitImage:
            source: "profile.jpg"
            size_hint: None, None
            size: "40dp", "40dp"
            radius: [20, ]
        MDBoxLayout:
            orientation: "vertical"
            MDLabel:
                text: root.group_text
                font_style: "Subtitle1"
                bold: True
                theme_text_color: "Primary"
                shorten: True
                shorten_from: "right"
            MDLabel:
                text: "Vừa xong lúc " + root.time_text
                font_style: "Caption"
                theme_text_color: "Secondary"

    MDSeparator:

    MDLabel:
        text: root.msg_text
        font_style: "Body1"
        theme_text_color: "Custom"
        text_color: 0.15, 0.15, 0.15, 1
        valign: "top"
        halign: "left"

    MDBoxLayout:
        orientation: "horizontal"
        spacing: "15dp"
        size_hint_y: None
        height: "45dp"
        MDRoundFlatButton:
            text: "BỎ QUA"
            size_hint_x: 0.4
            text_color: 0.6, 0.2, 0.2, 1
            line_color: 0.9, 0.5, 0.5, 1
            font_name: "Roboto-Medium"
            on_release: app.remove_ride(root)
        MDRaisedButton:
            text: "NHẬN CUỐC NGAY"
            size_hint_x: 0.6
            md_bg_color: 0.1, 0.5, 0.8, 1
            font_name: "Roboto-Medium"
            elevation: 2
            on_release: app.manual_accept_ride(root)

# --- GIAO DIỆN CHÍNH ---
MDScreen:
    md_bg_color: 0.95, 0.96, 0.98, 1

    MDBottomNavigation:
        id: bottom_nav
        panel_color: 1, 1, 1, 1
        text_color_active: 0.1, 0.5, 0.8, 1
        text_color_normal: 0.6, 0.6, 0.6, 1
        use_text: True

        # ================= TAB 1: CANH ME (RADAR & AUTO CHỐT) =================
        MDBottomNavigationItem:
            name: 'tab_canhme'
            text: 'Canh me'
            icon: 'radar'
            
            MDBoxLayout:
                orientation: "vertical"
                
                # --- CỤM ĐIỀU KHIỂN RADAR & AUTO ---
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: "115dp"
                    padding: "15dp"
                    spacing: "10dp"
                    md_bg_color: 1, 1, 1, 1
                    elevation: 2
                    
                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: "35dp"
                        
                        MDLabel:
                            id: lbl_radar_status
                            text: "HỆ THỐNG ĐANG TẠM DỪNG"
                            font_style: "Subtitle2"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: 0.6, 0.6, 0.6, 1
                            valign: "center"
                            
                        MDLabel:
                            text: "Auto chốt:"
                            font_style: "Caption"
                            bold: True
                            theme_text_color: "Primary"
                            halign: "right"
                            valign: "center"
                            size_hint_x: None
                            width: "70dp"
                            
                        MDSwitch:
                            id: sw_auto_main
                            pos_hint: {'center_y': .5}
                            on_active: app.sync_auto_switch(self.active)
                            
                    MDFillRoundFlatButton:
                        id: btn_toggle_radar
                        text: "BẬT RADAR QUÉT CUỐC"
                        font_name: "Roboto-Bold"
                        font_size: "18sp"
                        size_hint_x: 1
                        size_hint_y: None
                        height: "50dp"
                        md_bg_color: 0.1, 0.6, 0.2, 1
                        on_release: app.toggle_radar()
                
                # --- BANNER CẢNH BÁO ---
                MDBoxLayout:
                    size_hint_y: None
                    height: "35dp"
                    md_bg_color: 1, 0.95, 0.8, 1
                    padding: ["10dp", "0dp"]
                    MDIcon:
                        icon: "alert-circle-outline"
                        theme_text_color: "Custom"
                        text_color: 0.8, 0.5, 0, 1
                        pos_hint: {"center_y": .5}
                        font_size: "18sp"
                    MDLabel:
                        text: " Hãy giữ màn hình sáng để ứng dụng bắt cuốc nhanh nhất."
                        font_style: "Caption"
                        theme_text_color: "Custom"
                        text_color: 0.6, 0.4, 0, 1
                        valign: "center"

                ScrollView:
                    MDBoxLayout:
                        id: ride_list
                        orientation: "vertical"
                        padding: "16dp"
                        spacing: "16dp"
                        adaptive_height: True

        # ================= TAB 2: LỊCH SỬ BẮT CUỐC =================
        MDBottomNavigationItem:
            name: 'tab_tinnhan'
            text: 'Tin nhắn'
            icon: 'message-text-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Lịch sử bắt cuốc"
                    elevation: 1
                    md_bg_color: 1, 1, 1, 1
                    specific_text_color: 0.1, 0.1, 0.1, 1
                    right_action_items: [["delete-sweep-outline", lambda x: app.clear_history()]]
                
                # Nút mở khung chat trôi (Giải pháp 2)
                MDBoxLayout:
                    size_hint_y: None
                    height: "70dp"
                    padding: "12dp"
                    MDRaisedButton:
                        text: "MỞ KHUNG CHAT ZALO WEB"
                        icon: "chat-processing"
                        size_hint_x: 1
                        md_bg_color: 0.1, 0.6, 0.2, 1
                        on_release: app.root.ids.bottom_nav.switch_tab('tab_zalo')

                ScrollView:
                    MDList:
                        id: msg_history_list
        # ---------- TAB MỚI: QUẢN LÝ NHÓM ----------
        MDBottomNavigationItem:
            name: 'tab_nhom'
            text: 'Nhóm'
            icon: 'account-group'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Danh sách nhóm Zalo"
                    elevation: 1
                ScrollView:
                    MDList:
                        id: group_filter_list # Nơi hiện danh sách nhóm và nút gạt
        # ================= TAB 3: TÀI KHOẢN ZALO (QUẢN LÝ KẾT NỐI) =================
        MDBottomNavigationItem:
            name: 'tab_zalo'
            text: 'Tài khoản'
            icon: 'account-circle'
            on_tab_press: app._init_webview_android()
            on_enter: app.set_webview_visible(True)
            on_leave: app.set_webview_visible(False)

            MDBoxLayout:
                orientation: 'vertical'

                MDBoxLayout:
                    id: zalo_status_bar
                    size_hint_y: None
                    height: "48dp"
                    padding: ["12dp", "4dp"]
                    spacing: "10dp"
                    md_bg_color: 0.5, 0.5, 0.5, 1
                    
                    # ... (Các phần icon và label bên trong giữ nguyên) ...

                    FitImage:
                        id: zalo_avatar_view
                        source: "profile.jpg"
                        size_hint: None, None
                        size: "45dp", "45dp"
                        radius: [22.5, ]
                        pos_hint: {"center_y": .5}

                    MDBoxLayout:
                        orientation: "vertical"
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            id: zalo_name_view
                            text: "Chưa kết nối Zalo Web"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            font_style: "Subtitle1"
                            bold: True
                        MDLabel:
                            text: "Trình duyệt nhân Chromium chìm"
                            theme_text_color: "Custom"
                            text_color: 0.9, 0.9, 0.9, 1
                            font_style: "Caption"

                    MDRaisedButton:
                        id: btn_zalo_action
                        text: "TẢI LẠI"
                        size_hint_y: None
                        height: "36dp"
                        md_bg_color: 1, 1, 1, 0.25
                        pos_hint: {"center_y": .5}
                        on_release: app.reload_zalo_web()

                # Placeholder — Python nhúng WebView Java vào đây
                BoxLayout:
                    id: webview_container
                    size_hint_y: 1

        # ================= TAB 4: CÀI ĐẶT (CẤU HÌNH & THÔNG TIN APP) =================
        MDBottomNavigationItem:
            name: 'tab_caidat'
            text: 'Cài đặt'
            icon: 'cog-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Thiết lập hệ thống"
                    elevation: 1
                    md_bg_color: 1, 1, 1, 1
                    specific_text_color: 0.1, 0.1, 0.1, 1
                
                ScrollView:
                    MDBoxLayout:
                        orientation: 'vertical'
                        adaptive_height: True
                        padding: "16dp"
                        spacing: "15dp"
                        
                        # --- 1. THÔNG TIN NGƯỜI TẠO ---
                        MDCard:
                            orientation: "horizontal"
                            adaptive_height: True
                            padding: "12dp"
                            radius: [12, ]
                            md_bg_color: 1, 1, 1, 1
                            FitImage:
                                source: 'profile.jpg'
                                size_hint: None, None
                                size: "50dp", "50dp"
                                radius: [25, ]
                            MDBoxLayout:
                                orientation: 'vertical'
                                padding: ["15dp", 0, 0, 0]
                                MDLabel:
                                    text: "Taxi Lắk - ZAuto VIP"
                                    font_style: "Subtitle1"
                                    bold: True
                                MDLabel:
                                    text: "Hỗ trợ mua: 0838429999"
                                    theme_text_color: "Primary"
                                    font_style: "Caption"

                        MDRaisedButton:
                            text: "CẤP QUYỀN APP"
                            icon: "shield-check"
                            size_hint_x: 1
                            md_bg_color: 0.8, 0.4, 0.1, 1
                            on_release: app.check_permissions_and_guide()
                                
                        # --- 2. CỤM CÔNG TẮC ĐIỀU KHIỂN ---
                        MDCard:
                            orientation: "vertical"
                            adaptive_height: True
                            padding: "10dp"
                            radius: [12, ]
                            elevation: 1
                            md_bg_color: 1, 1, 1, 1
                            MDBoxLayout:
                                size_hint_y: None
                                height: "45dp"
                                MDLabel:
                                    text: "Tự động chốt cuốc"
                                    font_style: "Subtitle2"
                                MDSwitch:
                                    id: sw_auto_settings
                                    pos_hint: {'center_y': .5}
                                    on_active: app.sync_auto_switch(self.active)
                            MDSeparator:
                            MDBoxLayout:
                                size_hint_y: None
                                height: "45dp"
                                MDLabel:
                                    text: "Chỉ nhận tin chứa Từ Khóa"
                                    font_style: "Subtitle2"
                                MDSwitch:
                                    id: sw_filter
                                    pos_hint: {'center_y': .5}
                        
                        # --- 3. CỤM TỪ KHÓA ---
                        MDCard:
                            orientation: "vertical"
                            adaptive_height: True
                            padding: "15dp"
                            spacing: "10dp"
                            radius: [12, ]
                            elevation: 1
                            md_bg_color: 1, 1, 1, 1
                            MDTextField:
                                id: inp_nhan
                                hint_text: "Từ khóa NHẬN (cách nhau dấu phẩy)"
                                helper_text: "Ví dụ: taxi, xe, đón, book"
                                helper_text_mode: "on_focus"
                                icon_right: "check-circle-outline"
                                icon_right_color: 0.1, 0.6, 0.2, 1
                            MDTextField:
                                id: inp_loai
                                hint_text: "Từ khóa BỎ QUA (cách nhau dấu phẩy)"
                                helper_text: "Ví dụ: gửi đồ, 16c, xe tải"
                                helper_text_mode: "on_focus"
                                icon_right: "close-circle-outline"
                                icon_right_color: 0.8, 0.2, 0.2, 1
                            MDTextField:
                                id: inp_reply
                                hint_text: "Nội dung trả lời tự động"
                                helper_text: "Ví dụ: Dạ em nhận cuốc này ạ."
                                helper_text_mode: "on_focus"
                                icon_right: "message-reply-text-outline"
                        
                        MDRaisedButton:
                            text: "LƯU CẤU HÌNH HỆ THỐNG"
                            size_hint_x: 1
                            size_hint_y: None
                            height: "50dp"
                            md_bg_color: 0.1, 0.5, 0.8, 1
                            font_name: "Roboto-Bold"
                            elevation: 2
                            on_release: app.save_config()

                        # --- 4. TRẠNG THÁI BẢN QUYỀN (GIỮ NGUYÊN KIỂU DÁNG GỐC) ---
                        MDCard:
                            orientation: "vertical"
                            size_hint_y: None
                            height: "220dp"
                            padding: "15dp"
                            radius: [12, ]
                            md_bg_color: 1, 1, 1, 1
                            MDLabel:
                                text: "TRẠNG THÁI BẢN QUYỀN"
                                bold: True
                                font_style: "Subtitle1"
                            MDSeparator:
                                padding: [0, 10]
                            MDLabel:
                                id: lbl_key_type
                                text: "Loại Key: Đang kiểm tra..."
                            MDLabel:
                                id: lbl_expiry
                                text: "Hết hạn: --/--/----"
                            MDLabel:
                                text: "SĐT Mua Key: 0838429999"
                                theme_text_color: "Custom"
                                text_color: 0.1, 0.5, 0.8, 1
                            MDRaisedButton:
                                text: "MUA THÊM HẠN / ĐỔI KEY"
                                pos_hint: {"center_x": .5}
                                on_release: app.show_activation_popup_from_settings()

                        MDBoxLayout:
                            size_hint_y: None
                            height: "30dp"
'''
class ActivationPopup(Popup):
    def __init__(self, machine_id, on_success, can_cancel=False, **kwargs):
        super().__init__(**kwargs)
        self.title = "KÍCH HOẠT BẢN QUYỀN ZAUTO VIP"
        
        # --- CẤU HÌNH KÍCH THƯỚC THỦ CÔNG (CHỐNG LỆM NÚT) ---
        self.size_hint = (0.9, None) # Rộng 90% màn hình, cao không theo tỷ lệ %
        self.height = dp(480)        # Chiều cao cố định 480dp (vừa đủ hiện tất cả)
        self.auto_dismiss = can_cancel 
        self.on_success = on_success
        self.machine_id = machine_id

        # --- THIẾT KẾ NỀN TRẮNG CHUẨN VIP ---
        self.background = ""  
        self.background_color = (1, 1, 1, 1) 
        self.title_color = (0, 0, 0, 1)      
        self.separator_color = (0.1, 0.5, 0.8, 1)

        # --- TẠO BỘ CUỘN (SCROLLVIEW) ---
        # Giúp máy màn hình ngắn vẫn vuốt xuống để thấy nút Kích Hoạt
        root_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)

        # Layout chứa toàn bộ nội dung bên trong ScrollView
        main_layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(12), size_hint_y=None)
        # Quan trọng: Dòng này giúp layout tự nở dài ra theo nội dung để ScrollView hoạt động
        main_layout.bind(minimum_height=main_layout.setter('height'))

        # --- 1. NÚT X MÀU ĐỎ (CHỈ HIỆN KHI can_cancel=True) ---
        if can_cancel:
            header = BoxLayout(size_hint_y=None, height=dp(30))
            header.add_widget(Label()) # Đẩy nút X sang phải
            btn_close = Button(
                text="X", size_hint=(None, None), size=(dp(40), dp(30)),
                bold=True, color=(1, 1, 1, 1), background_normal='',
                background_color=(0.8, 0, 0, 1)
            )
            btn_close.bind(on_release=self.dismiss)
            header.add_widget(btn_close)
            main_layout.add_widget(header)

        # --- 2. PHẦN COPY ID MÁY ---
        main_layout.add_widget(Label(
            text="MÃ ID MÁY CỦA BẠN:", 
            color=(0.3, 0.3, 0.3, 1), font_size='14sp', 
            size_hint_y=None, height=dp(20), bold=True
        ))

        self.id_box = TextInput(
            text=machine_id, readonly=True, size_hint_y=None, height=dp(45),
            halign='center', font_size='16sp', font_name="Roboto",
            background_color=(0.95, 0.95, 0.95, 1), foreground_color=(0, 0, 0, 1)
        )
        main_layout.add_widget(self.id_box)

        btn_copy = Button(
            text="CHẠM ĐỂ COPY ID MÁY", 
            size_hint_y=None, height=dp(45),
            bold=True, font_size='15sp', background_normal='',
            background_color=(0.1, 0.5, 0.8, 1)
        )
        btn_copy.bind(on_release=self.copy_to_clipboard)
        main_layout.add_widget(btn_copy)
        
        # --- 3. PHẦN CHỌN GÓI VÀ NHẬP KEY ---
        main_layout.add_widget(Label(
            text="CHỌN GÓI VÀ NHẬP MÃ KEY:", 
            color=(0.2, 0.2, 0.2, 1), font_size='14sp',
            size_hint_y=None, height=dp(20), bold=True
        ))
        
        self.pkg_spin = Spinner(
            text='Chọn gói mua',
            values=('30 Ngày - 30K', '365 Ngày - 300K', 'VĨNH VIỄN - 600K'),
            size_hint_y=None, height=dp(45),
            background_color=(0.1, 0.5, 0.8, 1), color=(1, 1, 1, 1)
        )
        main_layout.add_widget(self.pkg_spin)

        self.key_in = TextInput(
            hint_text="Dán mã Key đã mua vào đây...", 
            multiline=False, size_hint_y=None, height=dp(45),
            halign='center', font_size='15sp'
        )
        main_layout.add_widget(self.key_in)

        # --- 4. THÔNG TIN HỖ TRỢ ---
        main_layout.add_widget(Label(
            text=f"Liên hệ Zalo mua Key: {SUPPORT_PHONE}", 
            font_size='13sp', color=(0.8, 0.2, 0.2, 1),
            size_hint_y=None, height=dp(30)
        ))

        # --- 5. NÚT KÍCH HOẠT ---
        btn_active = Button(
            text="KÍCH HOẠT NGAY", 
            size_hint_y=None, height=dp(55), 
            background_normal='', background_color=(0, 0.5, 0, 1), 
            color=(1, 1, 1, 1), bold=True
        )
        btn_active.bind(on_release=self.validate)
        main_layout.add_widget(btn_active)

        # Gán layout vào ScrollView, gán ScrollView làm nội dung của Popup
        root_scroll.add_widget(main_layout)
        self.content = root_scroll

    def copy_to_clipboard(self, instance):
        """Thực hiện copy ID vào clipboard"""
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(self.machine_id)
        toast("Đã copy ID máy thành công!")

    def validate(self, instance):
        key = self.key_in.text.strip()
        ok, expiry = verify_license(key, self.machine_id)
        if ok:
            with open(LICENSE_FILE, 'w') as f: f.write(key)
            self.on_success(expiry)
            self.dismiss()
        else:
            toast("Mã Key không đúng hoặc đã hết hạn!")
class RideCard(MDCard):
    group_text = StringProperty()
    msg_text = StringProperty()
    time_text = StringProperty()

class ZAutoProApp(MDApp):
    
      
    def toggle_radar(self):
        """Hàm bật/tắt công tắc Radar (Chỉ quét, không quyết định Auto)"""
        self.is_radar_running = not self.is_radar_running
        
        btn = self.root.ids.btn_toggle_radar
        lbl = self.root.ids.lbl_radar_status
        
        if self.is_radar_running:
            btn.text = "ĐANG QUÉT... (BẤM ĐỂ DỪNG)"
            btn.md_bg_color = (0.8, 0.2, 0.2, 1) # Nút chuyển Đỏ
            lbl.text = "RADAR ĐANG HOẠT ĐỘNG"
            lbl.text_color = (0.1, 0.5, 0.8, 1) # Chữ chuyển Xanh dương
            toast("Radar đã BẬT: Đang lắng nghe cuốc xe!")
        else:
            btn.text = "BẬT RADAR QUÉT CUỐC"
            btn.md_bg_color = (0.1, 0.6, 0.2, 1)
            lbl.text = "HỆ THỐNG ĐANG TẠM DỪNG"
            lbl.text_color = (0.6, 0.6, 0.6, 1)
            toast("Radar đã TẠM DỪNG!")

    def sync_auto_switch(self, active_state):
        try:
            if self.root.ids.sw_auto_main.active != active_state:
                self.root.ids.sw_auto_main.active = active_state

            if self.root.ids.sw_auto_settings.active != active_state:
                self.root.ids.sw_auto_settings.active = active_state

            self.save_config_silent()

            toast(
                "Đã bật AUTO CHỐT"
                if active_state else
                "Đã tắt AUTO CHỐT"
            )

        except Exception:
            print(traceback.format_exc())
    def build(self):
        self.icon = 'profile.jpg'
        self.theme_cls.primary_palette = "Blue"
        self.config_data = {
            'nhan': '', 'loai': '', 'reply_msg': 'Ok nhận', 'gia_km': '12000',
            'sw_filter': False, 'sw_auto': False, 'is_linked': False
        }
        self.is_linked = False # Khai báo mặc định là chưa liên kết
        self.root = Builder.load_string(KV)
        
        return self.root

    def on_start(self):
        self.load_config()
        self.check_license_at_startup()
        if platform == 'android':
            try:
                request_permissions([Permission.INTERNET, Permission.ACCESS_FINE_LOCATION, Permission.POST_NOTIFICATIONS])
                autoclass('org.zauto.ZaloForegroundService').startService(PythonActivity.mActivity)

                # ÉP CPU VÀ WIFI KHÔNG ĐƯỢC NGỦ CỰC MẠNH
                PowerManager = autoclass('android.os.PowerManager')
                Context = autoclass('android.content.Context')
                pm = cast(PowerManager, PythonActivity.mActivity.getSystemService(Context.POWER_SERVICE))
                self.wakelock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK | PowerManager.ON_AFTER_RELEASE, "ZAuto::WakeLockCore")
                # BẢO VỆ WAKELOCK ANDROID 14+ BẰNG TIMEOUT 10 PHÚT
                if self.wakelock is not None:
                    try:
                        if self.wakelock.isHeld(): self.wakelock.release()
                    except: pass
                    self.wakelock.acquire(10 * 60 * 1000)

                WifiManager = autoclass('android.net.wifi.WifiManager')
                wm = cast(WifiManager, PythonActivity.mActivity.getApplicationContext().getSystemService(Context.WIFI_SERVICE))
                self.wifilock = wm.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "ZAuto::WifiLockCore")
                if not self.wifilock.isHeld(): self.wifilock.acquire()

                # KHỞI TẠO KIẾN TRÚC REALTIME
                self.processed_msg_hashes = LRUCache(maxsize=1000) # Memory safe
                self.global_last_reply = 0
                self.last_reply_time = LRUCache(maxsize=200)

                # 1. KÍCH HOẠT LUỒNG LẮNG NGHE TIN NHẮN
                self.msg_worker_thread = threading.Thread(target=self._message_worker, daemon=True)
                self.msg_worker_thread.start()

                # 2. KÍCH HOẠT LUỒNG TRẢ LỜI TIN NHẮN
                self.reply_worker_thread = threading.Thread(target=self._reply_worker_loop, daemon=True)
                self.reply_worker_thread.start()

                Clock.schedule_interval(self._system_watchdog, 180)

                # Kích hoạt UI Queue Processor chạy 0.1s/lần
                Clock.schedule_interval(self._process_ui_queue, 0.1)

                if not hasattr(self, 'receiver_started'):
                    self.br = BroadcastReceiver(self.on_broadcast_received, 
                            actions=[
                                'org.zauto.taxi.LOGIN_SUCCESS',
                                'org.zauto.taxi.WEB_NEW_MSG',
                                'org.zauto.taxi.GROUPS_DATA',
                                'org.zauto.taxi.REPLY_RESULT',
                            ])
                    self.br.start()
                    self.receiver_started = True
            except Exception as e:
                logger.error(f"Lỗi on_start: {traceback.format_exc()}")
    def update_group_list_ui(self, groups):
        """Cập nhật danh sách nhóm từ Zalo Web lên giao diện Tab Nhóm"""
        try:
            group_list_widget = self.root.ids.group_filter_list
            # Lấy danh sách các nhóm hiện đang hiển thị trên màn hình
            current_ui_groups = [item.text for item in group_list_widget.children if hasattr(item, 'text')]
            
            from kivymd.uix.list import OneLineIconListItem, IconLeftWidget
            from kivymd.uix.selectioncontrol import MDSwitch
            from kivy.uix.boxlayout import BoxLayout

            for g_name in groups:
                # Nếu nhóm này chưa có trong giao diện thì mới thêm vào
                if g_name not in current_ui_groups:
                    # Mặc định nhóm mới là BẬT nếu chưa từng lưu trạng thái
                    if g_name not in self.enabled_groups:
                        self.enabled_groups[g_name] = True
                    
                    # Tạo item danh sách
                    item = OneLineIconListItem(text=g_name)
                    
                    # Thêm icon đại diện bên trái cho chuyên nghiệp
                    icon = IconLeftWidget(icon="account-group")
                    item.add_widget(icon)
                    
                    # Tạo công tắc gạt bên phải
                    switcher = MDSwitch(
                        active=self.enabled_groups[g_name],
                        pos_hint={'center_x': .9, 'center_y': .5}
                    )
                    
                    # Gán sự kiện khi tài xế gạt nút
                    # Dùng partial hoặc lambda có gán mặc định để tránh lỗi ghi đè biến name
                    switcher.bind(active=lambda sw, val, name=g_name: self.toggle_group(name, val))
                    
                    item.add_widget(switcher)
                    group_list_widget.add_widget(item)
        except Exception as e:
            print(f"Lỗi update_group_list_ui: {e}")

    def toggle_group(self, name, status):
        """Lưu trạng thái bật/tắt của từng nhóm và thông báo"""
        self.enabled_groups[name] = status
        self.save_config_silent() # Lưu ngay vào file config.json
        
        status_text = "BẬT" if status else "TẮT"
        toast(f"{status_text} nhận cuốc nhóm: {name}")            
    def check_license_at_startup(self):
        m_id = get_machine_id()
        current_time = int(time.time())

        # 1. KIỂM TRA BẢN QUYỀN CHÍNH THỨC (KEY VIP) TRƯỚC
        if os.path.exists(LICENSE_FILE):
            try:
                with open(LICENSE_FILE, 'r') as f:
                    key = f.read().strip()
                ok, expiry = verify_license(key, m_id)
                if ok:
                    if expiry < current_time:
                        self.safe_toast("Phát hiện thời gian hệ thống không chính xác!")
                        self.show_activation_popup()
                        return
                    self.apply_license_ui(expiry)
                    return
            except Exception as e:
                logger.error(f"Lỗi đọc license VIP: {e}")

        # 2. CƠ CHẾ OFFLINE CHỐNG GỠ APP & XÓA DATA ĐỂ RESET 15 NGÀY FREE
        trial_expire = 0

        # Đường dẫn file backup ẩn ở phân vùng dùng chung (Không bị xóa khi gỡ cài đặt app)
        backup_dir = "/sdcard/Android/media/org.zauto.taxi/"
        backup_file = os.path.join(backup_dir, ".sys_secure_node.dat")

        # Đọc dữ liệu dùng thử từ 3 nguồn để đối chiếu chéo (Local App, SharedPreferences, Backup SDCard)
        local_val = None
        shared_val = None
        backup_val = None

        # Nguồn A: Đọc file local của App (Bị xóa khi Clear Data hoặc Gỡ cài đặt)
        if os.path.exists(TRIAL_FILE):
            try:
                with open(TRIAL_FILE, 'r') as f:
                    local_val = self._decrypt_secure_data(f.read().strip(), m_id)
            except: pass

        # Nguồn B: Đọc SharedPreferences hệ thống (Bị xóa khi Gỡ cài đặt nhưng GIỮ LẠI khi Clear Data)
        if platform == 'android':
            try:
                context = PythonActivity.mActivity
                shared_pref = context.getSharedPreferences("ZAutoSecureStore", context.MODE_PRIVATE)
                cipher_shared = shared_pref.getString("secure_token", None)
                if cipher_shared:
                    shared_val = self._decrypt_secure_data(cipher_shared, m_id)
            except: pass

        # Nguồn C: Đọc file ẩn ở phân vùng bộ nhớ chung (GIỮ LẠI TRONG MỌI TRƯỜNG HỢP gỡ app hay xóa data)
        if os.path.exists(backup_file):
            try:
                with open(backup_file, 'r') as f:
                    backup_val = self._decrypt_secure_data(f.read().strip(), m_id)
            except: pass

        # --- LOGIC QUYẾT ĐỊNH ĐỒNG BỘ OFFLINE ---
        # Ưu tiên lấy mốc hết hạn dùng thử nhỏ nhất/cũ nhất từng được lưu để chặn đứng hành vi gia hạn lậu
        valid_trials = []
        for val in [local_val, shared_val, backup_val]:
            if val and val.isdigit():
                valid_trials.append(int(val))

        if valid_trials:
            # Phát hiện đã từng cài app hoặc từng dùng thử: Lấy mốc thời gian dùng thử cũ nhất (an toàn nhất)
            trial_expire = min(valid_trials)
        else:
            # Máy hoàn toàn sạch sẽ (Lần đầu tiên cài app thật sự)
            trial_expire = current_time + (15 * 24 * 3600) # Cấp 15 ngày dùng thử

        # ĐỒNG BỘ NGƯỢC LẠI CẢ 3 NƠI ĐỂ KHÓA CHẶT THIẾT BỊ
        cipher_value = self._encrypt_secure_data(str(trial_expire), m_id)
        
        # Đồng bộ Nguồn A
        try:
            with open(TRIAL_FILE, 'w') as f:
                f.write(cipher_value)
        except: pass

        # Đồng bộ Nguồn B
        if platform == 'android':
            try:
                context = PythonActivity.mActivity
                shared_pref = context.getSharedPreferences("ZAutoSecureStore", context.MODE_PRIVATE)
                editor = shared_pref.edit()
                editor.putString("secure_token", cipher_value)
                editor.commit()
            except: pass

        # Đồng bộ Nguồn C (Tạo thư mục ẩn bộ nhớ chung và ghi file)
        try:
            os.makedirs(backup_dir, exist_ok=True)
            with open(backup_file, 'w') as f:
                f.write(cipher_value)
        except: pass

        # 3. CHỐNG QUAY NGƯỢC THỜI GIAN ĐIỆN THOẠI (TIME-TRAVEL PROTECTION)
        last_runtime = self.config_data.get('last_runtime', 0)
        if current_time < last_runtime:
            self.safe_toast("Phát hiện gian lận đổi ngày giờ điện thoại! Thiết bị đã bị khóa.")
            self.show_activation_popup()
            return
            
        # Cập nhật mốc thời gian chạy app mới nhất
        self.config_data['last_runtime'] = current_time
        self.save_config_silent()

        # 4. KIỂM TRA HẠN DÙNG THỬ
        if trial_expire > current_time:
            self.apply_license_ui(trial_expire, is_trial=True)
        else:
            self.show_activation_popup()
    def _encrypt_secure_data(self, data, key):
        """Mã hóa chuỗi dữ liệu dựa trên mã ANDROID_ID duy nhất của phần cứng"""
        try:
            # Sử dụng SHA256 của key phần cứng làm mật mã XOR
            key_hash = hashlib.sha256(key.encode()).hexdigest()
            encrypted = []
            for i in range(len(data)):
                key_c = key_hash[i % len(key_hash)]
                enc_c = chr(ord(data[i]) ^ ord(key_c))
                encrypted.append(enc_c)
            # Chuyển sang dạng Hex an toàn để ghi file
            return "".join(encrypted).encode('utf-8').hex()
        except:
            return data

    def _decrypt_secure_data(self, hex_data, key):
        """Giải mã chuỗi dữ liệu phần cứng"""
        try:
            data = bytes.fromhex(hex_data).decode('utf-8')
            key_hash = hashlib.sha256(key.encode()).hexdigest()
            decrypted = []
            for i in range(len(data)):
                key_c = key_hash[i % len(key_hash)]
                dec_c = chr(ord(data[i]) ^ ord(key_c))
                decrypted.append(dec_c)
            return "".join(decrypted)
        except:
            return hex_data        

    def apply_license_ui(self, expiry, is_trial=False):
        if expiry > 4000000000:
            type_str, date_str = "VĨNH VIỄN (VIP)", "Không giới hạn"
        else:
            type_str = "DÙNG THỬ (FREE)" if is_trial else "TRẢ PHÍ"
            date_str = time.strftime('%d/%m/%Y', time.localtime(expiry))
        
        # Cập nhật thông tin vào Tab Cài đặt
        self.root.ids.lbl_key_type.text = f"Loại Key: {type_str}"
        self.root.ids.lbl_expiry.text = f"Hết hạn: {date_str}"

    def show_activation_popup(self):
        # Sửa self.m_id thành get_machine_id()
        popup = ActivationPopup(machine_id=get_machine_id(), on_success=self.apply_license_ui, can_cancel=False)
        popup.open()
    def show_activation_popup_from_settings(self):
        # Sửa self.m_id thành get_machine_id()
        popup = ActivationPopup(machine_id=get_machine_id(), on_success=self.apply_license_ui, can_cancel=True)
        popup.open()
    def _message_worker(self):
        while getattr(self, 'app_running', True):
            try:
                action, data = self.msg_queue.get(timeout=1.0)
                if action == 'WEB_NEW_MSG':
                    self._process_heavy_message(data)
                self.msg_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Message Worker Crash: {traceback.format_exc()}")
                time.sleep(1) # Chống CPU Spike khi lỗi liên tục

    def _reply_worker_loop(self):
        while getattr(self, 'app_running', True):
            try:
                reply_payload = self.reply_queue.get(timeout=1.0)
                with self.reply_lock:
                    self._execute_reply_safe(reply_payload)
                self.reply_queue.task_done()
                time.sleep(0.5)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Reply Worker Crash: {traceback.format_exc()}")
                time.sleep(1)

    def _process_heavy_message(self, data):
        group = data.get('group', '')
        msg = data.get('msg', '')
        msg_id = data.get('msg_id', '')
        conversation_id = data.get('conversation_id', '')

        if not getattr(self, 'is_radar_running', False): return
        if group in getattr(self, 'enabled_groups', {}) and not self.enabled_groups[group]: return

        # TIẾT KIỆM CPU: Dùng hash() Native thay cho md5()
        raw_hash_data = f"{group}{msg}{msg_id}"
        msg_hash = hash(raw_hash_data)
        
        if msg_hash in self.processed_msg_hashes: return
        self.processed_msg_hashes[msg_hash] = True 

        # TUYỆT ĐỐI KHÔNG ĐỌC UI
        sw_filter_active = self.config_data.get('sw_filter', False)
        if sw_filter_active:
            msg_low = msg.lower()
            loai_keys = [k.strip() for k in self.config_data.get('loai', '').lower().split(',') if k.strip()]
            if loai_keys and any(lk in msg_low for lk in loai_keys): return
            nhan_keys = [k.strip() for k in self.config_data.get('nhan', '').lower().split(',') if k.strip()]
            if nhan_keys and not any(nk in msg_low for nk in nhan_keys): return

        # Đẩy sang UI Queue chống đơ màn hình
        try:
            self.ui_queue.put_nowait(('add_ride', (group, msg, msg_id, conversation_id)))
            self.ui_queue.put_nowait(('log', (group, msg)))
        except queue.Full: pass

        sw_auto_active = self.config_data.get('sw_auto', False)
        if sw_auto_active:
            reply_text = self.config_data.get('reply_msg', 'Ok nhận')
            self.queue_reply(group, conversation_id, msg_id, reply_text)

    def _system_watchdog(self, dt):
        """Khôi phục Worker, Tối ưu RAM và chặn nhân bản Thread"""
        self.gc_counter += 1
        if self.gc_counter % 10 == 0: # Ép xả RAM mức 2 định kỳ
            try: gc.collect(2)
            except: pass
            
        if not getattr(self, 'app_running', False): return

        with self.worker_restart_lock:
            if not hasattr(self, 'msg_worker_thread') or not self.msg_worker_thread.is_alive():
                if not getattr(self, '_restarting_msg_worker', False):
                    self._restarting_msg_worker = True
                    self.msg_worker_thread = threading.Thread(target=self._message_worker, daemon=True)
                    self.msg_worker_thread.start()
                    self._restarting_msg_worker = False

            if not hasattr(self, 'reply_worker_thread') or not self.reply_worker_thread.is_alive():
                if not getattr(self, '_restarting_reply_worker', False):
                    self._restarting_reply_worker = True
                    self.reply_worker_thread = threading.Thread(target=self._reply_worker_loop, daemon=True)
                    self.reply_worker_thread.start()
                    self._restarting_reply_worker = False
    def log_history(self, group, msg):
        # Dùng List chuẩn Material của KivyMD
        item = TwoLineAvatarIconListItem(text=f"[{time.strftime('%H:%M')}] {group}", secondary_text=msg)
        item.add_widget(ImageLeftWidget(source="profile.jpg"))
        self.root.ids.msg_history_list.add_widget(item, index=0)

    def remove_ride(self, card_widget):
        try:
            if hasattr(card_widget, 'unbind'): card_widget.unbind()
            card_widget.clear_widgets()
            self.root.ids.ride_list.remove_widget(card_widget)
            try: del card_widget
            except: pass
        except Exception as e:
            logger.error(f"Lỗi remove_ride: {e}")
    def on_broadcast_received(self, context, intent):
        action = intent.getAction()
        if action == 'org.zauto.taxi.LOGIN_SUCCESS':
            self.is_linked = True
            zalo_name = intent.getStringExtra("zalo_name")
            zalo_avatar = intent.getStringExtra("zalo_avatar")
            if zalo_name: self.config_data['zalo_name'] = zalo_name
            if zalo_avatar: self.config_data['zalo_avatar'] = zalo_avatar
            Clock.schedule_once(lambda dt: self.save_config_silent())
            Clock.schedule_once(lambda dt: self.update_profile_ui())
            Clock.schedule_once(lambda dt: toast("Đã liên kết Zalo Web thành công!"))
            return
        if action == 'org.zauto.taxi.GROUPS_DATA':
            try:
                groups_json = intent.getStringExtra("groups_list")
                if groups_json:
                    groups = json.loads(groups_json)
                    Clock.schedule_once(lambda dt: self.update_group_list_ui(groups))
            except Exception as e: logger.error(f"GROUPS_DATA Error: {e}")
            return
        if action == 'org.zauto.taxi.WEB_NEW_MSG':
            payload = {
                'group': intent.getStringExtra("group") or "",
                'msg': intent.getStringExtra("msg") or "",
                'msg_id': intent.getStringExtra("msg_id") or "", # DATA MỚI TỪ DOM
                'conversation_id': intent.getStringExtra("conversation_id") or ""
            }
            if payload['group'] and payload['msg']:
                try:
                    self.msg_queue.put(('WEB_NEW_MSG', payload), timeout=0.3)
                except queue.Full:
                    logger.warning("msg_queue full bỏ qua Broadcast")

    def add_ride_card(self, group, msg, msg_id="", conversation_id=""):
        try:
            max_rides = 30
            ride_list = self.root.ids.ride_list
            while len(ride_list.children) >= max_rides:
                old_card = ride_list.children[-1]
                ride_list.remove_widget(old_card)
                old_card.clear_widgets()
                del old_card
            card = RideCard(group_text=group, msg_text=msg, time_text=time.strftime("%H:%M"))
            # Gán ẩn data vào Widget để KHÔNG PHẢI SỬA GIAO DIỆN KV
            card.msg_id = msg_id
            card.conversation_id = conversation_id
            self.root.ids.ride_list.add_widget(card, index=0)
        except Exception: logger.error(traceback.format_exc())

    def manual_accept_ride(self, card_widget):
        # Lấy data ẩn ra và ném vào Hàng đợi Reply
        self.queue_reply(card_widget.group_text, getattr(card_widget, 'conversation_id', ''), getattr(card_widget, 'msg_id', ''), self.root.ids.inp_reply.text)
        toast(f"Đang chốt: {card_widget.group_text}")
        self.remove_ride(card_widget)

    def queue_reply(self, group, conversation_id, msg_id, reply_text):
        # KHÓA THỜI GIAN CHỐNG RACE CONDITION
        with self.reply_time_lock:
            now = time.time()
            if now - getattr(self, 'global_last_reply', 0) < 1.5: return 
            self.global_last_reply = now
        
        cache_key = f"{conversation_id}_{msg_id}"
        if now - self.last_reply_time.get(cache_key, 0) < 30: return 
        self.last_reply_time[cache_key] = now

        # BACKPRESSURE: Chặn Queue Overflow
        if self.reply_queue.qsize() > 40:
            logger.warning("Reply queue overload")
            return

        try:
            self.reply_queue.put({'group': group, 'conversation_id': conversation_id, 'msg_id': msg_id, 'reply_text': reply_text}, timeout=0.3)
        except queue.Full:
            logger.warning("reply_queue timeout")

    @run_on_ui_thread
    def _execute_reply_safe(self, payload):
        """HÀM GỌI XUỐNG JAVA PHẢI CHẠY TRÊN UI THREAD CỦA ANDROID"""
        try:
            if platform == 'android' and getattr(self, 'is_linked', False):
                autoclass('org.zauto.ZaloWebManager').sendReplyToSpecificMessage(
                    PythonActivity.mActivity, 
                    payload['conversation_id'], 
                    payload['msg_id'], 
                    payload['reply_text'],
                    payload['group']
                )
                logger.info(f"Đã gửi lệnh chốt: msg_id={payload['msg_id']}")
        except Exception as e:
            logger.error(f"Lỗi _execute_reply_safe: {traceback.format_exc()}")
    
    def load_config(self):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=15.0, isolation_level=None)
            c = conn.cursor()
            c.execute("SELECT key_name, value_data FROM config")
            rows = c.fetchall()
            conn.close()

            # Đặt khung mặc định an toàn trước
            self.config_data = {
                'nhan': '', 'loai': '', 'reply_msg': 'Ok nhận',
                'sw_filter': False, 'sw_auto': False, 'is_linked': False, 
                'enabled_groups': {}, 'zalo_name': 'Chưa kết nối Zalo', 'zalo_avatar': 'profile.jpg'
            }
            # Nếu có data từ DB thì đè lên
            if rows:
                for k, v in rows: 
                    self.config_data[k] = json.loads(v)

            self.is_linked = self.config_data.get('is_linked', False)
            self.enabled_groups = self.config_data.get('enabled_groups', {})

            ids = self.root.ids
            if ids.get('inp_nhan'): ids.inp_nhan.text = self.config_data.get('nhan', '')
            if ids.get('inp_loai'): ids.inp_loai.text = self.config_data.get('loai', '')
            if ids.get('inp_reply'): ids.inp_reply.text = self.config_data.get('reply_msg', 'Ok nhận')
            if ids.get('sw_filter'): ids.sw_filter.active = self.config_data.get('sw_filter', False)
            
            is_auto = self.config_data.get('sw_auto', False)
            if ids.get('sw_auto_settings'): ids.sw_auto_settings.active = is_auto

            self.update_profile_ui()
            if self.enabled_groups:
                Clock.schedule_once(lambda dt: self.update_group_list_ui(self.enabled_groups.keys()), 0)
        except Exception as e:
            logger.error(f"Lỗi SQLite Load: {e}")

    def save_config_silent(self):
        try:
            with db_lock:
                conn = sqlite3.connect(DB_PATH, timeout=15.0, isolation_level=None)
                c = conn.cursor()
                for k, v in self.config_data.items():
                    c.execute("INSERT OR REPLACE INTO config (key_name, value_data) VALUES (?, ?)", (k, json.dumps(v)))
                conn.close()
        except Exception as e:
            logger.error(f"Lỗi SQLite Save: {e}")
    

    def update_profile_ui(self):
        try:
            ids = self.root.ids
            if self.config_data.get('zalo_name') and not self.is_linked:
                self.is_linked = True

            # Thêm điều kiện kiểm tra id có tồn tại trong KV không
            if 'zalo_name_view' in ids:
                ids.zalo_name_view.text = self.config_data.get('zalo_name', "Đã kết nối") if self.is_linked else "Chưa kết nối Zalo"

            if 'zalo_avatar_view' in ids:
                ids.zalo_avatar_view.source = self.config_data.get('zalo_avatar', 'profile.jpg') if self.is_linked else 'profile.jpg'

            if 'btn_zalo_action' in ids:
                ids.btn_zalo_action.text = "HUỶ LIÊN KẾT ZALO" if self.is_linked else "LIÊN KẾT ZALO NGAY"
                ids.btn_zalo_action.md_bg_color = (0.8, 0.2, 0.2, 1) if self.is_linked else (0.1, 0.5, 0.8, 1)
        except Exception as e:
            print(f"Lỗi UI Profile: {e}")

    def save_config(self):
        """BẮT BUỘC ĐỌC UI VÀO BIẾN TRƯỚC KHI XUỐNG DB"""
        try:
            ids = self.root.ids
            if ids.get('inp_nhan'): self.config_data['nhan'] = ids.inp_nhan.text
            if ids.get('inp_loai'): self.config_data['loai'] = ids.inp_loai.text
            if ids.get('inp_reply'): self.config_data['reply_msg'] = ids.inp_reply.text
            if ids.get('sw_filter'): self.config_data['sw_filter'] = ids.sw_filter.active
            if ids.get('sw_auto_main'): self.config_data['sw_auto'] = ids.sw_auto_main.active
            self.config_data['enabled_groups'] = self.enabled_groups
            self.config_data['is_linked'] = self.is_linked
            
            self.save_config_silent()
            self.safe_toast("Đã lưu cấu hình thành công!")
        except Exception as e:
            logger.error(f"Lỗi save_config: {e}")   

    def clear_history(self):
        self.root.ids.msg_history_list.clear_widgets()
        toast("Đã dọn dẹp tin nhắn.")

    def check_permissions_and_guide(self):
        """Hàm tự động quét quyền và điều hướng thông minh"""
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Settings = autoclass('android.provider.Settings')
                Intent = autoclass('android.content.Intent')
                
                context = PythonActivity.mActivity
                resolver = context.getContentResolver()
                
                # Lấy package name hiện tại (org.zauto.taxi)
                pkg_name = context.getPackageName() 
                
                acc_granted = False
                notif_granted = False
                
                # --- 1. KIỂM TRA QUYỀN TRỢ NĂNG (ACCESSIBILITY) ---
                # Đọc chuỗi các dịch vụ trợ năng đang được bật trên điện thoại
                acc_services = Settings.Secure.getString(resolver, "enabled_accessibility_services")
                if acc_services and f"{pkg_name}/org.zauto.ZaloAccessibility" in acc_services:
                    acc_granted = True
                    
                # --- 2. KIỂM TRA QUYỀN ĐỌC THÔNG BÁO (NOTIFICATION LISTENER) ---
                # Đọc chuỗi các dịch vụ nghe thông báo đang được bật
                notif_listeners = Settings.Secure.getString(resolver, "enabled_notification_listeners")
                if notif_listeners and f"{pkg_name}/org.zauto.ZaloNotificationService" in notif_listeners:
                    notif_granted = True

                # --- 3. XỬ LÝ ĐIỀU HƯỚNG ---
                if acc_granted and notif_granted:
                    # Nếu cả 2 quyền cốt lõi đã bật
                    toast("Tuyệt vời! Ứng dụng đã được cấp đầy đủ quyền.")
                
                elif not acc_granted:
                    # Nếu chưa bật Trợ Năng -> Dẫn thẳng vào mục Trợ Năng
                    toast("Vui lòng tìm và BẬT 'ZAuto VIP' trong phần Trợ Năng!")
                    intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    context.startActivity(intent)
                
                elif not notif_granted:
                    # Nếu chưa bật Đọc Thông Báo -> Dẫn thẳng vào mục Quyền Thông Báo
                    toast("Vui lòng CHO PHÉP 'ZAuto VIP' đọc thông báo!")
                    intent = Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS")
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    context.startActivity(intent)

            except Exception:
                import traceback
                print(traceback.format_exc())
                # Backup an toàn nếu điện thoại khách không hỗ trợ hàm check
                toast("Hãy tìm và cấp quyền cho ứng dụng ZAuto VIP")
                try:
                    PythonActivity.mActivity.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                except: pass

    def reload_zalo_web(self):
        if platform == 'android':
            autoclass('org.zauto.ZaloWebManager').reloadWeb(PythonActivity.mActivity)
            toast("Đang tải lại Zalo Web...")

    

   
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app_running = True
        self.is_radar_running = False  
        self.enabled_groups = {}       
        self.webview_inited = False
        self.webview_visible = False
        self._webview_timer = None 
        self.config_data = {}
        self.is_linked = False
        
        # Tối ưu RAM: Giảm Cache xuống 300 chống Leak
        self.processed_msg_hashes = LRUCache(maxsize=300)
        self.global_last_reply = 0
        self.last_reply_time = LRUCache(maxsize=200)
        
        # QUEUE ĐA LUỒNG
        self.msg_queue = queue.Queue(maxsize=500)
        self.reply_queue = queue.Queue(maxsize=50)
        self.ui_queue = queue.Queue(maxsize=100) # Queue chuyên đẩy UI update chống Freeze Kivy
        
        # LOCK SYSTEM CHUẨN
        self.reply_time_lock = threading.Lock()
        self.reply_lock = threading.Lock()
        self.worker_restart_lock = threading.Lock()
        self.toast_lock = threading.Lock()
        
        self._last_toast = 0
        self.gc_counter = 0
        self._restarting_msg_worker = False
        self._restarting_reply_worker = False
        self.last_webview_bounds = None
        Window.softinput_mode = "below_target"

    def safe_toast(self, msg):
        """Bảo vệ UI EventLoop khỏi spam toast"""
        with self.toast_lock:
            now = time.time()
            if now - self._last_toast < 1.5:
                return
            self._last_toast = now
        Clock.schedule_once(lambda dt: toast(msg), 0)

    def _process_ui_queue(self, dt):
        """Xử lý UI Update tập trung, chống Crash & Lag UI"""
        try:
            for _ in range(5): # Giới hạn 5 task / frame
                task, args = self.ui_queue.get_nowait()
                if task == 'add_ride':
                    self.add_ride_card(*args)
                elif task == 'log':
                    self.log_history(*args)
                elif task == 'toast':
                    self.safe_toast(*args)
                self.ui_queue.task_done()
        except queue.Empty:
            pass

    def _init_webview_android(self):
        """Khởi tạo cấu trúc Webview chìm dưới Android"""
        if self.webview_inited: return
        if platform == 'android':
            try:
                activity = PythonActivity.mActivity
                autoclass('org.zauto.ZaloWebManager').initWebView(activity)
                self.webview_inited = True
            except Exception:
                print(traceback.format_exc())

    def set_webview_visible(self, is_visible):
        self.webview_visible = is_visible
        if is_visible:
            if not getattr(self, '_webview_timer', None):
                # GIẢM LAG CPU: Quét toạ độ 0.35s / lần
                self._webview_timer = Clock.schedule_interval(self._sync_webview_pos, 0.35)
        else:
            if getattr(self, '_webview_timer', None):
                self._webview_timer.cancel()
                self._webview_timer = None
            if platform == 'android' and getattr(self, 'webview_inited', False):
                self._hide_webview_overlay()

    @run_on_ui_thread
    def _hide_webview_overlay(self):
        try:
            autoclass('org.zauto.ZaloWebManager').updateWebViewBounds(PythonActivity.mActivity, 0, 0, 0, 0, False)
        except Exception: pass

    def _sync_webview_pos(self, dt):
        if platform != 'android' or not getattr(self, 'webview_inited', False) or not getattr(self, 'webview_visible', False): 
            return
        try:
            container = self.root.ids.webview_container
            
            # CHỐNG ANR: Không render Java Bounds nếu Widget đang nằm ngoài ViewTree
            if not container.get_root_window():
                return
                
            x, y = container.to_window(0, 0)
            w, h = container.size
            
            from kivy.core.window import Window
            android_y = Window.height - (y + h)
            
            new_bounds = (int(x), int(android_y), int(w), int(h))
            if new_bounds == getattr(self, 'last_webview_bounds', None):
                return # Cache bounds -> Không đổi thì không gọi Bridge Java
            
            self.last_webview_bounds = new_bounds
            
            activity = PythonActivity.mActivity
            autoclass('org.zauto.ZaloWebManager').updateWebViewBounds(
                activity, new_bounds[0], new_bounds[1], new_bounds[2], new_bounds[3], True
            )
        except Exception:
            pass
    def on_stop(self):
        self.app_running = False 
        
        # CHỐNG ZOMBIE THREAD: Ép Join luồng trước khi thoát
        try:
            if hasattr(self, 'msg_worker_thread') and self.msg_worker_thread:
                self.msg_worker_thread.join(timeout=2)
            if hasattr(self, 'reply_worker_thread') and self.reply_worker_thread:
                self.reply_worker_thread.join(timeout=2)
        except: pass
        
        if platform == 'android':
            try:
                # CHỐNG LEAK CONTEXT RECEIVER
                if hasattr(self, 'br'):
                    try:
                        self.br.stop()
                        self.br = None
                    except: pass
                    
                # 3. Dùng vòng while nhả triệt để reference counter của Wakelock
                if hasattr(self, 'wakelock') and self.wakelock is not None:
                    try:
                        while self.wakelock.isHeld():
                            self.wakelock.release()
                    except Exception as we: logger.error(f"Wakelock Error: {we}")

                # 4. Nhả triệt để Wifilock
                if hasattr(self, 'wifilock') and self.wifilock is not None:
                    try:
                        while self.wifilock.isHeld():
                            self.wifilock.release()
                    except Exception as wfe: logger.error(f"Wifilock Error: {wfe}")

            except Exception as e:
                logger.error(f"Lỗi dọn dẹp on_stop: {e}")

if __name__ == '__main__':
    ZAutoProApp().run()
