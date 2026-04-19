import json, os
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from kivymd.uix.list import OneLineRightIconListItem, TwoLineListItem, OneLineListItem
from kivy.properties import StringProperty, BooleanProperty

# Cấu hình đường dẫn file
if platform == 'android':
    CONFIG_FILE = '/data/data/org.zauto.taxi/files/config.json'
    HISTORY_FILE = '/data/data/org.zauto.taxi/files/history.json'
    MATCHES_FILE = '/data/data/org.zauto.taxi/files/matches.json'
    from android.runnable import run_on_ui_thread
    from jnius import autoclass, cast
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Settings = autoclass('android.provider.Settings')
    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')
else:
    CONFIG_FILE, HISTORY_FILE, MATCHES_FILE = 'config.json', 'history.json', 'matches.json'
    def run_on_ui_thread(func): return func

KV = '''
<GroupListItem>:
    text: root.group_name
    MDSwitch:
        pos_hint: {'center_y': .5, 'center_x': .9}
        active: root.is_active
        on_active: app.toggle_group(root.group_name, self.active)

MDScreen:
    MDBottomNavigation:
        panel_color: 1, 1, 1, 1
        text_color_active: 0.1, 0.4, 0.8, 1

        # TAB 1: CANH ME (RADAR)
        MDBottomNavigationItem:
            name: 'tab_canhme'
            text: 'Canh me'
            icon: 'home-outline'
            MDBoxLayout:
                orientation: 'vertical'
                padding: "20dp"
                MDLabel:
                    text: "ZAUTO PRO - TAXI LẮK"
                    halign: "center"
                    font_style: "H6"
                MDIconButton:
                    id: status_icon
                    icon: "shield-check-outline"
                    icon_size: "80sp"
                    pos_hint: {"center_x": .5}
                MDRaisedButton:
                    text: "KHỞI ĐỘNG RADAR"
                    pos_hint: {"center_x": .5}
                    on_release: app.start_zauto_service()

        # TAB 2: NHẬT KÝ QUÉT (TẤT CẢ TIN NHẮN)
        MDBottomNavigationItem:
            name: 'tab_tinnhan'
            text: 'Tin nhắn'
            icon: 'message-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Nhật ký quét Radar"
                    right_action_items: [["delete-sweep", lambda x: app.clear_history(HISTORY_FILE)]]
                ScrollView:
                    MDList:
                        id: msg_history_list

        # TAB 3: CÀI ĐẶT (THUẬT TOÁN & GIÁ)
        MDBottomNavigationItem:
            name: 'tab_caidat'
            text: 'Cài đặt'
            icon: 'cog-outline'
            MDBoxLayout:
                orientation: 'vertical'
                ScrollView:
                    MDBoxLayout:
                        orientation: 'vertical'
                        adaptive_height: True
                        padding: "15dp"
                        spacing: "10dp"
                        MDTextField:
                            id: inp_reply
                            hint_text: "Câu chốt tự động"
                            mode: "rectangle"
                        MDTextField:
                            id: inp_nhan
                            hint_text: "Từ khóa NHẬN"
                            mode: "rectangle"
                        MDTextField:
                            id: inp_loai
                            hint_text: "Từ khóa LOẠI"
                            mode: "rectangle"
                        MDTextField:
                            id: inp_gia_km
                            hint_text: "Giá tiền/KM (VD: 12000)"
                            mode: "rectangle"
                            input_filter: "int"
                        MDRaisedButton:
                            text: "LƯU CẤU HÌNH"
                            on_release: app.save_config()
                        MDSeparator:
                        MDLabel:
                            text: "Nhóm đang Radar tìm được:"
                            bold: True
                        MDList:
                            id: group_list

        # TAB 4: THÔNG BÁO (CUỐC ĐÃ CHỐT)
        MDBottomNavigationItem:
            name: 'tab_thongbao'
            text: 'Thông báo'
            icon: 'bell-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Cuốc xe đã chốt"
                ScrollView:
                    MDList:
                        id: match_history_list

        # TAB 5: TÀI KHOẢN (ZALO WEB)
        MDBottomNavigationItem:
            name: 'tab_taikhoan'
            text: 'Tài khoản'
            icon: 'account-outline'
            MDBoxLayout:
                orientation: 'vertical'
                padding: "10dp"
                MDCard:
                    size_hint: 1, None
                    height: "120dp"
                    padding: "10dp"
                    FitImage:
                        source: 'profile.jpg'
                        size_hint: None, None
                        size: "60dp", "60dp"
                        radius: [30, ]
                    MDLabel:
                        text: "Vũ Văn Thành\\nTaxi Huyện Lắk"
                        halign: "center"
                MDRaisedButton:
                    text: "LIÊN KẾT ZALO WEB (QUÉT QR)"
                    md_bg_color: 0, 0.5, 0, 1
                    pos_hint: {"center_x": .5}
                    on_release: app.open_zalo_web_qr()
                MDLabel:
                    text: "Logs hệ thống:"
                    font_style: "Caption"
                ScrollView:
                    MDList:
                        id: log_list
'''

class GroupListItem(OneLineRightIconListItem):
    group_name = StringProperty()
    is_active = BooleanProperty(False)

class ZAutoProApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.config_data = {'nhan': '', 'loai': '', 'reply_msg': 'Ok nhận', 'gia_km': '12000', 'groups': {}}
        self.root = Builder.load_string(KV)
        self.load_config()
        Clock.schedule_interval(self.auto_refresh_ui, 3.0)
        return self.root

    def on_start(self):
        # Trì hoãn 3 giây để tránh sập app lúc mới mở
        Clock.schedule_once(self.check_permissions_and_guide, 3)

    def add_log(self, text):
        self.root.ids.log_list.add_widget(OneLineListItem(text=text), index=0)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f: self.config_data = json.load(f)
                self.root.ids.inp_nhan.text = self.config_data.get('nhan', '')
                self.root.ids.inp_loai.text = self.config_data.get('loai', '')
                self.root.ids.inp_reply.text = self.config_data.get('reply_msg', 'Ok nhận')
                self.root.ids.inp_gia_km.text = str(self.config_data.get('gia_km', '12000'))
                self.refresh_group_list()
            except: pass

    def save_config(self):
        self.config_data.update({
            'nhan': self.root.ids.inp_nhan.text.lower(),
            'loai': self.root.ids.inp_loai.text.lower(),
            'reply_msg': self.root.ids.inp_reply.text,
            'gia_km': self.root.ids.inp_gia_km.text
        })
        with open(CONFIG_FILE, 'w') as f: json.dump(self.config_data, f)
        self.add_log("Đã lưu cấu hình!")

    def refresh_group_list(self):
        self.root.ids.group_list.clear_widgets()
        for g, active in self.config_data.get('groups', {}).items():
            self.root.ids.group_list.add_widget(GroupListItem(group_name=g, is_active=active))

    def toggle_group(self, name, state):
        self.config_data['groups'][name] = state
        with open(CONFIG_FILE, 'w') as f: json.dump(self.config_data, f)

    def auto_refresh_ui(self, dt):
        # Cập nhật danh sách nhóm
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    new_data = json.load(f)
                if len(new_data.get('groups', {})) != len(self.config_data.get('groups', {})):
                    self.config_data = new_data
                    self.refresh_group_list()
            except: pass
        
        # Cập nhật Tab 2 (Lịch sử quét)
        self.update_list_from_file(HISTORY_FILE, self.root.ids.msg_history_list)
        # Cập nhật Tab 4 (Cuốc xe chốt)
        self.update_list_from_file(MATCHES_FILE, self.root.ids.match_history_list)

    def update_list_from_file(self, file_path, list_widget):
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                list_widget.clear_widgets()
                for item in reversed(data[-20:]):
                    list_widget.add_widget(TwoLineListItem(text=item['group'], secondary_text=item['msg']))
            except: pass

    def clear_history(self, path):
        if os.path.exists(path): os.remove(path)
        self.add_log("Đã xóa nhật ký")

    @run_on_ui_thread
    def open_zalo_web_qr(self):
        if platform != 'android': return
        try:
            WebView = autoclass('android.webkit.WebView')
            Activity = PythonActivity.mActivity
            wv = WebView(Activity)
            wv.getSettings().setJavaScriptEnabled(True)
            wv.getSettings().setDomStorageEnabled(True)
            wv.getSettings().setUserAgentString("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")
            wv.loadUrl("https://chat.zalo.me")
            Activity.setContentView(wv)
        except Exception as e: self.add_log(f"Lỗi: {e}")

    def check_permissions_and_guide(self, dt):
        if platform != 'android': return
        try:
            activity = PythonActivity.mActivity
            package_name = activity.getPackageName()
            enabled = Settings.Secure.getString(activity.getContentResolver(), "enabled_notification_listeners")
            if package_name not in (enabled or ""):
                intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)
                return
            pm = cast(autoclass('android.os.PowerManager'), activity.getSystemService("power"))
            if not pm.isIgnoringBatteryOptimizations(package_name):
                intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                intent.setData(Uri.parse(f"package:{package_name}"))
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)
        except: pass

    def start_zauto_service(self):
        if platform == 'android':
            try:
                service = autoclass('org.zauto.taxi.ServiceZaloservice')
                service.start(PythonActivity.mActivity, '')
                self.add_log("Đã bật Radar ngầm!")
            except Exception as e: self.add_log(f"Lỗi: {e}")

if __name__ == '__main__':
    ZAutoProApp().run()
