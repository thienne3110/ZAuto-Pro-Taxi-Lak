import json, os, re, time, traceback
import hashlib # Dùng để băm SHA256 kiểm tra key
import uuid    # Dùng để lấy ID máy
import random
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
    height: "200dp"
    elevation: 3
    shadow_radius: 10
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
                
                # Header Bar
                MDBoxLayout:
                    size_hint_y: None
                    height: "60dp"
                    padding: ["20dp", "0dp", "20dp", "0dp"]
                    md_bg_color: 1, 1, 1, 1
                    elevation: 1
                    MDLabel:
                        id: lbl_counter
                        text: "RADAR VIP ĐANG QUÉT..."
                        font_style: "Subtitle2"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: 0.1, 0.5, 0.8, 1
                    MDBoxLayout:
                        orientation: "horizontal"
                        adaptive_width: True
                        spacing: "10dp"
                        MDLabel:
                            text: "Auto:"
                            font_style: "Subtitle2"
                            halign: "right"
                            valign: "center"
                        MDSwitch:
                            id: sw_auto_main
                            pos_hint: {'center_y': .5}
                            on_active: app.sync_auto_switch(self.active)
                
                # Banner cảnh báo
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

        # ================= TAB 2: LỊCH SỬ TIN NHẮN =================
        MDBottomNavigationItem:
            name: 'tab_tinnhan'
            text: 'Tin nhắn'
            icon: 'message-text-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Lịch sử tin nhắn"
                    elevation: 1
                    md_bg_color: 1, 1, 1, 1
                    specific_text_color: 0.1, 0.1, 0.1, 1
                    right_action_items: [["delete-sweep-outline", lambda x: app.clear_history()]]
                ScrollView:
                    MDList:
                        id: msg_history_list

        # ================= TAB 3: CÀI ĐẶT =================
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
                        spacing: "20dp"
                        
                        # --- THẺ PROFILE ---
                        MDCard:
                            size_hint: 1, None
                            height: "90dp"
                            padding: "15dp"
                            radius: [12, ]
                            elevation: 2
                            md_bg_color: 1, 1, 1, 1
                            MDBoxLayout:
                                orientation: 'horizontal'
                                spacing: "15dp"
                                FitImage:
                                    source: 'profile.jpg'
                                    size_hint: None, None
                                    size: "60dp", "60dp"
                                    radius: [30, ]
                                MDBoxLayout:
                                    orientation: 'vertical'
                                    MDLabel:
                                        text: "Vũ Văn Thành"
                                        font_style: "Subtitle1"
                                        bold: True
                                    MDLabel:
                                        text: "Taxi Huyện Lắk - ZAuto VIP"
                                        font_style: "Caption"
                                        theme_text_color: "Secondary"
                        
                        # --- CỤM NÚT KẾT NỐI & QUYỀN ---
                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            size_hint_y: None
                            height: "45dp"
                            MDRaisedButton:
                                text: "LIÊN KẾT ZALO"
                                icon: "qrcode-scan"
                                size_hint_x: 0.5
                                md_bg_color: 0.1, 0.6, 0.2, 1
                                on_release: app.open_zalo_web_qr()
                            MDRaisedButton:
                                text: "CẤP QUYỀN APP"
                                icon: "shield-check"
                                size_hint_x: 0.5
                                md_bg_color: 0.8, 0.4, 0.1, 1
                                on_release: app.check_permissions_and_guide()
                                
                        # --- CỤM CÔNG TẮC ĐIỀU KHIỂN ---
                        MDCard:
                            orientation: "vertical"
                            size_hint_y: None
                            height: "110dp"
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
                        
                        # --- CỤM TỪ KHÓA ---
                        MDCard:
                            orientation: "vertical"
                            size_hint_y: None
                            height: "220dp"
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
                        
                        # --- NÚT LƯU ---
                        MDRaisedButton:
                            text: "LƯU CẤU HÌNH HỆ THỐNG"
                            size_hint_x: 1
                            size_hint_y: None
                            height: "50dp"
                            md_bg_color: 0.1, 0.5, 0.8, 1
                            font_name: "Roboto-Bold"
                            elevation: 2
                            on_release: app.save_config()
                        # Thêm Card này vào đầu Tab Cài đặt
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
                        # Khoảng trống đáy
                        MDBoxLayout:
                            size_hint_y: None
                            height: "30dp"
'''
class ActivationPopup(Popup):
    def __init__(self, machine_id, on_success, can_cancel=False, **kwargs):
        super().__init__(**kwargs)
        self.title = "KÍCH HOẠT BẢN QUYỀN ZAUTO VIP"
        self.size_hint = (0.9, 0.8)
        self.auto_dismiss = can_cancel 
        self.on_success = on_success
        self.machine_id = machine_id

        # --- NỀN TRẮNG SẠCH SẼ ---
        self.background = ""  
        self.background_color = (1, 1, 1, 1) 
        self.title_color = (0, 0, 0, 1)      
        self.separator_color = (0.1, 0.5, 0.8, 1)

        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # --- 1. DẤU X MÀU ĐỎ GÓC PHẢI (CHỈ HIỆN KHI can_cancel=True) ---
        if can_cancel:
            header = BoxLayout(size_hint_y=None, height=35)
            header.add_widget(Label()) # Đẩy nút X sang sát lề phải
            btn_close = Button(
                text="X",
                size_hint=(None, None),
                size=(40, 35),
                bold=True,
                font_size='20sp',
                color=(1, 1, 1, 1),           # Chữ X Trắng
                background_normal='', 
                background_color=(0.8, 0, 0, 1) # Nền nút Đỏ
            )
            btn_close.bind(on_release=self.dismiss)
            header.add_widget(btn_close)
            main_layout.add_widget(header)

        # --- 2. NÚT BẤM COPY ĐƯỢC BÔI MÀU NỔI BẬT ---
        btn_copy = Button(
            text="CHẠM VÀO ĐÂY ĐỂ COPY ID MÁY", 
            size_hint_y=None, 
            height=45,
            bold=True,
            font_size='15sp',
            color=(1, 1, 1, 1),           # Chữ trắng
            background_normal='', 
            background_color=(0.1, 0.5, 0.8, 1) # Bôi nền xanh dương nổi bật
        )
        btn_copy.bind(on_release=self.copy_to_clipboard)
        main_layout.add_widget(btn_copy)
        
        # Ô chứa ID Máy (Nền xám nhạt, chữ đen dễ nhìn)
        self.id_box = TextInput(
            text=machine_id, 
            readonly=True, 
            size_hint_y=None, 
            height=45, 
            halign='center', 
            font_size='18sp',
            background_color=(0.95, 0.95, 0.95, 1),
            foreground_color=(0, 0, 0, 1)
        )
        main_layout.add_widget(self.id_box)
        
        # --- 3. PHẦN CHỌN GÓI VÀ NHẬP KEY ---
        main_layout.add_widget(Label(text="CHỌN LOẠI KEY MUỐN MUA:", color=(0.2, 0.2, 0.2, 1), font_size='14sp'))
        
        self.pkg_spin = Spinner(
            text='Chọn gói mua',
            values=('30 Ngày - 30K', '365 Ngày - 300K', 'VĨNH VIỄN - 600K'),
            size_hint_y=None, height=45,
            background_color=(0.1, 0.5, 0.8, 1),
            color=(1, 1, 1, 1)
        )
        main_layout.add_widget(self.pkg_spin)

        self.key_in = TextInput(
            hint_text="Dán mã Key đã mua vào đây...", 
            multiline=False, 
            size_hint_y=None, 
            height=45,
            halign='center',
            font_size='15sp'
        )
        main_layout.add_widget(self.key_in)

        main_layout.add_widget(Label(text=f"Liên hệ Zalo mua Key: {SUPPORT_PHONE}", font_size='13sp', color=(0.8, 0.2, 0.2, 1)))

        btn_active = Button(
            text="KÍCH HOẠT NGAY", 
            size_hint_y=None, 
            height=55, 
            background_normal='',
            background_color=(0, 0.5, 0, 1), 
            color=(1, 1, 1, 1),
            bold=True
        )
        btn_active.bind(on_release=self.validate)
        main_layout.add_widget(btn_active)

        self.content = main_layout

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
        
        # Xử lý khi đăng nhập thành công
        if action == 'org.zauto.taxi.LOGIN_SUCCESS':
            self.is_linked = True
            self.save_config_silent()
            toast("Đã liên kết Zalo Web thành công!")
            return

        # Xử lý khi có tin nhắn mới (Gộp chung cả Accessibility và Web ẩn)
        if action in ['org.zauto.taxi.NEW_MSG', 'org.zauto.taxi.WEB_NEW_MSG']:
            group = intent.getStringExtra("group")
            msg = intent.getStringExtra("msg")
            
            if group and msg:
                msg_hash = str(hash(group + msg))
                if msg_hash in self.processed_msg_hashes: return
                self.processed_msg_hashes.add(msg_hash)
                if len(self.processed_msg_hashes) > 500: self.processed_msg_hashes.clear()
                
                if self.root.ids.sw_filter.active:
                    msg_low = msg.lower()
                    loai_keys = [k.strip() for k in self.root.ids.inp_loai.text.lower().split(',') if k.strip()]
                    if loai_keys and any(lk in msg_low for lk in loai_keys): return
                    
                    nhan_keys = [k.strip() for k in self.root.ids.inp_nhan.text.lower().split(',') if k.strip()]
                    if nhan_keys and not any(nk in msg_low for nk in nhan_keys): return

                Clock.schedule_once(lambda dt: self.add_ride_card(group, msg))
                Clock.schedule_once(lambda dt: self.log_history(group, msg))

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
        self.execute_reply(card_widget.group_text, self.root.ids.inp_reply.text)
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

    def sync_auto_switch(self, active_state):
        self.root.ids.sw_auto_main.active = active_state
        self.root.ids.sw_auto_settings.active = active_state
        self.save_config_silent()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: 
                    self.config_data = json.load(f)
                self.root.ids.inp_nhan.text = self.config_data.get('nhan', '')
                self.root.ids.inp_loai.text = self.config_data.get('loai', '')
                self.root.ids.inp_reply.text = self.config_data.get('reply_msg', 'Ok nhận')
                
                is_auto = self.config_data.get('sw_auto', False)
                self.root.ids.sw_auto_main.active = is_auto
                self.root.ids.sw_auto_settings.active = is_auto
                self.root.ids.sw_filter.active = self.config_data.get('sw_filter', False)
                self.is_linked = self.config_data.get('is_linked', False) # Nạp lại trạng thái
            except: pass

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

    def clear_history(self):
        self.root.ids.msg_history_list.clear_widgets()
        toast("Đã dọn dẹp tin nhắn.")

    def check_permissions_and_guide(self):
        if platform == 'android':
            try:
                toast("Hãy tìm và Bật ứng dụng ZAuto VIP")
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
