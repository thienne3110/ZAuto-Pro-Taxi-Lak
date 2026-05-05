import json, os, random
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from kivymd.uix.list import OneLineRightIconListItem, TwoLineListItem, OneLineListItem
from kivy.properties import StringProperty, BooleanProperty
from kivymd.toast import toast

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

        MDBottomNavigationItem:
            name: 'tab_canhme'
            text: 'Canh me'
            icon: 'radar'
            MDBoxLayout:
                orientation: 'vertical'
                padding: "20dp"
                spacing: "20dp"
                MDLabel:
                    text: "ZAUTO VIP V6 - TAXI LẮK"
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
                    text: "BẬT RADAR VIP"
                    pos_hint: {"center_x": .5}
                    size_hint_x: 0.8
                    md_bg_color: 0.1, 0.4, 0.8, 1
                    on_release: app.toggle_radar()

        MDBottomNavigationItem:
            name: 'tab_tinnhan'
            text: 'Tin nhắn'
            icon: 'message-text-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Live Chat & Zalo Web"
                    elevation: 2
                    right_action_items: [["delete-sweep", lambda x: app.clear_history(HISTORY_FILE)]]
                MDBoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: "60dp"
                    padding: "10dp"
                    spacing: "10dp"
                    MDRaisedButton:
                        text: "MỞ ZALO WEB (SYNC JS)"
                        md_bg_color: 0, 0.5, 0, 1
                        size_hint_x: 0.7
                        on_release: app.open_zalo_web_qr()
                    MDRaisedButton:
                        text: "XÓA CACHE"
                        md_bg_color: 0.8, 0.2, 0.2, 1
                        size_hint_x: 0.3
                        on_release: app.clear_web_cache()
                ScrollView:
                    MDList:
                        id: msg_history_list

        MDBottomNavigationItem:
            name: 'tab_thongbao'
            text: 'Chốt cuốc'
            icon: 'bell-check'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Cuốc xe thành công"
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
                        
                        MDCard:
                            size_hint: 1, None
                            height: "90dp"
                            padding: "10dp"
                            radius: [10, ]
                            MDBoxLayout:
                                orientation: 'horizontal'
                                spacing: "15dp"
                                FitImage:
                                    source: 'profile.jpg'
                                    size_hint: None, None
                                    size: "70dp", "70dp"
                                    radius: [35, ]
                                MDLabel:
                                    text: "Vũ Văn Thành - Taxi Huyện Lắk"
                                    bold: True
                                    valign: "center"
                        
                        MDRaisedButton:
                            text: "KIỂM TRA & CẤP QUYỀN FULL VIP"
                            md_bg_color: 0.8, 0.4, 0.1, 1
                            pos_hint: {"center_x": .5}
                            size_hint_x: 1
                            on_release: app.check_permissions_and_guide()
                        MDTextField:
                            id: inp_reply
                            hint_text: "Câu chốt tự động (Spintax: Cách nhau dấu |)"
                            mode: "rectangle"
                        MDTextField:
                            id: inp_nhan
                            hint_text: "Từ khóa NHẬN (vd: taxi, xe)"
                            mode: "rectangle"
                        MDTextField:
                            id: inp_loai
                            hint_text: "Từ khóa LOẠI (để trống cũng đc)"
                            mode: "rectangle"
                        MDTextField:
                            id: inp_gia_km
                            hint_text: "Giá taxi/km (VD: 12000)"
                            mode: "rectangle"
                            input_filter: "int"
                        MDBoxLayout:
                            MDLabel:
                                text: "AI Tính giá & Anti-Ban"
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
                            text: "Quản lý Nhóm/Người nhắn:"
                            bold: True
                        MDList:
                            id: group_list
'''

class GroupListItem(OneLineRightIconListItem):
    group_name = StringProperty()
    is_active = BooleanProperty(False)

class ZAutoProApp(MDApp):
    radar_active = BooleanProperty(False)

    def build(self):
        self.icon = 'profile.jpg'
        self.theme_cls.primary_palette = "Blue"
        self.config_data = {'nhan': '', 'loai': '', 'reply_msg': 'Ok nhận', 'gia_km': '12000', 'ai_active': False, 'groups': {}}
        self.root = Builder.load_string(KV)
        self.load_config()
        Clock.schedule_interval(self.auto_refresh_ui, 1.0) 
        return self.root

    def on_start(self):
        if platform == 'android':
            request_permissions([
                Permission.ACCESS_FINE_LOCATION, 
                Permission.ACCESS_COARSE_LOCATION, 
                Permission.POST_NOTIFICATIONS
            ])
            Clock.schedule_once(self.check_permissions_and_guide, 3)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: self.config_data = json.load(f)
                self.root.ids.inp_nhan.text = self.config_data.get('nhan', '')
                self.root.ids.inp_loai.text = self.config_data.get('loai', '')
                self.root.ids.inp_reply.text = self.config_data.get('reply_msg', 'Ok nhận')
                self.root.ids.inp_gia_km.text = str(self.config_data.get('gia_km', '12000'))
                self.root.ids.sw_ai_price.active = self.config_data.get('ai_active', False)
                self.refresh_group_list()
            except: pass

    def save_config(self):
        try:
            self.config_data.update({
                'nhan': self.root.ids.inp_nhan.text.lower(),
                'loai': self.root.ids.inp_loai.text.lower(),
                'reply_msg': self.root.ids.inp_reply.text,
                'gia_km': self.root.ids.inp_gia_km.text or '12000',
                'ai_active': self.root.ids.sw_ai_price.active
            })
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: 
                json.dump(self.config_data, f, ensure_ascii=False)
            toast("Đã lưu cấu hình VIP thành công!")
        except Exception as e: toast(f"Lỗi: {e}")

    def refresh_group_list(self):
        self.root.ids.group_list.clear_widgets()
        for g, active in self.config_data.get('groups', {}).items():
            self.root.ids.group_list.add_widget(GroupListItem(group_name=g, is_active=active))

    def toggle_group(self, name, state):
        try:
            self.config_data['groups'][name] = state
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(self.config_data, f, ensure_ascii=False)
        except: pass

    def auto_refresh_ui(self, dt):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: new_data = json.load(f)
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
                self.root.ids.lbl_doanhthu.text = f"Doanh thu tạm tính: {total_revenue:,} đ"
            except: pass

    def clear_history(self, path):
        if os.path.exists(path): os.remove(path)
        if path == MATCHES_FILE: self.root.ids.lbl_doanhthu.text = "Doanh thu tạm tính: 0 đ"
        toast("Đã dọn dẹp dữ liệu!")

    @run_on_ui_thread
    def clear_web_cache(self):
        if platform != 'android': return
        try:
            WebView = autoclass('android.webkit.WebView')
            WebStorage = autoclass('android.webkit.WebStorage')
            Activity = PythonActivity.mActivity
            WebView(Activity).clearCache(True)
            WebStorage.getInstance().deleteAllData()
            autoclass('android.webkit.CookieManager').getInstance().removeAllCookies(None)
            autoclass('android.webkit.CookieManager').getInstance().flush()
            toast("Đã xóa sạch bộ nhớ Web!")
        except Exception as e: pass

    @run_on_ui_thread
    def open_zalo_web_qr(self):
        if platform != 'android': return
        try:
            WebView = autoclass('android.webkit.WebView')
            WebChromeClient = autoclass('android.webkit.WebChromeClient')
            CookieManager = autoclass('android.webkit.CookieManager')
            Activity = PythonActivity.mActivity
            Dialog = autoclass('android.app.Dialog')
            
            wv = WebView(Activity)
            wv.setWebChromeClient(WebChromeClient())
            settings = wv.getSettings()
            
            settings.setJavaScriptEnabled(True)
            settings.setDomStorageEnabled(True)
            settings.setDatabaseEnabled(True)
            settings.setAllowFileAccess(True)
            
            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15"
            settings.setUserAgentString(user_agent)
            
            cookie_manager = CookieManager.getInstance()
            cookie_manager.setAcceptCookie(True)
            cookie_manager.setAcceptThirdPartyCookies(wv, True)

            js_inject = """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                setInterval(function() {
                    let msgs = document.querySelectorAll('.message-view__bubble');
                    if(msgs.length > 0) { console.log('ZAuto Sync: OK'); }
                }, 2000);
            """
            wv.evaluateJavascript(js_inject, None)
            wv.loadUrl("https://chat.zalo.me")
            
            dialog = Dialog(Activity, 16973830)
            dialog.setContentView(wv)
            dialog.show()
            
            toast("Web Sync VIP Mode: Bật. Bấm Back để thu nhỏ.")
        except Exception as e: pass

    def check_permissions_and_guide(self, dt=None):
        if platform != 'android': return
        try:
            activity = PythonActivity.mActivity
            package_name = activity.getPackageName()
            pm = cast(autoclass('android.os.PowerManager'), activity.getSystemService("power"))
            enabled = Settings.Secure.getString(activity.getContentResolver(), "enabled_notification_listeners")
            
            if package_name not in (enabled or ""):
                toast("BẬT quyền Đọc tin nhắn!")
                activity.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                return 
            
            if not pm.isIgnoringBatteryOptimizations(package_name):
                toast("BẬT quyền Chạy ngầm!")
                intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).setData(Uri.parse(f"package:{package_name}")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)
                return
                
            toast("App đã kích hoạt Full Quyền VIP.")
        except Exception as e: pass

    def toggle_radar(self):
        self.radar_active = not self.radar_active
        if self.radar_active:
            self.root.ids.status_icon.icon = "shield-check"
            self.root.ids.status_icon.icon_color = (0.2, 0.8, 0.2, 1)
            self.root.ids.lbl_status.text = "Radar VIP: QUÉT THẦN TỐC..."
            self.root.ids.btn_radar.text = "DỪNG HỆ THỐNG"
            self.root.ids.btn_radar.md_bg_color = (0.8, 0.2, 0.2, 1)
            if platform == 'android':
                try: autoclass('org.zauto.taxi.ServiceZaloservice').start(PythonActivity.mActivity, '')
                except: pass
        else:
            self.root.ids.status_icon.icon = "shield-off"
            self.root.ids.status_icon.icon_color = (0.8, 0.2, 0.2, 1)
            self.root.ids.lbl_status.text = "Hệ thống đang TẮT"
            self.root.ids.btn_radar.text = "BẬT RADAR VIP"
            self.root.ids.btn_radar.md_bg_color = self.theme_cls.primary_color

if __name__ == '__main__':
    ZAutoProApp().run()
