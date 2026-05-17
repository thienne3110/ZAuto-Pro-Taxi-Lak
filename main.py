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
Config.set('kivy', 'pause_on_minimize', '0') # CẤM KIVY NGỦ ĐÔNG KHI ẨN APP

# --- 1. HỆ THỐNG LOG PRODUCTION ---
if platform == 'android':
    # Sửa chữ taxi thành zauto cho khớp với buildozer.spec
    BASE_PATH = '/data/data/org.zauto.zauto/files/'
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
<RideCard>:
    orientation: "vertical"
    padding: "16dp"
    spacing: "12dp"
    size_hint_y: None
    height: self.minimum_height
    adaptive_height: True
    elevation: 0
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
        size_hint_y: None
        height: self.texture_size[1]

    MDBoxLayout:
        orientation: "horizontal"
        spacing: "10dp"
        size_hint_y: None
        height: "45dp"
        MDRoundFlatButton:
            text: "BỎ QUA"
            size_hint_x: 0.4
            text_color: 0.6, 0.2, 0.2, 1
            line_color: 0.9, 0.5, 0.5, 1
            on_release: app.remove_ride(root)
        Button:
            text: "NHẬN CUỐC"
            size_hint_x: 0.6
            size_hint_y: None
            height: "45dp"
            bold: True
            background_normal: ''
            background_color: 0.1, 0.5, 0.8, 1
            on_release: app.manual_accept_ride(root)

MDScreen:
    md_bg_color: 0.95, 0.96, 0.98, 1

    MDBottomNavigation:
        id: bottom_nav
        panel_color: 1, 1, 1, 1
        text_color_active: 0.1, 0.5, 0.8, 1
        text_color_normal: 0.6, 0.6, 0.6, 1
        use_text: True

        # ================= TAB 1: CANH ME =================
        MDBottomNavigationItem:
            name: 'tab_canhme'
            text: 'Canh me'
            icon: 'radar'
            
            MDBoxLayout:
                orientation: "vertical"
                
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    adaptive_height: True
                    padding: "15dp"
                    spacing: "10dp"
                    md_bg_color: 1, 1, 1, 1
                    radius: [0, 0, 15, 15]
                    
                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: "40dp"
                        
                        MDLabel:
                            id: lbl_radar_status
                            text: "TẠM DỪNG"
                            font_style: "Subtitle2"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: 0.6, 0.6, 0.6, 1
                            valign: "center"
                            
                        MDLabel:
                            text: "Auto:"
                            font_style: "Caption"
                            bold: True
                            theme_text_color: "Primary"
                            halign: "right"
                            valign: "center"
                            size_hint_x: None
                            width: "40dp"
                            
                        MDSwitch:
                            id: sw_auto_main
                            pos_hint: {'center_y': .5}
                            on_active: app.sync_auto_switch(self.active)
                            
                    MDFillRoundFlatButton:
                        id: btn_toggle_radar
                        text: "BẬT QUÉT CUỐC"
                        font_name: "Roboto-Bold"
                        size_hint_x: 1
                        size_hint_y: None
                        height: "45dp"
                        md_bg_color: 0.1, 0.6, 0.2, 1
                        on_release: app.toggle_radar()
                
                MDBoxLayout:
                    size_hint_y: None
                    height: "40dp"
                    md_bg_color: 1, 0.95, 0.8, 1
                    padding: ["10dp", "0dp"]
                    MDIcon:
                        icon: "alert-circle-outline"
                        theme_text_color: "Custom"
                        text_color: 0.8, 0.5, 0, 1
                        pos_hint: {"center_y": .5}
                    MDLabel:
                        text: " Giữ sáng màn hình để bắt cuốc"
                        font_style: "Caption"
                        theme_text_color: "Custom"
                        text_color: 0.6, 0.4, 0, 1
                        valign: "center"

                ScrollView:
                    MDBoxLayout:
                        id: ride_list
                        orientation: "vertical"
                        padding: "10dp"
                        spacing: "10dp"
                        size_hint_y: None
                        height: self.minimum_height
                        adaptive_height: True

        # ================= TAB 2: LỊCH SỬ =================
        MDBottomNavigationItem:
            name: 'tab_tinnhan'
            text: 'Tin nhắn'
            icon: 'message-text-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Lịch sử chốt"
                    elevation: 0
                    md_bg_color: 1, 1, 1, 1
                    specific_text_color: 0.1, 0.1, 0.1, 1
                    right_action_items: [["delete-sweep-outline", lambda x: app.clear_history()]]
                
                MDBoxLayout:
                    size_hint_y: None
                    height: "60dp"
                    padding: "10dp"
                    md_bg_color: 1, 1, 1, 1
                    Button:
                        text: "MỞ KHUNG CHAT ZALO"
                        size_hint_x: 1
                        size_hint_y: None
                        height: "45dp"
                        bold: True
                        background_normal: ''
                        background_color: 0.1, 0.6, 0.2, 1
                        on_release: app.root.ids.bottom_nav.switch_tab('tab_zalo')

                ScrollView:
                    MDList:
                        id: msg_history_list
                        md_bg_color: 0.95, 0.96, 0.98, 1

        # ================= TAB NHÓM =================
        MDBottomNavigationItem:
            name: 'tab_nhom'
            text: 'Nhóm'
            icon: 'account-group'
            
            MDBoxLayout:
                orientation: 'vertical'
                
                MDTopAppBar:
                    title: "Danh sách nhóm"
                    elevation: 0
                    md_bg_color: 0.1, 0.6, 0.2, 1
                    specific_text_color: 1, 1, 1, 1
                    pos_hint: {"top": 1}
                    
                ScrollView:
                    MDList:
                        id: group_filter_list
                        md_bg_color: 0.95, 0.96, 0.98, 1

        # ================= TAB TÀI KHOẢN ZALO =================
        MDBottomNavigationItem:
            name: 'tab_zalo'
            text: 'Zalo'
            icon: 'account-circle'
            on_tab_press: app._init_webview_android()
            on_enter: app.set_webview_visible(True)
            on_leave: app.set_webview_visible(False)

            MDBoxLayout:
                orientation: 'vertical'

                MDBoxLayout:
                    id: zalo_status_bar
                    size_hint_y: None
                    height: "65dp"
                    padding: ["10dp", "5dp"]
                    spacing: "10dp"
                    md_bg_color: 0.1, 0.5, 0.8, 1
                    
                    FitImage:
                        id: zalo_avatar_view
                        source: "profile.jpg"
                        size_hint: None, None
                        size: "40dp", "40dp"
                        radius: [20, ]
                        pos_hint: {"center_y": .5}

                    # ---> ĐÃ LÙI LỀ VÀO TRONG NẰM CÙNG HÀNG VỚI FitImage <---
                    MDBoxLayout:
                        orientation: "vertical"
                        pos_hint: {"center_y": .5}
                        md_bg_color: 0.1, 0.5, 0.8, 1
                        MDLabel:
                            id: zalo_name_view
                            text: "Chưa kết nối Zalo"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            font_style: "Subtitle2"
                            bold: True
                        MDLabel:
                            text: "Trình duyệt chìm"
                            theme_text_color: "Custom"
                            text_color: 0.9, 0.9, 0.9, 1
                            font_style: "Caption"

                    # ---> NÚT NÀY CŨNG ĐÃ LÙI LỀ VÀO TRONG <---
                    MDRaisedButton:
                        id: btn_zalo_action
                        text: "TẢI LẠI"
                        size_hint_y: None
                        height: "36dp"
                        md_bg_color: 1, 1, 1, 0.25
                        pos_hint: {"center_y": .5}
                        elevation: 0
                        on_release: app.reload_zalo_web()

                # ---> HỘP CHỨA WEBVIEW PHẢI NẰM NGOÀI ĐỂ XẾP DƯỚI THANH STATUS <---
                MDBoxLayout:
                    id: webview_container
                    size_hint_y: 1
                    md_bg_color: 1, 1, 1, 1

        # ================= TAB CÀI ĐẶT =================
        MDBottomNavigationItem:
            name: 'tab_caidat'
            text: 'Cài đặt'
            icon: 'cog-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Thiết lập hệ thống"
                    elevation: 0
                    md_bg_color: 1, 1, 1, 1
                    specific_text_color: 0.1, 0.1, 0.1, 1
                
                ScrollView:
                    MDBoxLayout:
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        adaptive_height: True
                        padding: "10dp"
                        spacing: "15dp"
                        md_bg_color: 0.95, 0.96, 0.98, 1
                        
                        MDBoxLayout: # Thông tin tài khoản
                            orientation: "horizontal"
                            size_hint_y: None
                            height: "70dp"
                            padding: "10dp"
                            md_bg_color: 1, 1, 1, 1
                            radius: [10, ]
                            FitImage:
                                source: 'profile.jpg'
                                size_hint: None, None
                                size: "50dp", "50dp"
                                radius: [25, ]
                            MDBoxLayout:
                                orientation: 'vertical'
                                padding: ["10dp", 0, 0, 0]
                                MDLabel:
                                    text: "Taxi Lắk - ZAuto VIP"
                                    font_style: "Subtitle2"
                                    bold: True
                                MDLabel:
                                    text: "Hỗ trợ mua: 0838429999"
                                    theme_text_color: "Primary"
                                    font_style: "Caption"

                        # --- KHỐI NÚT ĐIỀU KHIỂN HỆ THỐNG ---
                        MDBoxLayout:
                            orientation: "vertical"
                            size_hint_y: None
                            height: self.minimum_height
                            adaptive_height: True
                            spacing: "10dp"

                            Button:
                                text: "CẤP QUYỀN APP"
                                size_hint_x: 1
                                size_hint_y: None
                                height: "45dp"
                                bold: True
                                background_normal: ''
                                background_color: 0.8, 0.4, 0.1, 1
                                on_release: app.check_permissions_and_guide()
                                
                            Button:
                                text: "CHỐNG NGỦ ĐÔNG (QUAN TRỌNG)"
                                size_hint_x: 1
                                size_hint_y: None
                                height: "45dp"
                                bold: True
                                background_normal: ''
                                background_color: 0.6, 0.1, 0.1, 1
                                on_release: app.request_ignore_battery()

                        # --- KHỐI CÔNG TẮC (GIỌNG NÓI / AUTO / FILTER) ---
                        MDBoxLayout:
                            orientation: "vertical"
                            size_hint_y: None
                            height: self.minimum_height
                            adaptive_height: True
                            padding: "10dp"
                            md_bg_color: 1, 1, 1, 1
                            radius: [10, ]

                            MDBoxLayout:
                                size_hint_y: None
                                height: "45dp"
                                MDLabel:
                                    text: "Đọc giọng nói (Báo cuốc/Chốt)"
                                    font_style: "Subtitle2"
                                MDSwitch:
                                    id: sw_voice
                                    pos_hint: {'center_y': .5}
                            
                            MDSeparator:

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
                            MDSeparator:

                            MDBoxLayout:
                                size_hint_y: None
                                height: "45dp"
                                MDLabel:
                                    text: "Bật bong bóng chat nổi (Floating Bubble)"
                                    font_style: "Subtitle2"
                                MDSwitch:
                                    id: sw_bubble
                                    pos_hint: {'center_y': .5}
                                    on_active: app.toggle_bubble_service(self.active)
                        # --- HƯỚNG DẪN DÙNG TIẾNG VIỆT ---
                        MDBoxLayout:
                            orientation: "vertical"
                            size_hint_y: None
                            height: self.minimum_height 
                            padding: "12dp"
                            spacing: "5dp" 
                            md_bg_color: 0.9, 0.95, 1, 1
                            radius: [10, ]
                            
                            MDLabel:
                                text: "💡 MẸO GÕ TIẾNG VIỆT:"
                                font_style: "Caption"
                                bold: True
                                theme_text_color: "Primary"
                                size_hint_y: None
                                height: self.texture_size[1]
                                
                            MDLabel:
                                text: "Soạn chữ ở Zalo rồi Copy,bấm biểu tượng DÁN ở bên cạnh mỗi ô."
                                font_style: "Caption"
                                theme_text_color: "Secondary"
                                size_hint_y: None
                                height: self.texture_size[1]

                        # --- CÁC Ô NHẬP LIỆU CÓ NÚT DÁN NHANH ---
                        MDBoxLayout: 
                            orientation: "vertical"
                            size_hint_y: None
                            height: self.minimum_height
                            adaptive_height: True
                            padding: "10dp"
                            spacing: "20dp"
                            md_bg_color: 1, 1, 1, 1
                            radius: [10, ]
                            
                            MDBoxLayout:
                                orientation: "horizontal"
                                size_hint_y: None
                                height: "50dp"
                                spacing: "10dp"
                                TextInput:
                                    id: inp_nhan
                                    hint_text: "Từ khóa NHẬN"
                                    multiline: True
                                    background_color: 0.95, 0.95, 0.95, 1
                                    foreground_color: 0, 0, 0, 1
                                MDIconButton:
                                    icon: "content-paste"
                                    pos_hint: {"center_y": .5}
                                    on_release: inp_nhan.text = app.Clipboard.paste()

                            MDBoxLayout:
                                orientation: "horizontal"
                                size_hint_y: None
                                height: "50dp"
                                spacing: "10dp"
                                TextInput:
                                    id: inp_loai
                                    hint_text: "Từ khóa BỎ QUA"
                                    multiline: True
                                    background_color: 0.95, 0.95, 0.95, 1
                                    foreground_color: 0, 0, 0, 1
                                MDIconButton:
                                    icon: "content-paste"
                                    pos_hint: {"center_y": .5}
                                    on_release: inp_loai.text = app.Clipboard.paste()

                            MDBoxLayout:
                                orientation: "horizontal"
                                size_hint_y: None
                                height: "50dp"
                                spacing: "10dp"
                                TextInput:
                                    id: inp_reply
                                    hint_text: "Nội dung trả lời tự động"
                                    multiline: True
                                    background_color: 0.95, 0.95, 0.95, 1
                                    foreground_color: 0, 0, 0, 1
                                MDIconButton:
                                    icon: "content-paste"
                                    pos_hint: {"center_y": .5}
                                    on_release: inp_reply.text = app.Clipboard.paste()
                                
                            TextInput:
                                id: inp_delay
                                hint_text: "Khoảng cách chốt 2 cuốc (giây)"
                                text: "30"
                                input_filter: "int"
                                size_hint_y: None
                                height: "45dp"
                                background_color: 0.95, 0.95, 0.95, 1
                                foreground_color: 0, 0, 0, 1
                        
                        Button:
                            text: "LƯU CẤU HÌNH"
                            size_hint_x: 1
                            size_hint_y: None
                            height: "45dp"
                            bold: True
                            background_normal: ''
                            background_color: 0.1, 0.5, 0.8, 1
                            on_release: app.save_config()

                        MDBoxLayout:
                            orientation: "vertical"
                            size_hint_y: None
                            height: "180dp"
                            padding: "15dp"
                            spacing: "5dp"
                            md_bg_color: 1, 1, 1, 1
                            radius: [10, ]
                            MDLabel:
                                text: "BẢN QUYỀN"
                                bold: True
                                font_style: "Subtitle2"
                            MDSeparator:
                            MDLabel:
                                id: lbl_key_type
                                text: "Loại Key: Đang kiểm tra..."
                                font_style: "Caption"
                            MDLabel:
                                id: lbl_expiry
                                text: "Hết hạn: --/--/----"
                                font_style: "Caption"
                            MDLabel:
                                text: "SĐT Mua Key: 0838429999"
                                theme_text_color: "Custom"
                                text_color: 0.1, 0.5, 0.8, 1
                                font_style: "Caption"
                            Button:
                                text: "MUA THÊM HẠN"
                                size_hint_y: None
                                height: "35dp"
                                pos_hint: {"center_x": .5}
                                bold: True
                                background_normal: ''
                                background_color: 0.1, 0.6, 0.2, 1
                                on_release: app.show_activation_popup_from_settings()

                        MDBoxLayout:
                            size_hint_y: None
                            height: "20dp"
                            md_bg_color: 0.95, 0.96, 0.98, 1
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

            # FIX 1: BẮT BUỘC PHẢI CẬP NHẬT VÀO BỘ NHỚ RAM TRƯỚC KHI LƯU
            self.config_data['sw_auto'] = active_state
            self.save_config_silent()

            toast("Đã bật AUTO CHỐT" if active_state else "Đã tắt AUTO CHỐT")

        except Exception:
            print(traceback.format_exc())
    def build(self):
        from kivy.core.clipboard import Clipboard # Thêm dòng này
        self.Clipboard = Clipboard
        self.icon = 'profile.jpg'
        self.theme_cls.primary_palette = "Blue"
        self.config_data = {
            'nhan': '', 'loai': '', 'reply_msg': 'Ok nhận', 'gia_km': '12000',
            'global_delay': '30', 'sw_voice': True,
            'sw_filter': False, 'sw_auto': False, 'is_linked': False,
            'sw_bubble': True
        }
        self.last_global_reply_time = 0 # Thêm dòng này để theo dõi thời gian chốt cuối cùng
        self.is_linked = False # Khai báo mặc định là chưa liên kết
        self.root = Builder.load_string(KV)
        
        return self.root

    def on_start(self):
        init_db()
        self.load_config()
        self.check_license_at_startup()
        if platform == 'android':
            try:
                # THÊM QUYỀN ĐỂ ĐỌC/GHI FILE ẨN CHỐNG GIAN LẬN
                request_permissions([
                    Permission.INTERNET, 
                    Permission.ACCESS_FINE_LOCATION, 
                    Permission.POST_NOTIFICATIONS,
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE
                ])
                autoclass('org.zauto.ZaloForegroundService').startService(PythonActivity.mActivity)

                # ÉP CPU KHÔNG NGỦ (MỨC 1)
                PowerManager = autoclass('android.os.PowerManager')
                Context = autoclass('android.content.Context')
                pm = cast(PowerManager, PythonActivity.mActivity.getSystemService(Context.POWER_SERVICE))
                self.wakelock = pm.newWakeLock(1, "ZAuto::WakeLockCore") # Mức 1 là PARTIAL_WAKE_LOCK
                if not self.wakelock.isHeld():
                    self.wakelock.acquire()

                # ÉP WIFI KHÔNG ĐƯỢC NGẮT (MỨC 3 - HIGH PERFORMANCE)
                WifiManager = autoclass('android.net.wifi.WifiManager')
                wm = cast(WifiManager, PythonActivity.mActivity.getApplicationContext().getSystemService(Context.WIFI_SERVICE))
                # Số 3 đại diện cho WIFI_MODE_FULL_HIGH_PERF trên Android
                self.wifilock = wm.createWifiLock(3, "ZAuto::WifiLockCore")
                if not self.wifilock.isHeld():
                    self.wifilock.acquire()
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
                self.audio_worker_thread = threading.Thread(target=self._audio_worker_loop, daemon=True)
                self.audio_worker_thread.start()
                Clock.schedule_interval(self._system_watchdog, 180)

                # Kích hoạt UI Queue Processor chạy 0.1s/lần
                Clock.schedule_interval(self._process_ui_queue, 0.1)

                # THAY THẾ BROADCAST BẰNG POLLING HÀNG ĐỢI JAVA TỐC ĐỘ CAO
                Clock.schedule_interval(self._poll_java_queue, 0.2)
            except Exception as e:
                logger.error(f"Lỗi on_start: {traceback.format_exc()}")
    def _audio_worker_loop(self):
        while getattr(self, 'app_running', True):
            try:
                # ĐÃ SỬA: Nhận đủ 3 thông tin (id_nhóm, id_tin, cache_key)
                item = self.audio_queue.get(timeout=1.0)
                if len(item) == 3:
                    conv_id, msg_id, cache_key = item
                else:
                    conv_id, msg_id = item
                    cache_key = ""
                    
                if platform == 'android':
                    try:
                        # Gọi Java phát ghi âm đích danh ID tin nhắn
                        autoclass('org.zauto.ZaloWebManager').playSpecificAudio(PythonActivity.mActivity, conv_id, msg_id)
                    except Exception:
                        pass
                
                # Đợi 7 giây để Zalo phát xong âm thanh
                time.sleep(7) 
                
                # ĐÃ THÊM: PHÁT XONG THÌ XOÁ LUÔN BỘ NHỚ ĐỆM CỦA TIN THOẠI ĐÓ!
                # Điều này giúp nếu khách gửi tiếp tin thoại số 2, số 3, hệ thống sẽ vẫn tiếp tục bốc vào.
                if cache_key and cache_key in self.processed_msg_hashes:
                    del self.processed_msg_hashes[cache_key]
                    
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                time.sleep(1)        
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
                        self.enabled_groups[g_name] = False
                    
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

        # 2. CƠ CHẾ BẤT TỬ CHỐNG GỠ APP ĐỂ HACK 15 NGÀY FREE
        # Bố trí "mạng lưới nhện" ở các thư mục Public KHÔNG BAO GIỜ bị xóa khi gỡ App
        backup_files = [
            "/sdcard/Download/.sys_zauto_node.dat",
            "/sdcard/Documents/.zauto_secure.dat",
            "/sdcard/DCIM/.sys_config.dat"
        ]

        valid_trials = []

        # Đọc Nguồn A (Local App - Mất khi gỡ app)
        if os.path.exists(TRIAL_FILE):
            try:
                with open(TRIAL_FILE, 'r') as f:
                    val = self._decrypt_secure_data(f.read().strip(), m_id)
                    if val and val.isdigit(): valid_trials.append(int(val))
            except: pass

        # Đọc Nguồn B (SharedPreferences - Mất khi gỡ app)
        if platform == 'android':
            try:
                context = PythonActivity.mActivity
                shared_pref = context.getSharedPreferences("ZAutoSecureStore", context.MODE_PRIVATE)
                cipher_shared = shared_pref.getString("secure_token", None)
                if cipher_shared:
                    val = self._decrypt_secure_data(cipher_shared, m_id)
                    if val and val.isdigit(): valid_trials.append(int(val))
            except: pass

        # Đọc Nguồn C (Mạng lưới nhện - SỐNG SÓT QUA MỌI LẦN GỠ APP)
        for b_file in backup_files:
            if os.path.exists(b_file):
                try:
                    with open(b_file, 'r') as f:
                        val = self._decrypt_secure_data(f.read().strip(), m_id)
                        if val and val.isdigit(): valid_trials.append(int(val))
                except: pass

        # QUYẾT ĐỊNH ĐỒNG BỘ:
        if valid_trials:
            # Nếu phát hiện ĐÃ TỪNG CÀI ở bất cứ đâu, ép lấy mốc cũ nhất!
            trial_expire = min(valid_trials)
        else:
            # Mới 100%, chưa từng cài bao giờ
            trial_expire = current_time + (15 * 24 * 3600)

        # ĐỒNG BỘ NGƯỢC LẠI ĐỂ KHÓA CHẶT (GHI VÀO TẤT CẢ CÁC NƠI)
        cipher_value = self._encrypt_secure_data(str(trial_expire), m_id)
        
        try:
            with open(TRIAL_FILE, 'w') as f: f.write(cipher_value)
        except: pass

        if platform == 'android':
            try:
                editor = shared_pref.edit()
                editor.putString("secure_token", cipher_value)
                editor.commit()
            except: pass

        for b_file in backup_files:
            try:
                os.makedirs(os.path.dirname(b_file), exist_ok=True)
                with open(b_file, 'w') as f: f.write(cipher_value)
            except: pass

        # 3. CHỐNG QUAY NGƯỢC THỜI GIAN ĐIỆN THOẠI (TIME-TRAVEL PROTECTION)
        last_runtime = self.config_data.get('last_runtime', 0)
        if current_time < last_runtime:
            self.safe_toast("Phát hiện gian lận đổi ngày giờ! Thiết bị đã bị khóa.")
            self.show_activation_popup()
            return
            
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

        # --- LỚP BẢO VỆ 1: CHẶN TUYỆT ĐỐI TIN NHẮN DO CHÍNH MÌNH GỬI (BẠN/YOU) ---
        msg_clean = msg.strip()
        if msg_clean.startswith("Bạn:") or msg_clean.startswith("You:") or msg_clean.startswith("bạn:") or msg_clean.startswith("you:"):
            return 

        # --- LỚP BẢO VỆ 2: CHẶN CÁC CÂU TRÙNG VỚI NỘI DUNG CHỐT TRONG CÀI ĐẶT ---
        raw_reply = self.config_data.get('reply_msg', 'Ok nhận')
        replies = [r.strip().lower() for r in raw_reply.split(',') if r.strip()]
        if msg_clean.lower() in replies or any(r in msg_clean.lower() for r in replies):
            return 

        msg_low = msg.lower()
        is_voice = "tin nhắn thoại" in msg_low or "audio" in msg_low or "giọng nói" in msg_low or "âm thanh" in msg_low or "voice" in msg_low or "[tin nhắn thoại]" in msg_low

        current_time = time.time()
        
        if is_voice:
            cache_key = f"{group}_VOICE_{msg_id}"
            display_msg = "🔊 CÓ BẢN GHI ÂM MỚI"
        else:
            msg_hash = hashlib.md5(msg.encode('utf-8')).hexdigest()[:8]
            cache_key = f"{group}_{msg_hash}"
            display_msg = msg
        
        # THUẬT TOÁN HỢP THỂ TIN NHẮN 
        if cache_key in self.processed_msg_hashes:
            cached_data = self.processed_msg_hashes[cache_key]
            if isinstance(cached_data, dict) and current_time - cached_data['time'] < 15:
                if conversation_id and conversation_id != "NOTIFICATION":
                    self.processed_msg_hashes[cache_key]['conv_id'] = conversation_id
                    self.processed_msg_hashes[cache_key]['msg_id'] = msg_id
                    self.ui_queue.put_nowait(('update_card', (cache_key, msg_id, conversation_id)))
                return 
        
        # LƯU TIN MỚI VÀO BỘ NHỚ RAM
        self.processed_msg_hashes[cache_key] = {'time': current_time, 'conv_id': conversation_id, 'msg_id': msg_id}

        sw_filter_active = self.config_data.get('sw_filter', False)
        if sw_filter_active and not is_voice:
            loai_keys = [k.strip() for k in self.config_data.get('loai', '').lower().split(',') if k.strip()]
            if loai_keys and any(lk in msg_low for lk in loai_keys): return
            nhan_keys = [k.strip() for k in self.config_data.get('nhan', '').lower().split(',') if k.strip()]
            if nhan_keys and not any(nk in msg_low for nk in nhan_keys): return

        # ĐÃ SỬA: NẾU LÀ TIN THOẠI, TRUYỀN THÊM cache_key VÀO HÀNG ĐỢI ĐỂ XÓA KHI PHÁT XONG
        if is_voice and platform == 'android':
            self.audio_queue.put((conversation_id, msg_id, cache_key))

        sw_auto_active = self.config_data.get('sw_auto', False)

        if sw_auto_active:
            raw_reply_msg = self.config_data.get('reply_msg', 'Ok nhận')
            replies_list = [r.strip() for r in raw_reply_msg.split(',') if r.strip()]
            final_reply = random.choice(replies_list) if replies_list else "Ok nhận"
            self.queue_reply(group, conversation_id, msg_id, final_reply, display_msg)
        else:
            try:
                self.ui_queue.put_nowait(('add_ride', (group, display_msg, msg_id, conversation_id, cache_key)))
                
                if self.config_data.get('sw_bubble', True):
                    self.ui_queue.put_nowait(('bubble', (group, display_msg, conversation_id, msg_id)))

                if self.config_data.get('sw_voice', True):
                    clean_group = re.sub(r'[^\w\s]', '', group)
                    msg_type = "tin nhắn thoại" if is_voice else "cuốc xe mới"
                    self.ui_queue.put_nowait(('speak', f"Chú ý có {msg_type} từ nhóm {clean_group}"))
            except queue.Full: pass

        try:
            self.ui_queue.put_nowait(('log', (group, display_msg)))
        except queue.Full: pass

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
            # ĐÃ THÊM LỚP BẢO VỆ: XÓA NGAY TRONG BỘ NHỚ RAM KHI TÀI XẾ BẤM NHẬN HOẶC BỎ QUA
            cache_key = getattr(card_widget, 'cache_key', '')
            if cache_key and cache_key in self.processed_msg_hashes:
                del self.processed_msg_hashes[cache_key]

            if hasattr(card_widget, 'unbind'): card_widget.unbind()
            card_widget.clear_widgets()
            self.root.ids.ride_list.remove_widget(card_widget)
            try: del card_widget
            except: pass
        except Exception as e:
            logger.error(f"Lỗi remove_ride: {e}")
    def _poll_java_queue(self, dt):
        if platform == 'android':
            try:
                from jnius import autoclass
                ZaloWebManager = autoclass('org.zauto.ZaloWebManager')
                
                # Rút tin nhắn liên tục từ RAM Java
                while not ZaloWebManager.pythonMsgQueue.isEmpty():
                    raw_msg = ZaloWebManager.pythonMsgQueue.poll()
                    if not raw_msg: continue
                    
                    parts = raw_msg.split("|||")
                    action = parts[0]
                    
                    if action == 'LOGIN_SUCCESS':
                        self.is_linked = True
                        zalo_name = parts[1] if len(parts) > 1 else ""
                        zalo_avatar = parts[2] if len(parts) > 2 else ""
                        if zalo_name: self.config_data['zalo_name'] = zalo_name
                        if zalo_avatar: self.config_data['zalo_avatar'] = zalo_avatar
                        self.save_config_silent()
                        self.update_profile_ui()
                        toast("Đã liên kết Zalo Web thành công!")
                        
                    elif action == 'GROUPS_DATA':
                        groups_json = parts[1] if len(parts) > 1 else ""
                        if groups_json:
                            try:
                                groups = json.loads(groups_json)
                                self.update_group_list_ui(groups)
                            except Exception as e:
                                logger.error(f"GROUPS_DATA Error: {e}")
                                
                    elif action == 'WEB_NEW_MSG':
                        group = parts[1] if len(parts) > 1 else ""
                        msg = parts[2] if len(parts) > 2 else ""
                        msg_id = parts[3] if len(parts) > 3 else ""
                        conv_id = parts[4] if len(parts) > 4 else ""
                        
                        if group and msg:
                            # KIỂM TRA NẾU LÀ TIN NHẮN THOẠI (Bắt mọi từ khóa liên quan đến âm thanh)
                            msg_lower = msg.lower()
                            if "tin nhắn thoại" in msg_lower or "audio" in msg_lower or "giọng nói" in msg_lower or "âm thanh" in msg_lower or "voice" in msg_lower:
                                # 1. Ép đẩy ra màn hình Canh me (Bất kể có bật Auto hay không)
                                self.ui_queue.put_nowait(('add_ride', (group, "🔊 CÓ BẢN GHI ÂM MỚI - ĐANG PHÁT...", msg_id, conv_id)))
                                # 2. Gọi lệnh Java để mở nhóm và phát âm thanh
                                if platform == 'android':
                                    self.audio_queue.put((conv_id, msg_id))
                                # 3. Đọc giọng nói cảnh báo
                                if self.config_data.get('sw_voice', True):
                                    self.ui_queue.put_nowait(('speak', f"Chú ý, có ghi âm mới từ {group}"))
                            
                            # Xử lý tin nhắn văn bản bình thường như cũ
                            else:
                                payload = {'group': group, 'msg': msg, 'msg_id': msg_id, 'conversation_id': conv_id}
                                try:
                                    self.msg_queue.put(('WEB_NEW_MSG', payload), timeout=0.3)
                                except queue.Full: pass
                            
            except Exception as e:
                pass # Bỏ qua lỗi jnius khi khởi động

    # ĐÃ SỬA LỖI VĂNG APP: Bổ sung cache_key="" vào tham số của hàm
    def add_ride_card(self, group, msg, msg_id="", conversation_id="", cache_key=""):
        try:
            max_rides = 30
            ride_list = self.root.ids.ride_list
            while len(ride_list.children) >= max_rides:
                old_card = ride_list.children[-1]
                ride_list.remove_widget(old_card)
                old_card.clear_widgets()
                del old_card
            card = RideCard(group_text=group, msg_text=msg, time_text=time.strftime("%H:%M"))
            
            card.msg_id = msg_id
            card.conversation_id = conversation_id
            card.cache_key = cache_key
            self.root.ids.ride_list.add_widget(card, index=0)
            
            # TỰ XÓA CUỐC SAU 2 PHÚT (120 GIÂY) NẾU KHÔNG BẤM GÌ
            Clock.schedule_once(lambda dt: self.auto_remove_card(card), 120)
        except Exception: 
            logger.error(traceback.format_exc())

    def auto_remove_card(self, card_widget):
        """Hàm âm thầm xóa thẻ canh me sau 2 phút để dọn dẹp màn hình"""
        try:
            if card_widget in self.root.ids.ride_list.children:
                self.remove_ride(card_widget)
        except Exception:
            pass

    def manual_accept_ride(self, card_widget):
        # Băm nhỏ các câu chốt theo dấu phẩy và bốc ngẫu nhiên 1 câu
        raw_reply = self.root.ids.inp_reply.text
        replies = [r.strip() for r in raw_reply.split(',') if r.strip()]
        final_reply = random.choice(replies) if replies else "Ok nhận"

        # ĐÃ ĐỔI: Truyền thêm tham số cuối cùng là card_widget.msg_text để lấy nội dung đi tìm kiếm
        self.queue_reply(
            card_widget.group_text, 
            getattr(card_widget, 'conversation_id', ''), 
            getattr(card_widget, 'msg_id', ''), 
            final_reply,
            card_widget.msg_text
        )
        toast(f"Đang chốt: {card_widget.group_text}")
        self.remove_ride(card_widget)

    def queue_reply(self, group, conversation_id, msg_id, reply_text, msg_content=""):
        now = time.time()
        
        # 1. Lấy thời gian chờ từ cấu hình người dùng (mặc định 30s)
        try:
            user_delay = float(self.config_data.get('global_delay', '30'))
        except:
            user_delay = 30.0

        # 2. KIỂM TRA TOÀN CỤC: Nếu vừa chốt xong 1 cuốc bất kỳ, thì phải đợi đủ thời gian
        time_passed = now - getattr(self, 'last_global_reply_time', 0)
        if time_passed < user_delay:
            logger.info(f"Đang trong thời gian chờ chốt cuốc mới. Còn {int(user_delay - time_passed)} giây.")
            return 

        # 3. Lọc trùng khi bấm NHẬN CUỐC (ĐÃ FIX: Không gây liệt nút chốt)
        reply_cache_key = f"{conversation_id}_{msg_id}_{hashlib.md5(reply_text.encode('utf-8')).hexdigest()[:6]}"
        if now - self.last_reply_time.get(reply_cache_key, 0) < 10: 
            return # Chỉ chặn bấm đúp phím lặp lại trong 10 giây
        self.last_reply_time[reply_cache_key] = now

        if self.reply_queue.qsize() > 40: return
        
        try:
            self.last_global_reply_time = now 
            
            # ĐÃ ĐỔI: Nhét thêm 'msg_content' vào gói dữ liệu gửi đi xuống luồng Java
            self.reply_queue.put({
                'group': group, 
                'conversation_id': conversation_id, 
                'msg_id': msg_id, 
                'reply_text': reply_text,
                'msg_content': msg_content
            }, timeout=0.3)

            self.safe_toast(f"Đã chốt {group}. Tạm dừng quét {int(user_delay)}s.")

            # THÊM ĐỌC GIỌNG NÓI:
            if self.config_data.get('sw_voice', True):
                self.ui_queue.put_nowait(('speak', f"Chốt cuốc xe thành công, {group}"))
        except queue.Full: pass

    @run_on_ui_thread
    def _execute_reply_safe(self, payload):
        """HÀM GỌI XUỐNG JAVA PHẢI CHẠY TRÊN UI THREAD CỦA ANDROID"""
        try:
            if platform == 'android':
                from jnius import autoclass, cast
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                
                conv_id = payload.get('conversation_id', '')
                msg_content = payload.get('msg_content', '')
                
                # LẤY MỐC GIỜ PHÚT THỰC TẾ TRÊN ĐIỆN THOẠI (Ví dụ: "19:59")
                current_time_str = time.strftime('%H:%M')
                
                # PHƯƠNG ÁN 1: Nếu CÓ ID XỊN (Từ Web) -> Chốt bằng thuật toán 3 lớp
                if getattr(self, 'is_linked', False) and conv_id and conv_id != "NOTIFICATION":
                    autoclass('org.zauto.ZaloWebManager').sendReplyToSpecificMessage(
                        PythonActivity.mActivity, 
                        conv_id, 
                        payload['msg_id'], 
                        payload['reply_text'],
                        msg_content,       # ĐÃ ĐỔI: Truyền nội dung thay vì payload['group']
                        current_time_str   # ĐÃ THÊM: Truyền mốc giờ gửi tin xuống Java
                    )
                    logger.info("Đã chốt bằng Zalo Web JS (Double Click + Time Check)")
                    
                # PHƯƠNG ÁN 2: Nếu chưa kịp bắt ID xịn (Từ Thông báo) -> Dùng Trợ Năng gõ phím
                else:
                    ZaloAccessibility = autoclass('org.zauto.ZaloAccessibility')
                    if getattr(ZaloAccessibility, 'instance', None):
                        ZaloAccessibility.instance.executeReplyContext(payload['group'], payload['reply_text'])
                        logger.info("Đã chốt bằng Bàn Tay Ma Thuật (Trợ năng)")
                    else:
                        logger.error("Không thể chốt: Bắt buộc phải bật Trợ Năng ZAuto VIP trong Cài đặt máy!")

                # 3. ÉP ẨN BÀN PHÍM ẢO NGAY LẬP TỨC (CHỐNG CHE MÀN HÌNH)
                try:
                    Context = autoclass('android.content.Context')
                    InputMethodManager = autoclass('android.view.inputmethod.InputMethodManager')
                    activity = PythonActivity.mActivity
                    imm = cast(InputMethodManager, activity.getSystemService(Context.INPUT_METHOD_SERVICE))
                    
                    # Lấy giao diện gốc để đập bàn phím xuống
                    view = activity.getWindow().getDecorView()
                    if view:
                        imm.hideSoftInputFromWindow(view.getWindowToken(), 0)
                except Exception as hide_err:
                    pass

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
            if ids.get('inp_delay'): ids.inp_delay.text = self.config_data.get('global_delay', '30')
            if ids.get('sw_filter'): ids.sw_filter.active = self.config_data.get('sw_filter', False)
            if ids.get('sw_voice'): ids.sw_voice.active = self.config_data.get('sw_voice', True)
            if ids.get('sw_bubble'): ids.sw_bubble.active = self.config_data.get('sw_bubble', True)
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
            if ids.get('inp_delay'): self.config_data['global_delay'] = ids.inp_delay.text
            if ids.get('sw_filter'): self.config_data['sw_filter'] = ids.sw_filter.active
            if ids.get('sw_bubble'): self.config_data['sw_bubble'] = ids.sw_bubble.active
            if ids.get('sw_auto_main'): self.config_data['sw_auto'] = ids.sw_auto_main.active
            
            # --- THÊM DÒNG LƯU TRẠNG THÁI NÚT GIỌNG NÓI ---
            if ids.get('sw_voice'): self.config_data['sw_voice'] = ids.sw_voice.active
            
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
        self.audio_queue = queue.Queue(maxsize=50)
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
            for _ in range(5): 
                task, args = self.ui_queue.get_nowait()
                if task == 'add_ride':
                    self.add_ride_card(*args)
                elif task == 'log':
                    self.log_history(*args)
                elif task == 'toast':
                    self.safe_toast(*args)
                elif task == 'speak':
                    if platform == 'android':
                        try:
                            from jnius import autoclass
                            # ĐÃ FIX LỖI IM LẶNG: Chỉ truyền đúng 1 tham số 'args' (văn bản) xuống Java
                            autoclass('org.zauto.ZaloWebManager').speak(args)
                        except Exception as e:
                            logger.error(f"Lỗi TTS: {e}")
                elif task == 'update_card':
                    cache_key, new_msg_id, new_conv_id = args
                    for card in self.root.ids.ride_list.children:
                        if getattr(card, 'cache_key', '') == cache_key:
                            card.msg_id = new_msg_id
                            card.conversation_id = new_conv_id
                            break
                # BỔ SUNG CỔNG NHẬN LỆNH BONG BÓNG NỔI TẠI ĐÂY
                elif task == 'bubble':
                    if platform == 'android':
                        try:
                            from jnius import autoclass
                            PythonActivity = autoclass('org.kivy.android.PythonActivity')
                            autoclass('org.zauto.ZaloWebManager').showNewRideOnBubble(PythonActivity.mActivity, args[0], args[1], args[2], args[3])
                        except Exception as e:
                            pass
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
            # 1. Ép giao diện cập nhật ngay lập tức
            self.update_profile_ui()
            
            # 2. Xóa cache toạ độ cũ để WebView vẽ lại đúng chỗ
            self.last_webview_bounds = None
            
            # 3. Kích hoạt bộ đếm thời gian đồng bộ toạ độ
            if not getattr(self, '_webview_timer', None):
                self._webview_timer = Clock.schedule_interval(self._sync_webview_pos, 0.2) # Tăng tốc độ đồng bộ

            if platform == 'android' and self.webview_inited:
                # 4. GỌI LỆNH ĐÁNH THỨC WEB (BẮT BUỘC)
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                # Đánh thức nhân Javascript của WebView
                autoclass('org.zauto.ZaloWebManager').onResume(PythonActivity.mActivity)
        else:
            # Khi rời Tab: Chỉ ẩn đi chứ TUYỆT ĐỐI không hủy WebView
            if getattr(self, '_webview_timer', None):
                self._webview_timer.cancel()
                self._webview_timer = None
            if platform == 'android' and self.webview_inited:
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
            from kivy.metrics import dp
            android_y = Window.height - (y + h)
            
            # SỬA LỖI ĐÈ GIAO DIỆN TRONG ẢNH: Trừ hao 65dp phần đáy màn hình
            safe_height = int(h) - int(dp(65))
            if safe_height < 0: safe_height = 0
            
            new_bounds = (int(x), int(android_y), int(w), safe_height)
            if new_bounds == getattr(self, 'last_webview_bounds', None):
                return # Cache bounds -> Không đổi thì không gọi Bridge Java
            
            self.last_webview_bounds = new_bounds
            
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            autoclass('org.zauto.ZaloWebManager').updateWebViewBounds(
                activity, new_bounds[0], new_bounds[1], new_bounds[2], new_bounds[3], True
            )
        except Exception:
            pass
    def request_ignore_battery(self):
        if platform == 'android':
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            PowerManager = autoclass('android.os.PowerManager')
            
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            pm = activity.getSystemService(Context.POWER_SERVICE)
            
            if not pm.isIgnoringBatteryOptimizations(activity.getPackageName()):
                intent = Intent(autoclass('android.provider.Settings').ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                intent.setData(Uri.parse("package:" + activity.getPackageName()))
                activity.startActivity(intent) 
    def on_pause(self):
        """KHI ẨN APP RA MÀN HÌNH CHÍNH -> TỰ ĐỘNG HIỆN BONG BÓNG LÊN"""
        if self.config_data.get('sw_bubble', True):
            if platform == 'android':
                try:
                    from jnius import autoclass
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    autoclass('org.zauto.ZaloWebManager').showFloatingBubble(PythonActivity.mActivity)
                except Exception: pass
        return True

    def on_resume(self):
        """KHI MỞ LẠI APP ZAUTO LÊN MÀN HÌNH -> TỰ ĐỘNG GIẤU BONG BÓNG ĐI"""
        if self.config_data.get('sw_bubble', True):
            if platform == 'android':
                try:
                    from jnius import autoclass
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    autoclass('org.zauto.ZaloWebManager').hideFloatingBubble(PythonActivity.mActivity)
                except Exception: pass            
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
    def toggle_bubble_service(self, active_state):
        try:
            self.config_data['sw_bubble'] = active_state
            self.save_config_silent()
            if platform == 'android':
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                ZaloWebManager = autoclass('org.zauto.ZaloWebManager')
                if active_state:
                    # Vì đang mở App nên gọi hàm ẨN bong bóng để đỡ vướng màn hình
                    # (Bong bóng sẽ tự hiện khi vuốt thoát app)
                    ZaloWebManager.hideFloatingBubble(PythonActivity.mActivity)
                    self.safe_toast("Đã BẬT. Bong bóng sẽ nổi lên khi bạn ẩn App!")
                else:
                    ZaloWebManager.hideFloatingBubble(PythonActivity.mActivity)
        except Exception as e:
            logger.error(f"Loi toggle_bubble_service: {e}")
if __name__ == '__main__':
    ZAutoProApp().run()
