import json
import os
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from kivymd.uix.list import OneLineRightIconListItem, TwoLineListItem, OneLineListItem
from kivy.properties import StringProperty, BooleanProperty

# ================= KẾT NỐI HỆ THỐNG ANDROID =================
if platform == 'android':
    CONFIG_FILE = '/data/data/org.zauto.taxi/files/config.json'
    HISTORY_FILE = '/data/data/org.zauto.taxi/files/history.json'
    
    from android.runnable import run_on_ui_thread
    from jnius import autoclass
    
    # Kéo các lệnh hệ thống của Android ra để đòi quyền
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Settings = autoclass('android.provider.Settings')
    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')

else:
    # Chạy trên máy tính Windows để test giao diện
    CONFIG_FILE = 'config.json'
    HISTORY_FILE = 'history.json'
    
    # Lệnh giả để Windows không bị văng lỗi
    def run_on_ui_thread(func):
        return func
# ============================================================

KV = '''
<GroupListItem>:
    text: root.group_name
    MDSwitch:
        pos_hint: {'center_y': .5, 'center_x': .9}
        active: root.is_active
        on_active: app.toggle_group(root.group_name, self.active)

MDScreen:
    md_bg_color: 0.95, 0.95, 0.95, 1

    MDBottomNavigation:
        panel_color: 1, 1, 1, 1
        selected_color_background: 0, 0, 1, .1
        text_color_active: 0.1, 0.4, 0.8, 1

        # ================= TAB 1: CANH ME =================
        MDBottomNavigationItem:
            name: 'tab_canhme'
            text: 'Canh me'
            icon: 'home-outline'
            MDBoxLayout:
                orientation: 'vertical'
                padding: "20dp"
                spacing: "20dp"
                MDLabel:
                    text: "ZAUTO PRO - TAXI LẮK"
                    halign: "center"
                    font_style: "H5"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: 0.1, 0.4, 0.8, 1
                MDIconButton:
                    id: status_icon
                    icon: "shield-check-outline"
                    icon_size: "100sp"
                    pos_hint: {"center_x": .5}
                    theme_text_color: "Custom"
                    text_color: 0.5, 0.5, 0.5, 1
                MDLabel:
                    id: lbl_status
                    text: "Hệ thống: Đang chờ lệnh"
                    halign: "center"
                MDRaisedButton:
                    text: "KHỞI ĐỘNG RADAR NGẦM"
                    pos_hint: {"center_x": .5}
                    size_hint_x: 0.8
                    height: "50dp"
                    on_release: app.start_zauto_service()

        # ================= TAB 2: TIN NHẮN =================
        MDBottomNavigationItem:
            name: 'tab_tinnhan'
            text: 'Tin nhắn'
            icon: 'message-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Nhật ký quét"
                    elevation: 0
                    right_action_items: [["delete-sweep", lambda x: app.clear_history()]]
                ScrollView:
                    MDList:
                        id: msg_history_list

        # ================= TAB 3: CÀI ĐẶT (ĐÃ CHUẨN HÓA FULL) =================
        MDBottomNavigationItem:
            name: 'tab_caidat'
            text: 'Cài đặt'
            icon: 'cog-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Cấu hình thuật toán"
                    elevation: 0
                ScrollView:
                    MDBoxLayout:
                        orientation: 'vertical'
                        adaptive_height: True
                        padding: "15dp"
                        spacing: "15dp"
                        
                        MDTextField:
                            id: inp_reply
                            hint_text: "Nội dung trả lời tự động"
                            mode: "rectangle"
                        MDTextField:
                            id: inp_nhan
                            hint_text: "Từ khóa NHẬN (cách nhau dấu phẩy)"
                            mode: "rectangle"
                        MDTextField:
                            id: inp_loai
                            hint_text: "Từ khóa LOẠI TRỪ (cách nhau dấu phẩy)"
                            mode: "rectangle"
                        
                        MDRaisedButton:
                            text: "LƯU CẤU HÌNH"
                            pos_hint: {"center_x": .5}
                            on_release: app.save_config()
                        
                        MDSeparator:
                        
                        MDLabel:
                            text: "Danh sách nhóm Zalo (Radar tự tìm)"
                            bold: True
                            font_style: "Subtitle1"
                        
                        MDList:
                            id: group_list

        # ================= TAB 4: THÔNG BÁO =================
        MDBottomNavigationItem:
            name: 'tab_thongbao'
            text: 'Thông báo'
            icon: 'bell-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Cuốc đã chốt"
                    elevation: 0
                ScrollView:
                    MDList:
                        id: catch_history_list

        # ================= TAB 5: TÀI KHOẢN =================
        MDBottomNavigationItem:
            name: 'tab_taikhoan'
            text: 'Tài khoản'
            icon: 'account-outline'
            MDBoxLayout:
                orientation: 'vertical'
                padding: "10dp"
                spacing: "10dp"
                MDCard:
                    orientation: 'vertical'
                    size_hint: 1, None
                    height: "220dp"
                    padding: "15dp"
                    radius: [15, ]
                    FitImage:
                        source: 'profile.jpg'
                        size_hint: None, None
                        size: "100dp", "100dp"
                        radius: [50, ]
                        pos_hint: {"center_x": .5}
                    MDLabel:
                        text: "Vũ Văn Thành"
                        halign: "center"
                        font_style: "H6"
                        bold: True
                    MDLabel:
                        text: "Taxi Huyện Lắk"
                        halign: "center"
                        theme_text_color: "Secondary"
                
                MDRaisedButton:
                    text: "LIÊN KẾT ZALO WEB (QUÉT QR)"
                    md_bg_color: 0, 0.5, 0, 1
                    pos_hint: {"center_x": .5}
                    on_release: app.open_zalo_web_qr()
                
                MDLabel:
                    text: "Nhật ký hệ thống (Logs):"
                    bold: True
                    font_style: "Caption"
                ScrollView:
                    md_bg_color: 0, 0, 0, 0.05
                    MDList:
                        id: log_list
'''

class GroupListItem(OneLineRightIconListItem):
    group_name = StringProperty()
    is_active = BooleanProperty(False)

class ZAutoProApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.config_data = {'nhan': '', 'loai': '', 'reply_msg': 'Ok nhận', 'groups': {}}
        self.root = Builder.load_string(KV)
        self.load_config()
        Clock.schedule_interval(self.auto_refresh_ui, 3.0)
        self.add_log("Giao diện khởi động thành công")
        return self.root

    def add_log(self, text):
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M:%S")
        self.root.ids.log_list.add_widget(OneLineListItem(text=f"[{time_str}] {text}"), index=0)

    @run_on_ui_thread
    def _open_native_webview(self):
        try:
            from jnius import autoclass
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            Activity = autoclass('org.kivy.android.PythonActivity').mActivity
            LayoutParams = autoclass('android.view.ViewGroup$LayoutParams')
            
            webview = WebView(Activity)
            settings = webview.getSettings()
            settings.setJavaScriptEnabled(True)
            settings.setDomStorageEnabled(True)
            # Lừa Zalo web rằng đang mở bằng máy tính
            settings.setUserAgentString("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")
            webview.setWebViewClient(WebViewClient())
            webview.loadUrl("https://chat.zalo.me")
            
            Activity.addContentView(webview, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        except Exception as e:
            self.add_log(f"Lỗi WebView: {str(e)}")

    def open_zalo_web_qr(self):
        if platform == 'android':
            self.add_log("Đang mở Zalo Web, vui lòng quét QR...")
            self._open_native_webview()
        else:
            self.add_log("Chức năng quét QR chỉ hoạt động trên Android")

    def auto_refresh_ui(self, dt):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    new_data = json.load(f)
                # Cập nhật danh sách nhóm nếu có nhóm mới
                if len(new_data.get('groups', {})) != len(self.config_data.get('groups', {})):
                    self.config_data = new_data
                    self.refresh_group_list()
                    self.add_log("Radar đã tìm thấy nhóm mới!")

                # Cập nhật tin nhắn vào Tab 2
                if os.path.exists(HISTORY_FILE):
                    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                    self.root.ids.msg_history_list.clear_widgets()
                    for item in reversed(history[-15:]):
                        self.root.ids.msg_history_list.add_widget(
                            TwoLineListItem(text=item['group'], secondary_text=item['msg'])
                        )
            except Exception: pass

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config_data = json.load(f)
                self.root.ids.inp_nhan.text = self.config_data.get('nhan', '')
                self.root.ids.inp_loai.text = self.config_data.get('loai', '')
                self.root.ids.inp_reply.text = self.config_data.get('reply_msg', 'Ok nhận')
                self.refresh_group_list()
            except Exception: pass

    def refresh_group_list(self):
        self.root.ids.group_list.clear_widgets()
        for g_name, is_on in self.config_data.get('groups', {}).items():
            self.root.ids.group_list.add_widget(GroupListItem(group_name=g_name, is_active=is_on))

    def toggle_group(self, group_name, is_active):
        self.config_data['groups'][group_name] = is_active
        self.save_to_disk()
        self.add_log(f"{'Bật' if is_active else 'Tắt'} quét: {group_name}")

    def save_config(self):
        self.config_data['nhan'] = self.root.ids.inp_nhan.text.lower()
        self.config_data['loai'] = self.root.ids.inp_loai.text.lower()
        self.config_data['reply_msg'] = self.root.ids.inp_reply.text
        self.save_to_disk()
        self.add_log("Đã lưu cấu hình thuật toán!")

    def save_to_disk(self):
        try:
            with open(CONFIG_FILE, 'w') as f: 
                json.dump(self.config_data, f)
        except Exception: pass

    def clear_history(self):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        self.root.ids.msg_history_list.clear_widgets()
        self.add_log("Đã xóa sạch nhật ký tin nhắn")

    def start_zauto_service(self):
        self.root.ids.lbl_status.text = "Hệ thống: ĐANG CHẠY NGẦM"
        self.root.ids.status_icon.text_color = (0, 0.7, 0, 1)
        self.add_log("Bắt đầu kích hoạt Service...")
        if platform == 'android':
            try:
                from jnius import autoclass
                service = autoclass('org.zauto.taxi.ServiceZaloservice')
                mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
                service.start(mActivity, '')
                self.add_log("Đã bật Service thành công!")
            except Exception as e:
                self.add_log(f"Lỗi khởi động Service: {str(e)}")

    def on_start(self):
        # Chờ 1 giây cho load giao diện xong mới bật popup xin quyền
        Clock.schedule_once(self.check_permissions_and_guide, 1)

    def check_permissions_and_guide(self, dt):
        if platform != 'android': return

        activity = PythonActivity.mActivity
        package_name = activity.getPackageName()
        
        # BƯỚC 1: KIỂM TRA QUYỀN ĐỌC THÔNG BÁO (Cho ZAuto)
        enabled_listeners = Settings.Secure.getString(
            activity.getContentResolver(), 
            "enabled_notification_listeners"
        )
        if package_name not in (enabled_listeners or ""):
            self.add_log("Bước 1: Vui lòng cấp quyền Truy cập thông báo!")
            intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            activity.startActivity(intent)
            return # Dừng lại chờ anh bật xong

        # BƯỚC 2: KIỂM TRA QUYỀN PIN CHỐNG NGỦ ĐÔNG (Cho ZAuto)
        from jnius import cast
        PowerManager = autoclass('android.os.PowerManager')
        power_manager = cast(PowerManager, activity.getSystemService(autoclass('android.content.Context').POWER_SERVICE))
        
        if not power_manager.isIgnoringBatteryOptimizations(package_name):
            self.add_log("Bước 2: Vui lòng cho phép ZAuto chạy ngầm!")
            intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
            intent.setData(Uri.parse(f"package:{package_name}"))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            activity.startActivity(intent)
            return # Dừng lại chờ anh bật xong

        # BƯỚC 3: ÉP DẪN VÀO CÀI ĐẶT CỦA ZALO GỐC (Chỉ làm 1 lần lúc mới cài)
        if not self.config_data.get('zalo_checked', False):
            self.add_log("Bước 3: Đang mở Cài đặt Zalo. HÃY BẬT THÔNG BÁO!")
            zalo_pkg = "com.zing.zalo"
            try:
                # Lệnh bế thẳng người dùng vào phần App Info (Thông tin ứng dụng) của Zalo
                intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                intent.setData(Uri.parse(f"package:{zalo_pkg}"))
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)
                
                # Đánh dấu là đã dẫn đi kiểm tra để lần sau mở app không bị làm phiền nữa
                self.config_data['zalo_checked'] = True
                self.save_to_disk()
            except Exception:
                self.add_log("Không tìm thấy app Zalo trên máy này!")    

if __name__ == '__main__':
    ZAutoProApp().run()
