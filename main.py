import json
import os
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from kivymd.uix.list import OneLineRightIconListItem
from kivy.properties import StringProperty

# Đường dẫn lưu file cấu hình dùng chung giữa UI và Service
if platform == 'android':
    CONFIG_FILE = '/data/data/org.zauto.taxi/files/config.json'
else:
    CONFIG_FILE = 'config.json'

KV = '''
<SettingsSwitch@MDBoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: "50dp"
    padding: "10dp", "0dp"
    title: ""
    id_switch: ""
    
    MDLabel:
        text: root.title
        theme_text_color: "Primary"
        font_style: "Body1"
        
    MDSwitch:
        id: root.id_switch
        pos_hint: {'center_y': .5}

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
        text_color_active: 0.1, 0.4, 0.8, 1
        text_color_normal: 0.5, 0.5, 0.5, 1

        # ================= TAB 1: CANH ME =================
        MDBottomNavigationItem:
            name: 'tab_canhme'
            text: 'Canh me'
            icon: 'home-outline'

            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "0/0    0/0"
                    elevation: 0
                    md_bg_color: 1, 1, 1, 1
                    specific_text_color: 0.1, 0.4, 0.8, 1
                    right_action_items: [["crown", lambda x: x, "Nâng cấp"]]

                MDBoxLayout:
                    orientation: 'vertical'
                    padding: "20dp"
                    
                    MDLabel:
                        text: "*Hãy luôn mở ứng dụng để không bỏ lỡ tin nhắn"
                        theme_text_color: "Custom"
                        text_color: 0.8, 0.4, 0, 1
                        halign: "center"
                        font_style: "Caption"
                        size_hint_y: 0.1

                    MDBoxLayout:
                        size_hint_y: 0.4
                        MDIconButton:
                            icon: "bell"
                            icon_size: "64sp"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            md_bg_color: 0.1, 0.4, 0.8, 1
                            pos_hint: {"center_x": .5, "center_y": .5}

                    MDLabel:
                        text: "Hệ thống đang túc trực..."
                        id: lbl_status
                        font_style: "H6"
                        bold: True
                        halign: "center"
                        size_hint_y: 0.1
                        
                    MDRaisedButton:
                        text: "KHỞI ĐỘNG HỆ THỐNG NGẦM"
                        pos_hint: {"center_x": .5}
                        md_bg_color: 0.1, 0.4, 0.8, 1
                        on_release: app.start_zauto_service()

                    Widget:
                        size_hint_y: 0.4

        # ================= TAB 2: CÀI ĐẶT (Core System) =================
        MDBottomNavigationItem:
            name: 'tab_caidat'
            text: 'Cài đặt'
            icon: 'cog-outline'

            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Cấu hình & Nhóm Zalo"
                    elevation: 0
                    md_bg_color: 1, 1, 1, 1
                    specific_text_color: 0, 0, 0, 1

                ScrollView:
                    MDBoxLayout:
                        orientation: 'vertical'
                        adaptive_height: True
                        padding: "15dp"
                        spacing: "20dp"
                        
                        MDTextField:
                            id: inp_nhan
                            hint_text: "Từ khóa nhận (+5đ) (VD: sân bay, bmt)"
                            mode: "rectangle"
                            
                        MDTextField:
                            id: inp_loai
                            hint_text: "Từ khóa loại trừ (-10đ) (VD: hàng, ghép)"
                            mode: "rectangle"

                        SettingsSwitch:
                            title: "Tự động nhận (Mở Zalo)"
                            id_switch: "sw_auto"

                        MDRaisedButton:
                            text: "LƯU TỪ KHÓA & TỰ ĐỘNG"
                            pos_hint: {"center_x": .5}
                            on_release: app.save_config()

                        MDSeparator:
                        
                        MDLabel:
                            text: "Danh sách Nhóm Radar quét được:"
                            font_style: "Subtitle2"
                            theme_text_color: "Secondary"

                        MDList:
                            id: group_list
                            
                        Widget:
                            size_hint_y: None
                            height: "50dp"

        # ================= TAB 3 & 4: THÔNG BÁO & TÀI KHOẢN =================
        MDBottomNavigationItem:
            name: 'tab_thongbao'
            text: 'Thông báo'
            icon: 'bell-outline'
            
        MDBottomNavigationItem:
            name: 'tab_taikhoan'
            text: 'Tài khoản'
            icon: 'account-outline'
            MDLabel:
                text: "Tài khoản: vu van thanh\\nĐã liên kết: Taxi Huyện Lắk"
                halign: "center"
'''

class GroupListItem(OneLineRightIconListItem):
    group_name = StringProperty()
    is_active = False

class ZAutoProApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.config_data = {'nhan': '', 'loai': '', 'auto': True, 'groups': {}}
        self.root = Builder.load_string(KV)
        self.load_config()
        
        # Radar quét lại file config mỗi 3 giây
        Clock.schedule_interval(self.auto_refresh_ui, 3.0)
        
        return self.root

    def auto_refresh_ui(self, dt):
        if os.path.exists(CONFIG_FILE):
            try:
                current_time = os.path.getmtime(CONFIG_FILE)
                if not hasattr(self, 'last_modified_time') or current_time > self.last_modified_time:
                    self.last_modified_time = current_time
                    
                    with open(CONFIG_FILE, 'r') as f:
                        new_data = json.load(f)
                    
                    # Nếu thấy Radar ngầm có thêm nhóm mới vào file -> Cập nhật UI
                    if len(new_data.get('groups', {})) != len(self.config_data.get('groups', {})):
                        self.config_data = new_data
                        self.refresh_group_list()
                        print("Radar: Đã cập nhật nhóm mới lên giao diện!")
            except Exception as e:
                pass 

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    self.config_data = json.load(f)
                    
                self.root.ids.inp_nhan.text = self.config_data.get('nhan', '')
                self.root.ids.inp_loai.text = self.config_data.get('loai', '')
                self.root.ids.sw_auto.active = self.config_data.get('auto', True)
                
                # Hiển thị các nhóm đã lưu
                self.refresh_group_list()
        except Exception as e:
            print("Lỗi đọc config:", e)

    def refresh_group_list(self):
        # Xóa list cũ, vẽ lại list mới
        self.root.ids.group_list.clear_widgets()
        for g_name, is_on in self.config_data.get('groups', {}).items():
            item = GroupListItem(group_name=g_name, is_active=is_on)
            self.root.ids.group_list.add_widget(item)

    def toggle_group(self, group_name, is_active):
        # Bật/Tắt nhóm ngay trên giao diện
        if 'groups' not in self.config_data:
            self.config_data['groups'] = {}
        self.config_data['groups'][group_name] = is_active
        self.save_to_disk()

    def save_config(self):
        # Lấy từ khóa mới nhập
        self.config_data['nhan'] = self.root.ids.inp_nhan.text.lower()
        self.config_data['loai'] = self.root.ids.inp_loai.text.lower()
        self.config_data['auto'] = self.root.ids.sw_auto.active
        
        # LƯU Ý: Không được khai báo 'groups' mới ở đây, để giữ nguyên dữ liệu nhóm cũ
        self.save_to_disk()
        print("Đã lưu Cấu hình thành công!")

    def save_to_disk(self):
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config_data, f)
        except Exception as e:
            print("Lỗi ghi file:", e)

    def start_zauto_service(self):
        self.root.ids.lbl_status.text = "Service đang chạy..."
        self.root.ids.lbl_status.text_color = (0, 0.6, 0.1, 1)
        if platform == 'android':
            from jnius import autoclass
            service = autoclass('org.zauto.taxi.ServiceZaloservice')
            mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
            service.start(mActivity, '')

if __name__ == '__main__':
    ZAutoProApp().run()
