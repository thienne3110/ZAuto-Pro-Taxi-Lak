import json
import os
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.utils import platform

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

MDScreen:
    md_bg_color: 1, 1, 1, 1

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

        # ================= TAB 2: TIN NHẮN (Mockup) =================
        MDBottomNavigationItem:
            name: 'tab_tinnhan'
            text: 'Tin nhắn'
            icon: 'message-outline'
            MDLabel:
                text: "Lịch sử tin nhắn sẽ hiển thị tại đây"
                halign: "center"

        # ================= TAB 3: CÀI ĐẶT (Core System) =================
        MDBottomNavigationItem:
            name: 'tab_caidat'
            text: 'Cài đặt'
            icon: 'cog-outline'

            MDBoxLayout:
                orientation: 'vertical'
                MDTopAppBar:
                    title: "Cài đặt Hệ thống"
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
                            text: "LƯU CẤU HÌNH THUẬT TOÁN"
                            pos_hint: {"center_x": .5}
                            on_release: app.save_config()

        # ================= TAB 4 & 5: THÔNG BÁO & TÀI KHOẢN =================
        MDBottomNavigationItem:
            name: 'tab_thongbao'
            text: 'Thông báo'
            icon: 'bell-outline'
            
        MDBottomNavigationItem:
            name: 'tab_taikhoan'
            text: 'Tài khoản'
            icon: 'account-outline'
            # Giao diện tài khoản đã thiết kế ở bước trước
            MDLabel:
                text: "Tài khoản: vu van thanh\\nĐã liên kết: Taxi Huyện Lắk"
                halign: "center"
'''

class ZAutoProApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        self.root = Builder.load_string(KV)
        self.load_config()
        return self.root

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    cfg = json.load(f)
                    self.root.ids.inp_nhan.text = cfg.get('nhan', '')
                    self.root.ids.inp_loai.text = cfg.get('loai', '')
                    # Note: Cần mapping ID switch chuẩn trong KV
        except Exception as e:
            print("Lỗi đọc config:", e)

    def save_config(self):
        cfg = {
            'nhan': self.root.ids.inp_nhan.text.lower(),
            'loai': self.root.ids.inp_loai.text.lower(),
            'auto': True # Mặc định bật để test
        }
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(cfg, f)
            print("Đã lưu config thành công vào bộ nhớ máy.")
        except Exception as e:
            print("Lỗi lưu config:", e)

    def start_zauto_service(self):
        # Hàm gọi Service Android chạy nền
        self.root.ids.lbl_status.text = "Service đang chạy..."
        self.root.ids.lbl_status.text_color = (0, 0.6, 0.1, 1)
        if platform == 'android':
            from jnius import autoclass
            service = autoclass('org.zauto.taxi.ServiceZaloservice')
            mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
            service.start(mActivity, '')

if __name__ == '__main__':
    ZAutoProApp().run()