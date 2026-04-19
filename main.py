import json
import os
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from kivymd.uix.list import OneLineRightIconListItem, TwoLineListItem, OneLineListItem
from kivy.properties import StringProperty, BooleanProperty

# Đường dẫn lưu file cấu hình dùng chung (ZAuto Taxi Lak)
if platform == 'android':
    CONFIG_FILE = '/data/data/org.zauto.taxi/files/config.json'
    HISTORY_FILE = '/data/data/org.zauto.taxi/files/history.json'
else:
    CONFIG_FILE = 'config.json'
    HISTORY_FILE = 'history.json'

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

        # ================= TAB 1: CANH ME (TRẠNG THÁI CHÍNH) =================
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
                    font_style: "H5"
                    halign: "center"
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
                    font_style: "Subtitle1"

                MDRaisedButton:
                    text: "KHỞI ĐỘNG RADAR NGẦM"
                    pos_hint: {"center_x": .5}
                    size_hint_x: 0.8
                    height: "50dp"
                    on_release: app.start_zauto_service()

        # ================= TAB 2: TIN NHẮN (NHẬT KÝ QUÉT NHÓM) =================
        MDBottomNavigationItem:
            name: 'tab_tinnhan'
            text: 'Tin nhắn'
            icon: 'message-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Tin nhắn vừa quét"
                    elevation: 0
                    right_action_items: [["delete-sweep", lambda x: app.clear_history()]]
                ScrollView:
                    MDList:
                        id: msg_history_list

        # ================= TAB 3: CÀI ĐẶT (QUẢN LÝ NHÓM & TỪ KHÓA) =================
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
                            hint_text: "Câu trả lời (VD: Nhận, Có mặt)"
                            mode: "rectangle"
                        
                        MDTextField:
                            id: inp_nhan
                            hint_text: "Từ khóa CHỐT (cách nhau dấu phẩy)"
                            mode: "rectangle"
                            helper_text: "VD: sân bay, lắk, bmt"
                            helper_text_mode: "on_focus"

                        MDTextField:
                            id: inp_loai
                            hint_text: "Từ khóa LOẠI (cách nhau dấu phẩy)"
                            mode: "rectangle"
                            helper_text: "VD: hàng, ghép, ship"
                            helper_text_mode: "on_focus"
                        
                        MDRaisedButton:
                            text: "LƯU CẤU HÌNH"
                            pos_hint: {"center_x": .5}
                            on_release: app.save_config()
                        
                        MDSeparator:
                        MDLabel:
                            text: "Danh sách nhóm (Radar tự tìm)"
                            bold: True
                        MDList:
                            id: group_list

        # ================= TAB 4: THÔNG BÁO (LỊCH SỬ CHỐT THÀNH CÔNG) =================
        MDBottomNavigationItem:
            name: 'tab_thongbao'
            text: 'Thông báo'
            icon: 'bell-outline'
            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Cuốc đã nhận thành công"
                    elevation: 0
                ScrollView:
                    MDList:
                        id: catch_history_list

        # ================= TAB 5: TÀI KHOẢN (PROFILE & LOGS) =================
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
                    elevation: 1
                    
                    FitImage:
                        source: 'profile.jpg' # Anh nhớ để file hình profile.jpg vào
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
                        text: "Taxi Huyện Lắk - 083.842.9999"
                        halign: "center"
                        theme_text_color: "Secondary"

                MDLabel:
                    text: "Nhật ký hệ thống (Logs):"
                    bold: True
                    font_style: "Caption"

                ScrollView:
                    md_bg_color: 0, 0, 0, 0.05
                    MDList:
                        id: log_list

                MDRaisedButton:
                    text: "THOÁT ỨNG DỤNG"
                    pos_hint: {"center_x": .5}
                    md_bg_color: 1, 0, 0, 1
                    on_release: app.stop()
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
        
        # Chạy Radar cập nhật UI mỗi 3 giây để đồng bộ với Service ngầm
        Clock.schedule_interval(self.auto_refresh_ui, 3.0)
        self.add_log("Khởi động giao diện thành công")
        return self.root

    def add_log(self, text):
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M:%S")
        self.root.ids.log_list.add_widget(OneLineListItem(text=f"[{time_str}] {text}"), index=0)

    def auto_refresh_ui(self, dt):
        """Đọc dữ liệu từ file mà Service ngầm ghi ra để hiện lên màn hình"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    new_data = json.load(f)
                # Nếu có nhóm mới do Service phát hiện, cập nhật danh sách
                if len(new_data.get('groups', {})) != len(self.config_data.get('groups', {})):
                    self.config_data = new_data
                    self.refresh_group_list()
                    self.add_log("Radar phát hiện nhóm Zalo mới")

                # Cập nhật lịch sử tin nhắn (Tab 2)
                if os.path.exists(HISTORY_FILE):
                    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                    self.root.ids.msg_history_list.clear_widgets()
                    for item in reversed(history[-15:]):
                        self.root.ids.msg_history_list.add_widget(
                            TwoLineListItem(text=item['group'], secondary_text=item['msg'])
                        )
            except: pass

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                self.config_data = json.load(f)
            self.root.ids.inp_nhan.text = self.config_data.get('nhan', '')
            self.root.ids.inp_loai.text = self.config_data.get('loai', '')
            self.root.ids.inp_reply.text = self.config_data.get('reply_msg', 'Ok nhận')
            self.refresh_group_list()

    def refresh_group_list(self):
        self.root.ids.group_list.clear_widgets()
        for g_name, is_on in self.config_data.get('groups', {}).items():
            self.root.ids.group_list.add_widget(GroupListItem(group_name=g_name, is_active=is_on))

    def toggle_group(self, group_name, is_active):
        self.config_data['groups'][group_name] = is_active
        self.save_to_disk()
        self.add_log(f"{'Bật' if is_active else 'Tắt'} quét nhóm: {group_name}")

    def save_config(self):
        self.config_data['nhan'] = self.root.ids.inp_nhan.text.lower()
        self.config_data['loai'] = self.root.ids.inp_loai.text.lower()
        self.config_data['reply_msg'] = self.root.ids.inp_reply.text
        self.save_to_disk()
        self.add_log("Đã cập nhật bộ lọc từ khóa")

    def save_to_disk(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config_data, f)

    def clear_history(self):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        self.root.ids.msg_history_list.clear_widgets()
        self.add_log("Đã xóa sạch lịch sử quét")

    def start_zauto_service(self):
        self.root.ids.lbl_status.text = "Hệ thống: ĐANG CHẠY NGẦM"
        self.root.ids.status_icon.text_color = (0, 0.7, 0, 1)
        self.add_log("Bắt đầu chạy Service Android...")
        if platform == 'android':
            try:
                from jnius import autoclass
                service = autoclass('org.zauto.taxi.ServiceZaloservice')
                mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
                service.start(mActivity, '')
                self.add_log("Service đã kích hoạt thành công")
            except Exception as e:
                self.add_log(f"Lỗi khởi động Service: {str(e)}")

if __name__ == '__main__':
    ZAutoProApp().run()
