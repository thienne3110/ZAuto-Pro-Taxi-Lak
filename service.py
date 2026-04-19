import time
import json
import re
import os
from jnius import autoclass, PythonJavaClass, java_method

Log = autoclass('android.util.Log')
CONFIG_FILE = '/data/data/org.zauto.taxi/files/config.json'

class ZaloListenerService(PythonJavaClass):
    __javainterfaces__ = ['android/service/notification/NotificationListenerService']
    __javacontext__ = 'app'
    
    def __init__(self):
        super(ZaloListenerService, self).__init__()
        self.TAG = "ZAuto_Engine"
        self.pattern_nhan = None
        self.pattern_loai = None
        self.active_groups = []
        self.load_rules()

    def load_rules(self):
        # ... (Phần code cũ: Đọc config, compile Regex) ...
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    cfg = json.load(f)
                    # ... compile regex ...
                    groups = cfg.get('groups', {})
                    self.active_groups = [g_name.lower() for g_name, is_on in groups.items() if is_on]
        except Exception as e:
            Log.e(self.TAG, f"Lỗi load config: {e}")

    # ================= BẢN NÂNG CẤP RADAR TỰ ĐỘNG =================
    def auto_discover_group(self, title):
        """Tự động thêm nhóm mới vào file config nếu chưa tồn tại"""
        try:
            cfg = {'nhan': '', 'loai': '', 'groups': {}}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    cfg = json.load(f)
            
            # Nếu tên này hoàn toàn mới
            if title not in cfg.get('groups', {}):
                cfg['groups'][title] = False # MẶC ĐỊNH TẮT ĐỂ AN TOÀN
                
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(cfg, f)
                    
                Log.d(self.TAG, f"RADAR: Đã bắt được nhóm/người mới -> {title}")
                # Load lại luật ngay lập tức
                self.load_rules()
        except Exception as e:
            Log.e(self.TAG, f"Lỗi Radar: {e}")
    # ==============================================================

    @java_method('(Landroid/service/notification/StatusBarNotification;)V')
    def onNotificationPosted(self, sbn):
        if sbn.getPackageName() == "com.zing.zalo":
            extras = sbn.getNotification().extras
            
            # Lấy tên chính xác 100% từ Zalo (có phân biệt hoa/thường)
            raw_title = str(extras.getString("android.title")) 
            text = extras.getCharSequence("android.text")
            
            if text:
                msg = str(text).lower()
                
                # 1. KÍCH HOẠT RADAR LƯU TÊN NHÓM
                self.auto_discover_group(raw_title)
                
                title_lower = raw_title.lower()
                
                # 2. KIỂM TRA NHÓM CÓ ĐƯỢC BẬT KHÔNG?
                if not any(g in title_lower for g in self.active_groups):
                    return # Nhóm đang TẮT -> Bỏ qua ngay
                
                # 3. NẾU ĐANG BẬT -> CHẤM ĐIỂM
                self.evaluate_message(msg, sbn)

    def evaluate_message(self, msg, sbn):
        cfg = self.get_config()
        score = 0
        
        # Kiểm tra từ khóa loại trừ và nhận
        if self.pattern_loai and self.pattern_loai.search(msg): return
        if self.pattern_nhan and self.pattern_nhan.search(msg): score += 5
            
        if score >= 5:
            # LẤY CHỮ ANH ĐÃ CÀI TRONG MỤC CÀI ĐẶT
            reply_text = cfg.get('reply_msg', 'Ok nhận')
            self.auto_reply_and_open(sbn, reply_text)

    def auto_reply_and_open(self, sbn, reply_text):
        notification = sbn.getNotification()
        
        # BƯỚC 1: TỰ ĐỘNG GỬI TIN NHẮN "OK/NHẬN" NGẦM (Nếu Zalo hỗ trợ)
        try:
            for action in notification.actions:
                if action.getRemoteInputs():
                    remote_inputs = action.getRemoteInputs()
                    bundle = autoclass('android.os.Bundle')()
                    # Nhét chữ anh cài đặt vào đây
                    bundle.putCharSequence(remote_inputs[0].getResultKey(), reply_text)
                    
                    intent = autoclass('android.content.Intent')()
                    autoclass('android.app.RemoteInput').addResultsToIntent(remote_inputs, intent, bundle)
                    
                    # Phát lệnh gửi tin nhắn đi ngay lập tức
                    action.actionIntent.send(self.context, 0, intent)
                    Log.d(self.TAG, f"Đã tự động gửi: {reply_text}")
        except Exception as e:
            Log.e(self.TAG, f"Lỗi gửi ngầm: {str(e)}")

        # BƯỚC 2: MỞ APP ZALO LÊN ĐỂ ANH KIỂM TRA
        intent = notification.contentIntent
        if intent:
            try:
                intent.send()
            except Exception: pass
