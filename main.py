import json, os, re, time, traceback
import hashlib # Dùng để băm SHA256 kiểm tra key
import uuid    # Dùng để lấy ID máy
import random
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
# Thêm các thành phần giao diện của Kivy
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
from kivymd.uix.card import MDCard
from kivymd.uix.list import TwoLineAvatarIconListItem, ImageLeftWidget
from kivy.properties import StringProperty, BooleanProperty
from kivymd.toast import toast

if platform == 'android':
    BASE_PATH = '/data/data/org.zauto.taxi/files/'
    from android.runnable import run_on_ui_thread
    from jnius import autoclass, cast
    from android.permissions import request_permissions, Permission
    from android.broadcast import BroadcastReceiver
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Settings = autoclass('android.provider.Settings')
    Intent = autoclass('android.content.Intent')
else:
    BASE_PATH = './'
    def run_on_ui_thread(func): return func

CONFIG_FILE = BASE_PATH + 'config.json'
HISTORY_FILE = BASE_PATH + 'history.json'
# --- CẤU HÌNH BẢN QUYỀN ---
SUPPORT_PHONE = "0838429999"
LICENSE_FILE = os.path.join(BASE_PATH, 'license.dat')
TRIAL_FILE = os.path.join(BASE_PATH, 'trial_check.dat')

# THÊM DÒNG NÀY: Giấu file vào thư mục Download (Chống gỡ App)
BACKUP_TRIAL_FILE = '/storage/emulated/0/Download/.sys_zauto_cache.dat'

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
                
                # BỎ NÚT MỞ KHUNG CHAT CŨ THEO YÊU CẦU CỦA BẠN

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
            # Lắng nghe sự kiện chuyển tab để điều khiển WebView
            on_tab_press: app.on_zalo_tab_active(True) 
            
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Quản lý Zalo"
                    elevation: 1
                    md_bg_color: 1, 1, 1, 1
                    specific_text_color: 0.1, 0.1, 0.1, 1
                
                MDBoxLayout:
                    orientation: 'vertical'
                    padding: "10dp"
                    spacing: "10dp"

                    # 1. THẺ THÔNG TIN TÀI KHOẢN GỐC (Thiết kế lại 2 tầng chuẩn Mobile)
                    MDCard:
                        orientation: "vertical"  # Chuyển thành bố cục dọc
                        adaptive_height: True    # Tự động co giãn theo nội dung
                        padding: "15dp"
                        spacing: "15dp"
                        radius: [12, ]
                        md_bg_color: 1, 1, 1, 1
                        elevation: 1
                        
                        MDBoxLayout:
                            orientation: "horizontal"
                            adaptive_height: True
                            spacing: "15dp"
                            
                            FitImage:
                                id: zalo_avatar_view
                                source: "profile.jpg"
                                size_hint: None, None
                                size: "50dp", "50dp"
                                radius: [25, ]
                                pos_hint: {"center_y": .5}
                                
                            MDBoxLayout:
                                orientation: "vertical"
                                adaptive_height: True
                                pos_hint: {"center_y": .5}
                                MDLabel:
                                    id: zalo_name_view
                                    text: "Chưa kết nối Zalo"
                                    font_style: "Subtitle1"
                                    bold: True
                                    adaptive_height: True
                                MDLabel:
                                    id: zalo_status_detail
                                    text: "Quét QR bên dưới để kết nối"
                                    font_style: "Caption"
                                    theme_text_color: "Secondary"
                                    adaptive_height: True
                                    
                        MDRaisedButton:
                            id: btn_zalo_action
                            text: "LIÊN KẾT ZALO NGAY"
                            size_hint_x: 1  # Trải dài nút bấm ra 100% bề ngang
                            height: "45dp"
                            md_bg_color: 0.1, 0.5, 0.8, 1
                            on_release: app.handle_zalo_auth()

                    # 2. KHUNG ĐỊNH VỊ WEBVIEW (Quan trọng nhất)
                    # Widget này sẽ đóng vai trò xác định vị trí và kích thước để đặt WebView Zalo Web đè lên.
                    Widget:
                        id: webview_placeholder
                        size_hint: 1, 1

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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_radar_running = False # Mặc định mở app lên là TẮT
        self.enabled_groups = {} # Lưu trạng thái bật/tắt của từng nhóm
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
        self.load_config()
        return self.root

    def on_start(self):
        self.check_license_at_startup()
        if platform == 'android':
            try:
                # 1. Yêu cầu cấp quyền hệ thống (Đã thêm quyền Đọc/Ghi Bộ Nhớ)
                request_permissions([
                    Permission.INTERNET, 
                    Permission.ACCESS_FINE_LOCATION, 
                    Permission.POST_NOTIFICATIONS,
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE
                ])
                
                # 2. Khởi động dịch vụ chạy ngầm chống Kill App (Android 12+)
                autoclass('org.zauto.ZaloForegroundService').startService(PythonActivity.mActivity)

                # 3. Kích hoạt WakeLock để giữ CPU chạy khi tắt màn hình
                PowerManager = autoclass('android.os.PowerManager')
                Context = autoclass('android.content.Context')
                pm = cast(PowerManager, PythonActivity.mActivity.getSystemService(Context.POWER_SERVICE))
                self.wakelock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ZAuto::WakeLock")
                if not self.wakelock.isHeld():
                    self.wakelock.acquire()

                # 4. Khởi tạo Cache chống bão tin nhắn & chống lặp (Spam Control)
                self.processed_msg_hashes = set()
                self.global_last_reply = 0
                self.last_reply_time = {}

                # 5. Đăng ký bộ lắng nghe Broadcast 3 Action (Động cơ Web)
                if not hasattr(self, 'receiver_started'):
                    self.br = BroadcastReceiver(self.on_broadcast_received, 
                            actions=[
                                'org.zauto.taxi.LOGIN_SUCCESS', 
                                'org.zauto.taxi.WEB_NEW_MSG',
                                'org.zauto.taxi.GROUPS_DATA'
                            ])
                    self.br.start()
                    self.receiver_started = True
                
                # 6. KHỞI TẠO WEBVIEW NHÚNG NGẦM (THÊM MỚI)
                # Dùng Clock để trễ 1 giây, đảm bảo giao diện Kivy đã load xong trước khi gọi Java
                Clock.schedule_once(lambda dt: self.init_embedded_webview(), 1)
                    
            except Exception:
                print(traceback.format_exc())

    def init_embedded_webview(self):
        """Khởi tạo WebView và load sẵn trang đăng nhập Zalo"""
        if platform != 'android':
            return
        try:
            ZaloWebManager = autoclass('org.zauto.ZaloWebManager')
            ZaloWebManager.initWebView(PythonActivity.mActivity)
        except Exception as e:
            print(f"Lỗi khởi tạo Embedded WebView: {e}")
            print(traceback.format_exc())

    def on_zalo_tab_active(self, is_active):
        """Hàm bật/tắt và cập nhật vị trí WebView khi chuyển đổi Tab"""
        if platform != 'android':
            return
            
        try:
            ZaloWebManager = autoclass('org.zauto.ZaloWebManager')
            if is_active:
                # Đợi giao diện Kivy render xong (0.1s) để lấy tọa độ chính xác nhất
                Clock.schedule_once(lambda dt: self.position_webview(), 0.1)
            else:
                # Khi người dùng vuốt sang Tab khác -> Ẩn ngay lập tức
                ZaloWebManager.hideWebView()
        except Exception as e:
            print(f"Lỗi điều khiển WebView Tab: {e}")

    def position_webview(self):
        """Tính toán tọa độ thực tế trên màn hình Android để đặt WebView đè lên đúng Placeholder"""
        if platform != 'android':
            return
            
        # NẾU CHƯA ĐĂNG NHẬP THÌ ẨN WEBVIEW, KHÔNG HIỆN LÊN TAB
        if not getattr(self, 'is_linked', False):
            try:
                from jnius import autoclass
                ZaloWebManager = autoclass('org.zauto.ZaloWebManager')
                ZaloWebManager.hideWebView()
            except: pass
            return

        try:
            placeholder = self.root.ids.webview_placeholder
            
            from jnius import autoclass
            Window = autoclass('android.view.Window')
            window = PythonActivity.mActivity.getWindow()
            decorView = window.getDecorView()
            screen_height = decorView.getHeight()

            from kivy.core.window import Window as KivyWindow
            scale = screen_height / KivyWindow.height 

            kx, ky = placeholder.to_window(*placeholder.pos)
            kw, kh = placeholder.size

            x = int(kx * scale)
            y = int((KivyWindow.height - ky - kh) * scale)
            w = int(kw * scale)
            h = int(kh * scale)

            ZaloWebManager = autoclass('org.zauto.ZaloWebManager')
            ZaloWebManager.showWebView(PythonActivity.mActivity, x, y, w, h)
        except Exception as e:
            print(f"Lỗi định vị WebView: {e}")
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
        
        # 1. Ưu tiên kiểm tra Key bản quyền (Key thật) trước
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, 'r') as f:
                key = f.read().strip()
                ok, expiry = verify_license(key, m_id)
                if ok:
                    self.apply_license_ui(expiry)
                    return

        # 2. Logic giấu file chống xóa App
        trial_expire = 0
        
        # BƯỚC A: Đọc từ file Backup (Nằm ngoài Download) trước, vì file này sống dai nhất
        if os.path.exists(BACKUP_TRIAL_FILE):
            try:
                with open(BACKUP_TRIAL_FILE, 'r') as f:
                    content = f.read().strip()
                    trial_expire = int(content) if content.isdigit() else 0
            except: pass
            
        # BƯỚC B: Nếu file Backup chưa có hoặc bị khách vô tình xóa, đọc tiếp file trong App (TRIAL_FILE)
        if trial_expire == 0 and os.path.exists(TRIAL_FILE):
            try:
                with open(TRIAL_FILE, 'r') as f:
                    content = f.read().strip()
                    trial_expire = int(content) if content.isdigit() else 0
            except: pass

        # 3. Nếu CẢ 2 FILE ĐỀU KHÔNG TỒN TẠI -> ĐÂY CHÍNH XÁC LÀ LẦN CÀI ĐẦU TIÊN
        if trial_expire == 0:
            # Tặng đúng 15 ngày (15 ngày * 24h * 3600 giây)
            trial_expire = int(time.time()) + (15 * 24 * 3600)
            toast("Tặng bạn 15 ngày dùng thử VIP hoàn toàn miễn phí!")
            
        # 4. Ghi đè/Cập nhật lại cả 2 file để "khóa" máy này lại
        try:
            # Ghi vào vùng an toàn của App
            with open(TRIAL_FILE, 'w') as f: 
                f.write(str(trial_expire))
        except: pass
        
        try:
            # Lén ghi 1 bản sao ra thư mục Download để phục phục kích hoạt lại nếu khách gỡ App
            if os.path.exists('/storage/emulated/0/Download/'):
                with open(BACKUP_TRIAL_FILE, 'w') as f: 
                    f.write(str(trial_expire))
        except: pass

        # 5. Kiểm tra hạn dùng thử
        if trial_expire > int(time.time()):
            self.apply_license_ui(trial_expire, is_trial=True)
            toast("Hệ thống đang chạy phiên bản Dùng Thử.")
        else:
            self.show_activation_popup()

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
    def on_broadcast_received(self, context, intent):
        action = intent.getAction()
        
        # --- 1. XỬ LÝ KHI ĐĂNG NHẬP ZALO WEB THÀNH CÔNG ---
        if action == 'org.zauto.taxi.LOGIN_SUCCESS':
            self.is_linked = True
            zalo_name = intent.getStringExtra("zalo_name")
            zalo_avatar = intent.getStringExtra("zalo_avatar")
            
            if zalo_name: self.config_data['zalo_name'] = zalo_name
            if zalo_avatar: self.config_data['zalo_avatar'] = zalo_avatar
            
            self.save_config_silent()
            self.update_profile_ui()
            
            # GỌI HÀM NÀY ĐỂ BUNG KHUNG CHAT ZALO VÀO TAB NGAY KHI POPUP ĐÓNG XONG
            Clock.schedule_once(lambda dt: self.position_webview(), 0.5)

            toast("Đã liên kết Zalo Web thành công!")
            return

        # --- 2. XỬ LÝ KHI NHẬN DANH SÁCH NHÓM TỪ WEB ---
        if action == 'org.zauto.taxi.GROUPS_DATA':
            try:
                import json
                groups_json = intent.getStringExtra("groups_list")
                if groups_json:
                    groups = json.loads(groups_json)
                    # Gọi hàm cập nhật giao diện danh sách nhóm ở Tab Nhóm
                    Clock.schedule_once(lambda dt: self.update_group_list_ui(groups))
            except Exception as e:
                print(f"Lỗi xử lý danh sách nhóm: {e}")
            return

        # --- 3. XỬ LÝ KHI CÓ TIN NHẮN MỚI (TRỢ NĂNG & WEB) ---
        if action in ['org.zauto.taxi.NEW_MSG', 'org.zauto.taxi.WEB_NEW_MSG']:
            
            # KIỂM TRA 1: Radar phải đang BẬT
            if not getattr(self, 'is_radar_running', False):
                return
                
            group = intent.getStringExtra("group")
            msg = intent.getStringExtra("msg")
            
            if group and msg:
                # KIỂM TRA 2: Lọc theo danh sách Nhóm (Tab Nhóm)
                # Nếu nhóm có trong danh sách và đang bị TẮT thì bỏ qua
                if group in getattr(self, 'enabled_groups', {}) and not self.enabled_groups[group]:
                    return

                # KIỂM TRA 3: Chống lặp tin nhắn (Spam Control)
                msg_hash = str(hash(group + msg))
                if msg_hash in self.processed_msg_hashes: 
                    return
                self.processed_msg_hashes.add(msg_hash)
                if len(self.processed_msg_hashes) > 500: 
                    self.processed_msg_hashes.clear()
                
                # KIỂM TRA 4: Logic lọc từ khóa (Tab Cài đặt)
                if self.root.ids.sw_filter.active:
                    msg_low = msg.lower()
                    
                    # Lọc từ khóa BỎ QUA (Loại)
                    loai_keys = [k.strip() for k in self.root.ids.inp_loai.text.lower().split(',') if k.strip()]
                    if loai_keys and any(lk in msg_low for lk in loai_keys): 
                        return
                    
                    # Lọc từ khóa NHẬN (Ưu tiên)
                    nhan_keys = [k.strip() for k in self.root.ids.inp_nhan.text.lower().split(',') if k.strip()]
                    if nhan_keys and not any(nk in msg_low for nk in nhan_keys): 
                        return

                # --- NẾU VƯỢT QUA HẾT CÁC BỘ LỌC -> HIỂN THỊ & CHỐT ---
                
                # Hiện thẻ cuốc ở tab Canh Me
                Clock.schedule_once(lambda dt: self.add_ride_card(group, msg))
                
                # Lưu vào lịch sử tin nhắn (Tab Tin nhắn)
                Clock.schedule_once(lambda dt: self.log_history(group, msg))

                # TỰ ĐỘNG CHỐT: Nếu công tắc "Tự động" đang BẬT
                if self.root.ids.sw_auto_main.active:
                    self.execute_reply(group, self.root.ids.inp_reply.text)

    def add_ride_card(self, group, msg):
        try:
            if len(self.root.ids.ride_list.children) >= 50:
                self.root.ids.ride_list.remove_widget(self.root.ids.ride_list.children[-1])
            
            card = RideCard(group_text=group, msg_text=msg, time_text=time.strftime("%H:%M"))
            self.root.ids.ride_list.add_widget(card, index=0)
        except Exception: print(traceback.format_exc())

    def log_history(self, group, msg):
        # Dùng List chuẩn Material của KivyMD
        item = TwoLineAvatarIconListItem(text=f"[{time.strftime('%H:%M')}] {group}", secondary_text=msg)
        item.add_widget(ImageLeftWidget(source="profile.jpg"))
        self.root.ids.msg_history_list.add_widget(item, index=0)

    def remove_ride(self, card_widget):
        self.root.ids.ride_list.remove_widget(card_widget)

    def manual_accept_ride(self, card_widget):
        """Hàm xử lý khi tài xế bấm nút NHẬN CUỐC NGAY bằng tay"""
        # 1. Bắn lệnh chốt cuốc ngay lập tức (Ưu tiên Web ẩn, dự phòng Trợ năng)
        self.execute_reply(card_widget.group_text, self.root.ids.inp_reply.text)
        
        # 2. Hiện thông báo nhanh để tài xế biết hệ thống đang xử lý
        toast(f"Đang chốt tay: {card_widget.group_text}")
        
        # 3. Xóa thẻ này khỏi danh sách Canh me sau khi nhận xong
        self.remove_ride(card_widget)

    def execute_reply(self, group, reply_text):
        try:
            now = time.time()
            if now - getattr(self, 'global_last_reply', 0) < 3: return
            self.global_last_reply = now
            if now - self.last_reply_time.get(group, 0) < 30: return
            self.last_reply_time[group] = now

            if platform == 'android':
                toast(f"Đang chốt cuốc thần tốc: {group}")
                
                # CHỈ CÒN DUY NHẤT 1 CÁCH CHỐT: QUA ZALO WEB ẨN (Tốc độ mili-giây)
                if getattr(self, 'is_linked', False): # Kiểm tra đã login Zalo Web chưa
                    js_command = f"window.sendHiddenMessage('{reply_text}');"
                    autoclass('org.zauto.ZaloWebManager').executeJS(PythonActivity.mActivity, js_command)
                else:
                    # Nếu tài xế bật Auto nhưng chưa quét QR
                    toast("LỖI: Vui lòng quét mã QR Zalo Web ở Tab Tài khoản trước!")
        except Exception: 
            print(traceback.format_exc())
    

    def load_config(self):
        """Nạp cấu hình từ file và cập nhật toàn bộ giao diện (Canh me, Nhóm, Tài khoản, Cài đặt)"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: 
                    self.config_data = json.load(f)
                
                # 1. NẠP TRẠNG THÁI LIÊN KẾT & DANH SÁCH NHÓM ĐÃ LƯU
                self.is_linked = self.config_data.get('is_linked', False)
                # Quan trọng: Nạp sổ cái các nhóm đã Bật/Tắt từ trước
                self.enabled_groups = self.config_data.get('enabled_groups', {})
                
                # 2. CẬP NHẬT CÁC Ô NHẬP LIỆU (TAB CÀI ĐẶT)
                ids = self.root.ids
                if ids.get('inp_nhan'):
                    ids.inp_nhan.text = self.config_data.get('nhan', '')
                if ids.get('inp_loai'):
                    ids.inp_loai.text = self.config_data.get('loai', '')
                if ids.get('inp_reply'):
                    ids.inp_reply.text = self.config_data.get('reply_msg', 'Ok nhận')
                
                # 3. NẠP TRẠNG THÁI LỌC TỪ KHÓA
                if ids.get('sw_filter'):
                    ids.sw_filter.active = self.config_data.get('sw_filter', False)

                # 4. ĐỒNG BỘ CÔNG TẮC AUTO CHỐT (ĐỒNG BỘ GIỮA TAB 1 VÀ TAB 4)
                # Khi gán lệnh này, hàm sync_auto_switch sẽ tự chạy để đổi màu nút Radar
                is_auto = self.config_data.get('sw_auto', False)
                if ids.get('sw_auto_settings'):
                    ids.sw_auto_settings.active = is_auto
                
                # 5. VẼ LẠI GIAO DIỆN TÀI KHOẢN (Tên Zalo, Ảnh đại diện)
                self.update_profile_ui()
                
                # 6. KHỞI TẠO LẠI DANH SÁCH NHÓM (Nếu đã có dữ liệu cũ)
                # Giúp Tab Nhóm hiện lại các nhóm cũ ngay cả khi chưa kịp quét từ Web
                if self.enabled_groups:
                    Clock.schedule_once(lambda dt: self.update_group_list_ui(self.enabled_groups.keys()))
                
            except Exception as e:
                print(f"Lỗi nạp cấu hình: {e}")
                # Reset về mặc định nếu file json bị lỗi cấu trúc
                self.config_data = {
                    'nhan': '', 'loai': '', 'reply_msg': 'Ok nhận',
                    'sw_filter': False, 'sw_auto': False, 'is_linked': False,
                    'enabled_groups': {}
                }
                self.enabled_groups = {}
    def save_config_silent(self):
        try:
            self.config_data.update({
                'nhan': self.root.ids.inp_nhan.text,
                'loai': self.root.ids.inp_loai.text,
                'reply_msg': self.root.ids.inp_reply.text,
                'sw_auto': self.root.ids.sw_auto_settings.active,
                'is_linked': self.is_linked,
                'enabled_groups': self.enabled_groups # THÊM DÒNG NÀY ĐỂ LƯU DANH SÁCH NHÓM
            })
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False)
        except: pass
    def handle_zalo_auth(self):
        """Xử lý nút bấm: Nếu đã liên kết thì Hủy, nếu chưa thì bật Popup quét QR"""
        if getattr(self, 'is_linked', False):
            self.is_linked = False
            self.config_data['zalo_name'] = ""
            self.config_data['zalo_avatar'] = ""
            self.save_config_silent()
            self.update_profile_ui()
            
            if platform == 'android':
                try:
                    from jnius import autoclass
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    ZaloWebManager = autoclass('org.zauto.ZaloWebManager')
                    ZaloWebManager.logoutAndClearData(PythonActivity.mActivity)
                except Exception as e:
                    print(f"Lỗi khi xóa session Zalo Web: {e}")
            
            toast("Đã đăng xuất và hủy liên kết Zalo Web.")
        else:
            # GỌI LẠI POPUP QUÉT QR TRÀN MÀN HÌNH NHƯ CŨ
            if platform == 'android':
                try:
                    from jnius import autoclass
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    ZaloWebManager = autoclass('org.zauto.ZaloWebManager')
                    ZaloWebManager.openZaloWebQR(PythonActivity.mActivity)
                except Exception as e:
                    print(f"Lỗi mở popup QR: {e}")
    

    def update_profile_ui(self):
        """Cập nhật thông tin Zalo - Thêm kiểm tra an toàn"""
        try:
            ids = self.root.ids
            # Nếu Python báo False nhưng thực tế file config có dữ liệu thì ép sang True
            if self.config_data.get('zalo_name') and not self.is_linked:
                self.is_linked = True

            if self.is_linked:
                ids.zalo_name_view.text = self.config_data.get('zalo_name', "Đã kết nối")
                ids.zalo_avatar_view.source = self.config_data.get('zalo_avatar', 'profile.jpg')
                ids.btn_zalo_action.text = "HUỶ LIÊN KẾT ZALO"
                ids.btn_zalo_action.md_bg_color = (0.8, 0.2, 0.2, 1)
            else:
                ids.zalo_name_view.text = "Chưa kết nối Zalo"
                ids.zalo_avatar_view.source = 'profile.jpg'
                ids.btn_zalo_action.text = "LIÊN KẾT ZALO NGAY"
                ids.btn_zalo_action.md_bg_color = (0.1, 0.5, 0.8, 1)
        except Exception as e:
            print(f"Lỗi UI: {e}")

    def save_config(self):
        """Hàm sửa lỗi văng App: Gọi khi khách bấm nút LƯU CẤU HÌNH"""
        self.save_config_silent()
        toast("Đã lưu cấu hình thành công!")    

    def clear_history(self):
        self.root.ids.msg_history_list.clear_widgets()
        toast("Đã dọn dẹp tin nhắn.")

    def check_permissions_and_guide(self):
        """Do sử dụng công nghệ Web ngầm VIP, app không còn cần xin quyền hệ thống rườm rà nữa."""
        toast("Hệ thống VIP chạy ngầm đã tự động tối ưu, không cần cấp thêm quyền!")

    

    def on_stop(self):
        if platform == 'android':
            try:
                if hasattr(self, 'br'): self.br.stop()
                if hasattr(self, 'wakelock') and self.wakelock.isHeld(): self.wakelock.release()
            except: pass

if __name__ == '__main__':
    ZAutoProApp().run()
