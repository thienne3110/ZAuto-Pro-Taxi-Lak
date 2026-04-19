import json, os
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from kivymd.uix.list import OneLineRightIconListItem, TwoLineListItem, OneLineListItem
from kivy.properties import StringProperty, BooleanProperty

# Cấu hình đường dẫn file chuẩn theo Package Name: org.zauto.taxi
if platform == 'android':
    BASE_PATH = '/data/data/org.zauto.taxi/files/'
    CONFIG_FILE = BASE_PATH + 'config.json'
    HISTORY_FILE = BASE_PATH + 'history.json'
    MATCHES_FILE = BASE_PATH + 'matches.json'
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

        MDBottomNavigationItem:
            name: 'tab_canhme'
            text: 'Radar'
            icon: 'radar'
            MDBoxLayout:
                orientation: 'vertical'
                padding: "20dp"
                spacing: "20dp"
                MDLabel:
                    text: "ZAUTO PRO - TAXI LẮK"
                    halign: "center"
                    font_style: "H5"
                    bold: True
                MDIconButton:
                    id: status_icon
                    icon: "shield-check"
                    icon_size: "100sp"
                    pos_hint: {"center_x": .5}
                MDLabel:
                    id: lbl_status
                    text: "Trạng thái: Sẵn sàng"
                    halign: "center"
                MDRaisedButton:
                    text: "KÍCH HOẠT HỆ THỐNG"
                    pos_hint: {"center_x": .5}
                    size_hint_x: 0.8
                    on_release: app.start_zauto_service()

        MDBottomNavigationItem:
            name: 'tab_tinnhan'
            text: 'Nhật ký'
            icon: 'message-bulleted'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Lịch sử quét tin"
                    right_action_items: [["delete-sweep", lambda x: app.clear_history(HISTORY_FILE)]]
                ScrollView:
                    MDList:
                        id: msg_history_list

        MDBottomNavigationItem:
            name: 'tab_caidat'
            text: 'Cấu hình'
            icon: 'cog-outline'
            MDBoxLayout:
                orientation: 'vertical'
                ScrollView:
                    MDBoxLayout:
                        orientation: 'vertical'
                        adaptive_height: True
                        padding: "15dp"
                        spacing: "15dp"
                        MDTextField:
                            id: inp_reply
                            hint_text: "Câu chốt tự động"
                            mode: "rectangle"
                        MDTextField:
                            id: inp_nhan
                            hint_text: "Từ khóa NHẬN (cách nhau dấu phẩy)"
                            mode: "rectangle"
                        MDTextField:
                            id: inp_loai
                            hint_text: "Từ khóa LOẠI (cách nhau dấu phẩy)"
                            mode: "rectangle"
                        MDTextField:
                            id: inp_gia_km
                            hint_text: "Giá cước/KM (VD: 12000)"
                            mode: "rectangle"
                            input_filter: "int"
                        MDRaisedButton:
                            text: "LƯU CẤU HÌNH"
                            pos_hint: {"center_x": .5}
                            on_release: app.save_config()
                        MDSeparator:
                        MDLabel:
                            text: "Danh sách nhóm Radar đang tìm:"
                            bold: True
                        MDList:
                            id: group_list

        MDBottomNavigationItem:
            name: 'tab_thongbao'
            text: 'Chốt cuốc'
            icon: 'bell-check'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Cuốc xe đã nhận"
                ScrollView:
                    MDList:
                        id: match_history_list

        MDBottomNavigationItem:
            name: 'tab_zalo'
            text: 'Zalo Web'
            icon: 'web'
            MDBoxLayout:
                orientation: 'vertical'
                padding: "10dp"
                MDCard:
                    orientation: 'vertical'
                    size_hint: 1, None
                    height: "180dp"
                    padding: "15dp"
                    radius: [15, ]
                    FitImage:
                        source: 'profile.jpg'
                        size_hint: None, None
                        size: "80dp", "80dp"
                        radius: [40, ]
                        pos_hint: {"center_x": .5}
                    MDLabel:
                        text: "Vũ Văn Thành - Taxi Lắk"
                        halign: "center"
                        bold: True
                MDRaisedButton:
                    text: "ĐĂNG NHẬP ZALO (QUÉT QR)"
                    md_bg_color: 0, 0.5, 0, 1
                    pos_hint: {"center_x": .5}
                    on_release: app.open_zalo_web_qr()
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
        Clock.schedule_once(self.check_permissions_and_guide, 4)

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
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f: new_data = json.load(f)
                if len(new_data.get('groups', {})) != len(self.config_data.get('groups', {})):
                    self.config_data = new_data
                    self.refresh_group_list()
            except: pass
        self.update_list(HISTORY_FILE, self.root.ids.msg_history_list)
        self.update_list(MATCHES_FILE, self.root.ids.match_history_list)

    def update_list(self, path, widget):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
                widget.clear_widgets()
                for i in reversed(data[-20:]):
                    widget.add_widget(TwoLineListItem(text=i['group'], secondary_text=i['msg']))
            except: pass

    def clear_history(self, path):
        if os.path.exists(path): os.remove(path)
        self.add_log("Đã dọn dẹp nhật ký")

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
        except Exception as e: self.add_log(f"Lỗi Zalo Web: {e}")

    def check_permissions_and_guide(self, dt):
        if platform != 'android': return
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION, Permission.ACCESS_BACKGROUND_LOCATION])
            
            activity = PythonActivity.mActivity
            package_name = activity.getPackageName()
            enabled = Settings.Secure.getString(activity.getContentResolver(), "enabled_notification_listeners")
            if package_name not in (enabled or ""):
                activity.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                return
            pm = cast(autoclass('android.os.PowerManager'), activity.getSystemService("power"))
            if not pm.isIgnoringBatteryOptimizations(package_name):
                intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).setData(Uri.parse(f"package:{package_name}")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)
        except: pass

    def start_zauto_service(self):
        if platform == 'android':
            try:
                autoclass('org.zauto.taxi.ServiceZaloservice').start(PythonActivity.mActivity, '')
                self.root.ids.lbl_status.text = "Radar: ĐANG QUÉT..."
                self.add_log("Đã bật Radar ngầm!")
            except Exception as e: self.add_log(f"Lỗi: {e}")

if __name__ == '__main__':
    ZAutoProApp().run()
