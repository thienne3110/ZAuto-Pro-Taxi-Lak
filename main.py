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
                        on_release: app.show_zalo_web()

                ScrollView:
                    MDList:
                        id: msg_history_list

        # ================= TAB 3: TÀI KHOẢN ZALO (QUẢN LÝ KẾT NỐI) =================
        MDBottomNavigationItem:
            name: 'tab_zalo'
            text: 'Tài khoản'
            icon: 'account-circle'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Quản lý Zalo"
                    elevation: 1
                    md_bg_color: 1, 1, 1, 1
                    specific_text_color: 0.1, 0.1, 0.1, 1
                
                ScrollView:
                    MDBoxLayout:
                        orientation: 'vertical'
                        adaptive_height: True
                        padding: "20dp"
                        spacing: "20dp"

                        MDCard:
                            orientation: "vertical"
                            adaptive_height: True
                            padding: "20dp"
                            spacing: "15dp"
                            radius: [15, ]
                            md_bg_color: 1, 1, 1, 1
                            elevation: 2

                            MDBoxLayout:
                                orientation: "vertical"
                                spacing: "10dp"
                                adaptive_height: True
                                FitImage:
                                    id: zalo_avatar_view
                                    source: "profile.jpg"
                                    size_hint: None, None
                                    size: "100dp", "100dp"
                                    radius: [50, ]
                                    pos_hint: {"center_x": .5}
                                MDLabel:
                                    id: zalo_name_view
                                    text: "Chưa liên kết Zalo"
                                    font_style: "H6"
                                    bold: True
                                    halign: "center"
                            
                            MDSeparator:

                            MDLabel:
                                id: zalo_status_detail
                                text: "Vui lòng liên kết để bắt đầu nhận cuốc."
                                font_style: "Caption"
                                theme_text_color: "Secondary"
                                halign: "center"

                        MDRaisedButton:
                            id: btn_zalo_action
                            text: "LIÊN KẾT ZALO NGAY"
                            size_hint_x: 1
                            height: "50dp"
                            md_bg_color: 0.1, 0.5, 0.8, 1
                            on_release: app.handle_zalo_auth()

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
        """Đồng bộ trạng thái công tắc Auto Chốt giữa các Tab"""
        # 1. Cập nhật trạng thái cho công tắc ở Tab Canh me
        if self.root.ids.get('sw_auto_main'):
            self.root.ids.sw_auto_main.active = active_state
            
        # 2. Cập nhật trạng thái cho công tắc ở Tab Cài đặt
        if self.root.ids.get('sw_auto_settings'):
            self.root.ids.sw_auto_settings.active = active_state
            
        # 3. Lưu trạng thái vào bộ nhớ để lần sau mở app không phải bật lại
        self.save_config_silent()
        
        # Thông báo nhẹ cho người dùng biết
        if active_state:
            toast("Đã bật chế độ TỰ ĐỘNG chốt cuốc!")
        else:
            toast("Đã tắt chế độ tự động (Chuyển sang chốt tay)")
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
                # 1. Yêu cầu cấp quyền hệ thống
                request_permissions([Permission.INTERNET, Permission.ACCESS_FINE_LOCATION, Permission.POST_NOTIFICATIONS])
                
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

                # 5. Đăng ký bộ lắng nghe Broadcast 3 Action (Động cơ Web + Động cơ Accessibility)
                if not hasattr(self, 'receiver_started'):
                    self.br = BroadcastReceiver(self.on_broadcast_received, 
                        actions=[
                            'org.zauto.taxi.NEW_MSG',       # NGUỒN 1: Tin nhắn bắt từ màn hình (Accessibility)
                            'org.zauto.taxi.LOGIN_SUCCESS', # TÍN HIỆU: Đăng nhập Zalo Web thành công
                            'org.zauto.taxi.WEB_NEW_MSG'    # NGUỒN 2: Tin nhắn cào ngầm từ Zalo Web (Main)
                        ])
                    self.br.start()
                    self.receiver_started = True
                    
            except Exception:
                print(traceback.format_exc())
    def check_license_at_startup(self):
        m_id = get_machine_id()
        # Ưu tiên kiểm tra Key thật trước
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, 'r') as f:
                key = f.read().strip()
                ok, expiry = verify_license(key, m_id)
                if ok:
                    self.apply_license_ui(expiry)
                    return

        # Nếu không có key, kiểm tra Trial 15 ngày
        trial_expire = 0
        if not os.path.exists(TRIAL_FILE):
            trial_expire = int(time.time()) + (15 * 24 * 3600)
            with open(TRIAL_FILE, 'w') as f: f.write(str(trial_expire))
        else:
            with open(TRIAL_FILE, 'r') as f:
                content = f.read().strip()
                trial_expire = int(content) if content.isdigit() else 0

        if trial_expire > int(time.time()):
            self.apply_license_ui(trial_expire, is_trial=True)
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
            
            # Lấy thông tin Tên và Avatar từ Java gửi qua Broadcast
            zalo_name = intent.getStringExtra("zalo_name")
            zalo_avatar = intent.getStringExtra("zalo_avatar")
            
            if zalo_name: self.config_data['zalo_name'] = zalo_name
            if zalo_avatar: self.config_data['zalo_avatar'] = zalo_avatar
            
            self.save_config_silent()
            self.update_profile_ui() # Cập nhật hiển thị lên Tab Cài đặt ngay
            toast("Đã liên kết Zalo Web thành công!")
            return

        # --- 2. XỬ LÝ KHI CÓ TIN NHẮN MỚI (ACCESSIBILITY & WEB) ---
        if action in ['org.zauto.taxi.NEW_MSG', 'org.zauto.taxi.WEB_NEW_MSG']:
            
            # KIỂM TRA: Nếu chưa Bật Radar (Nút to màu xanh) thì không làm gì cả
            if not getattr(self, 'is_radar_running', False):
                return
                
            group = intent.getStringExtra("group")
            msg = intent.getStringExtra("msg")
            
            if group and msg:
                # Kiểm tra trùng lặp tin nhắn (Spam Control)
                msg_hash = str(hash(group + msg))
                if msg_hash in self.processed_msg_hashes: return
                self.processed_msg_hashes.add(msg_hash)
                if len(self.processed_msg_hashes) > 500: self.processed_msg_hashes.clear()
                
                # --- LOGIC LỌC TỪ KHÓA ---
                if self.root.ids.sw_filter.active:
                    msg_low = msg.lower()
                    
                    # Kiểm tra từ khóa LOẠI (Bỏ qua)
                    loai_keys = [k.strip() for k in self.root.ids.inp_loai.text.lower().split(',') if k.strip()]
                    if loai_keys and any(lk in msg_low for lk in loai_keys): 
                        return # Có từ khóa cấm -> Bỏ qua ngay
                    
                    # Kiểm tra từ khóa NHẬN (Ưu tiên)
                    nhan_keys = [k.strip() for k in self.root.ids.inp_nhan.text.lower().split(',') if k.strip()]
                    if nhan_keys and not any(nk in msg_low for nk in nhan_keys): 
                        return # Không chứa từ khóa cần tìm -> Bỏ qua

                # --- HIỂN THỊ LÊN MÀN HÌNH ---
                # Hiện thẻ cuốc ở tab Canh Me để tài xế có thể bấm nhận tay
                Clock.schedule_once(lambda dt: self.add_ride_card(group, msg))
                # Lưu vào lịch sử tin nhắn
                Clock.schedule_once(lambda dt: self.log_history(group, msg))

                # --- LOGIC TỰ ĐỘNG CHỐT (AUTO REPLY) ---
                # CHỈ tự động nhắn tin nếu công tắc "Auto chốt" (Nút nhỏ góc phải) đang BẬT
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
                
                # --- [LEVEL UP] ƯU TIÊN 1: BẮN TIN NGẦM QUA ZALO WEB ẨN ---
                # Không giật màn hình, tốc độ bằng mili-giây
                if self.is_linked: # Nếu đã quét QR
                    js_command = f"window.sendHiddenMessage('{reply_text}');"
                    autoclass('org.zauto.ZaloWebManager').executeJS(PythonActivity.mActivity, js_command)
                    return # Đã bắn qua Web thành công thì thoát luôn

                # --- [LEVEL UP] DỰ PHÒNG 2: DÙNG ACCESSIBILITY NATIVE ---
                # Nếu chưa login Web, dùng Trợ năng vuốt màn hình
                instance = autoclass('org.zauto.ZaloAccessibility').instance
                if instance:
                    instance.executeReplyContext(group, reply_text)
                else:
                    toast("LỖI: Chưa Link Web và Chưa Bật Trợ Năng!")
        except Exception: 
            print(traceback.format_exc())

    

    def load_config(self):
        """Nạp cấu hình từ file và cập nhật toàn bộ giao diện 4 Tab"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: 
                    self.config_data = json.load(f)
                
                # 1. Nạp trạng thái liên kết Zalo (Dùng cho Tab Tài khoản)
                self.is_linked = self.config_data.get('is_linked', False)
                
                # 2. Cập nhật các ô nhập liệu ở Tab Cài đặt
                # Dùng .get() để tránh lỗi nếu ID chưa tồn tại trong KV
                ids = self.root.ids
                if ids.get('inp_nhan'):
                    ids.inp_nhan.text = self.config_data.get('nhan', '')
                if ids.get('inp_loai'):
                    ids.inp_loai.text = self.config_data.get('loai', '')
                if ids.get('inp_reply'):
                    ids.inp_reply.text = self.config_data.get('reply_msg', 'Ok nhận')
                
                # 3. Nạp trạng thái Lọc từ khóa
                if ids.get('sw_filter'):
                    ids.sw_filter.active = self.config_data.get('sw_filter', False)

                # 4. ĐỒNG BỘ CÔNG TẮC AUTO CHỐT
                # Quan trọng: Khi gán 'active', Kivy sẽ tự động gọi hàm sync_auto_switch
                # giúp cái nút Radar ở Tab 1 cũng được cập nhật theo.
                is_auto = self.config_data.get('sw_auto', False)
                if ids.get('sw_auto_settings'):
                    ids.sw_auto_settings.active = is_auto
                
                # 5. Vẽ lại giao diện Zalo (Tên, Avatar) lên Tab Tài khoản
                # Hàm này sẽ dựa vào biến self.is_linked vừa nạp ở trên
                self.update_profile_ui()
                
            except Exception as e:
                print(f"Lỗi nạp cấu hình: {e}")
                # Nếu file lỗi, reset về mặc định để tránh treo App
                self.config_data = {
                    'nhan': '', 'loai': '', 'reply_msg': 'Ok nhận',
                    'sw_filter': False, 'sw_auto': False, 'is_linked': False
                }

    def save_config_silent(self):
        try:
            self.config_data.update({
                'nhan': self.root.ids.inp_nhan.text.lower(),
                'loai': self.root.ids.inp_loai.text.lower(),
                'reply_msg': self.root.ids.inp_reply.text,
                'sw_filter': self.root.ids.sw_filter.active,
                'sw_auto': self.root.ids.sw_auto_settings.active,
                'is_linked': self.is_linked # Lưu trạng thái để tắt app bật lại không mất
            })
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: 
                json.dump(self.config_data, f, ensure_ascii=False)
        except: pass
    def handle_zalo_auth(self):
        """Xử lý nút bấm thông minh: Nếu có rồi thì Hủy, chưa có thì Liên kết"""
        if self.is_linked:
            # Logic Hủy liên kết
            self.is_linked = False
            self.config_data['zalo_name'] = ""
            self.config_data['zalo_avatar'] = ""
            self.save_config_silent()
            self.update_profile_ui()
            toast("Đã hủy liên kết Zalo.")
        else:
            # Logic Mở web quét QR
            self.open_zalo_web_qr()
    def show_zalo_web(self):
        """Hàm gọi cửa sổ Zalo Web trôi lên màn hình để nhắn tin"""
        # 1. Kiểm tra xem khách đã quét mã QR chưa
        if not getattr(self, 'is_linked', False):
            toast("Bạn chưa liên kết Zalo! Hãy qua Tab Tài khoản quét QR trước.")
            # Tự động chuyển hướng sang tab Tài khoản (tab_zalo) để khách quét mã
            self.root.ids.bottom_nav.switch_tab('tab_zalo')
            return
            
        # 2. Nếu đã liên kết, gọi Java để bung cửa sổ Web
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                # Gọi lại hàm mở Webview (Lúc này đã có session nên sẽ vào thẳng khung chat)
                autoclass('org.zauto.ZaloWebManager').openZaloWebQR(PythonActivity.mActivity)
                toast("Bấm nút Trở Về (Back) để ĐÓNG khung chat!")
            except Exception: 
                import traceback
                print(traceback.format_exc())
                toast("Lỗi: Không thể mở khung chat!")
        else:
            # Thông báo khi test trên máy tính
            toast("Tính năng này chỉ hoạt động trên điện thoại Android")        

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

    def open_zalo_web_qr(self):
        if platform == 'android':
            try:
                autoclass('org.zauto.ZaloWebManager').openZaloWebQR(PythonActivity.mActivity)
            except Exception: print(traceback.format_exc())

    def on_stop(self):
        if platform == 'android':
            try:
                if hasattr(self, 'br'): self.br.stop()
                if hasattr(self, 'wakelock') and self.wakelock.isHeld(): self.wakelock.release()
            except: pass

if __name__ == '__main__':
    ZAutoProApp().run()
