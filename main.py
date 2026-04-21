import json, os, random
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from kivymd.uix.list import OneLineRightIconListItem, TwoLineListItem, OneLineListItem
from kivy.properties import StringProperty, BooleanProperty
from kivymd.uix.snackbar import Snackbar

if platform == 'android':
    BASE_PATH = '/data/data/org.zauto.taxi/files/'
    from android.runnable import run_on_ui_thread
    from jnius import autoclass, cast
    from android.permissions import request_permissions, Permission
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Settings = autoclass('android.provider.Settings')
    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')
else:
    BASE_PATH = './'
    def run_on_ui_thread(func): return func

CONFIG_FILE = BASE_PATH + 'config.json'
HISTORY_FILE = BASE_PATH + 'history.json'
MATCHES_FILE = BASE_PATH + 'matches.json'

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

        # TAB 1: RADAR SĂN CUỐC
        MDBottomNavigationItem:
            name: 'tab_canhme'
            text: 'Canh me'
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
                    icon: "shield-off"
                    icon_size: "120sp"
                    theme_icon_color: "Custom"
                    icon_color: 0.8, 0.2, 0.2, 1
                    pos_hint: {"center_x": .5}
                MDLabel:
                    id: lbl_status
                    text: "Hệ thống đang TẮT"
                    halign: "center"
                    font_style: "H6"
                MDRaisedButton:
                    id: btn_radar
                    text: "BẬT RADAR SĂN CUỐC"
                    pos_hint: {"center_x": .5}
                    size_hint_x: 0.8
                    md_bg_color: 0.1, 0.4, 0.8, 1
                    on_release: app.toggle_radar()

        # TAB 2: LIVE CHAT (MỌI TIN NHẮN)
        MDBottomNavigationItem:
            name: 'tab_tinnhan'
            text: 'Tin nhắn'
            icon: 'message-text-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Live Chat (Tất cả tin nhắn)"
                    elevation: 2
                    right_action_items: [["delete-sweep", lambda x: app.clear_history(HISTORY_FILE)]]
                ScrollView:
                    MDList:
                        id: msg_history_list

        # TAB 3: CUỐC ĐÃ NHẬN & DOANH THU (TÍNH NĂNG VIP)
        MDBottomNavigationItem:
            name: 'tab_thongbao'
            text: 'Chốt cuốc'
            icon: 'bell-check'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Cuốc xe đã chốt"
                    elevation: 2
                    right_action_items: [["delete-sweep", lambda x: app.clear_history(MATCHES_FILE)]]
                MDCard:
                    size_hint_y: None
                    height: "80dp"
                    padding: "10dp"
                    md_bg_color: 0.9, 0.95, 1, 1
                    MDLabel:
                        id: lbl_doanhthu
                        text: "Doanh thu tạm tính: 0 đ"
                        halign: "center"
                        font_style: "H6"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: 0.1, 0.6, 0.1, 1
                ScrollView:
                    MDList:
                        id: match_history_list

        # TAB 4: CÀI ĐẶT BỘ LỌC & AI
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
                            hint_text: "Giá taxi/km (VD: 12000)"
                            mode: "rectangle"
                            input_filter: "int"
                        MDBoxLayout:
                            MDLabel:
                                text: "AI Tính giá tự động"
                                bold: True
                            MDSwitch:
                                id: sw_ai_price
                                active: False
                        MDRaisedButton:
                            text: "LƯU CẤU HÌNH"
                            pos_hint: {"center_x": .5}
                            on_release: app.save_config()
                        MDSeparator:
                        MDLabel:
                            text: "Quản lý Nhóm quét:"
                            bold: True
                        MDList:
                            id: group_list

        # TAB 5: ZALO WEB BYPASS ANTI-BOT
        MDBottomNavigationItem:
            name: 'tab_taikhoan'
            text: 'Zalo Web'
            icon: 'laptop'
            MDBoxLayout:
                orientation: 'vertical'
                padding: "10dp"
                spacing: "15dp"
                MDCard:
                    orientation: 'vertical'
                    size_hint: 1, None
                    height: "150dp"
                    padding: "15dp"
                    radius: [15, ]
                    FitImage:
                        source: 'profile.jpg'
                        size_hint: None, None
                        size: "70dp", "70dp"
                        radius: [35, ]
                        pos_hint: {"center_x": .5}
                    MDLabel:
                        text: "Vũ Văn Thành - Taxi Huyện Lắk"
                        halign: "center"
                        bold: True
                MDBoxLayout:
                    orientation: 'horizontal'
                    spacing: "10dp"
                    size_hint_y: None
                    height: "50dp"
                    MDRaisedButton:
                        text: "MỞ ZALO WEB"
                        md_bg_color: 0, 0.5, 0, 1
                        size_hint_x: 0.7
                        on_release: app.open_zalo_web_qr()
                    MDRaisedButton:
                        text: "XÓA CACHE"
                        md_bg_color: 0.8, 0.2, 0.2, 1
                        size_hint_x: 0.3
                        on_release: app.clear_web_cache()
'''

class GroupListItem(OneLineRightIconListItem):
    group_name = StringProperty()
    is_active = BooleanProperty(False)

class ZAutoProApp(MDApp):
    radar_active = BooleanProperty(False)

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.config_data = {'nhan': '', 'loai': '', 'reply_msg': 'Ok nhận', 'gia_km': '12000', 'ai_active': False, 'groups': {}}
        self.root = Builder.load_string(KV)
        self.load_config()
        # Cập nhật Live Chat siêu tốc 1 giây/lần
        Clock.schedule_interval(self.auto_refresh_ui, 1.0) 
        return self.root

    def on_start(self):
        if platform == 'android':
            request_permissions([
                Permission.ACCESS_FINE_LOCATION, 
                Permission.ACCESS_COARSE_LOCATION, 
                Permission.POST_NOTIFICATIONS
            ], self.check_permissions_and_guide)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f: self.config_data = json.load(f)
                self.root.ids.inp_nhan.text = self.config_data.get('nhan', '')
                self.root.ids.inp_loai.text = self.config_data.get('loai', '')
                self.root.ids.inp_reply.text = self.config_data.get('reply_msg', 'Ok nhận')
                self.root.ids.inp_gia_km.text = str(self.config_data.get('gia_km', '12000'))
                self.root.ids.sw_ai_price.active = self.config_data.get('ai_active', False)
                self.refresh_group_list()
            except: pass

    def save_config(self):
        self.config_data.update({
            'nhan': self.root.ids.inp_nhan.text.lower(),
            'loai': self.root.ids.inp_loai.text.lower(),
            'reply_msg': self.root.ids.inp_reply.text,
            'gia_km': self.root.ids.inp_gia_km.text,
            'ai_active': self.root.ids.sw_ai_price.active
        })
        with open(CONFIG_FILE, 'w') as f: json.dump(self.config_data, f)
        Snackbar(text="Đã lưu cấu hình thuật toán thành công!").open()

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
        self.update_matches_and_revenue()

    def update_list(self, path, widget):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
                widget.clear_widgets()
                for i in reversed(data[-40:]):
                    widget.add_widget(TwoLineListItem(text=f"Từ: {i['group']}", secondary_text=i['msg']))
            except: pass

    def update_matches_and_revenue(self):
        if os.path.exists(MATCHES_FILE):
            try:
                with open(MATCHES_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
                self.root.ids.match_history_list.clear_widgets()
                total_revenue = 0
                for i in reversed(data[-40:]):
                    self.root.ids.match_history_list.add_widget(TwoLineListItem(text=f"Chốt: {i['group']}", secondary_text=i['msg']))
                    total_revenue += i.get('revenue', 0)
                
                # Cập nhật bảng tính tiền VIP
                self.root.ids.lbl_doanhthu.text = f"Doanh thu tạm tính: {total_revenue:,} đ"
            except: pass

    def clear_history(self, path):
        if os.path.exists(path): os.remove(path)
        if path == MATCHES_FILE: self.root.ids.lbl_doanhthu.text = "Doanh thu tạm tính: 0 đ"
        Snackbar(text="Đã làm mới dữ liệu!").open()

    @run_on_ui_thread
    def clear_web_cache(self):
        if platform != 'android': return
        try:
            WebView = autoclass('android.webkit.WebView')
            WebView(PythonActivity.mActivity).clearCache(True)
            autoclass('android.webkit.CookieManager').getInstance().removeAllCookies(None)
            Snackbar(text="Đã xóa bộ nhớ đệm Web!").open()
        except: pass

    @run_on_ui_thread
    def open_zalo_web_qr(self):
        if platform != 'android': return
        try:
            WebView = autoclass('android.webkit.WebView')
            WebSettings = autoclass('android.webkit.WebSettings')
            CookieManager = autoclass('android.webkit.CookieManager')
            Activity = PythonActivity.mActivity
            wv = WebView(Activity)
            settings = wv.getSettings()
            
            settings.setJavaScriptEnabled(True)
            settings.setDomStorageEnabled(True)
            settings.setAllowFileAccess(True)
            
            # BYPASS ANTI-BOT: Chrome 124 bản mới nhất
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            settings.setUserAgentString(user_agent)
            
            cookie_manager = CookieManager.getInstance()
            cookie_manager.setAcceptCookie(True)
            cookie_manager.setAcceptThirdPartyCookies(wv, True)

            # CHÈN MÃ JS XÓA DẤU VẾT BOT CỦA WEBVIEW
            wv.evaluateJavascript("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})", None)

            wv.loadUrl("https://chat.zalo.me")
            Activity.setContentView(wv)
        except Exception as e: pass

    def check_permissions_and_guide(self, p=None, g=None):
        if platform != 'android': return
        try:
            activity = PythonActivity.mActivity
            package_name = activity.getPackageName()
            
            # Quyền thông báo
            enabled = Settings.Secure.getString(activity.getContentResolver(), "enabled_notification_listeners")
            if package_name not in (enabled or ""):
                activity.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                return
            
            # ÉP CHỐNG TẮT APP NGẦM TUYỆT ĐỐI
            pm = cast(autoclass('android.os.PowerManager'), activity.getSystemService("power"))
            if not pm.isIgnoringBatteryOptimizations(package_name):
                intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).setData(Uri.parse(f"package:{package_name}")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)
        except: pass

    def toggle_radar(self):
        self.radar_active = not self.radar_active
        if self.radar_active:
            self.root.ids.status_icon.icon = "shield-check"
            self.root.ids.status_icon.icon_color = (0.2, 0.8, 0.2, 1)
            self.root.ids.lbl_status.text = "Radar: ĐANG QUÉT CUỐC..."
            self.root.ids.btn_radar.text = "DỪNG HỆ THỐNG"
            self.root.ids.btn_radar.md_bg_color = (0.8, 0.2, 0.2, 1)
            if platform == 'android':
                try: autoclass('org.zauto.taxi.ServiceZaloservice').start(PythonActivity.mActivity, '')
                except: pass
        else:
            self.root.ids.status_icon.icon = "shield-off"
            self.root.ids.status_icon.icon_color = (0.8, 0.2, 0.2, 1)
            self.root.ids.lbl_status.text = "Hệ thống đang TẮT"
            self.root.ids.btn_radar.text = "BẬT RADAR SĂN CUỐC"
            self.root.ids.btn_radar.md_bg_color = self.theme_cls.primary_color

if __name__ == '__main__':
    ZAutoProApp().run()
