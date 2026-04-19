import time
import json
import re
import os
from jnius import autoclass, PythonJavaClass, java_method

Log = autoclass('android.util.Log')

# File config được viết bởi main.py
CONFIG_FILE = '/data/data/org.zauto.taxi/files/config.json'

class ZaloListenerService(PythonJavaClass):
    __javainterfaces__ = ['android/service/notification/NotificationListenerService']
    __javacontext__ = 'app'
    
    def __init__(self):
        super(ZaloListenerService, self).__init__()
        self.TAG = "ZAuto_Engine"
        self.pattern_nhan = None
        self.pattern_loai = None
        self.is_auto = True
        self.load_rules()
        Log.d(self.TAG, "ZAuto Service Da Khoi Dong Thanh Cong!")

    def load_rules(self):
        # Đọc config và Compile Regex trước để tăng tốc độ x5 lần
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    cfg = json.load(f)
                    
                    # Chuyển string "sân bay, bmt" thành regex "(sân bay|bmt)"
                    nhan_words = [w.strip() for w in cfg.get('nhan', '').split(',') if w.strip()]
                    loai_words = [w.strip() for w in cfg.get('loai', '').split(',') if w.strip()]
                    
                    if nhan_words:
                        self.pattern_nhan = re.compile(r'(' + '|'.join(nhan_words) + r')', re.IGNORECASE)
                    if loai_words:
                        self.pattern_loai = re.compile(r'(' + '|'.join(loai_words) + r')', re.IGNORECASE)
                        
                    self.is_auto = cfg.get('auto', True)
                    Log.d(self.TAG, "Da load va compile Regex xong.")
        except Exception as e:
            Log.e(self.TAG, f"Loi doc config: {e}")

    @java_method('(Landroid/service/notification/StatusBarNotification;)V')
    def onNotificationPosted(self, sbn):
        if sbn.getPackageName() == "com.zing.zalo":
            extras = sbn.getNotification().extras
            text = extras.getCharSequence("android.text")
            
            if text:
                msg = str(text)
                self.evaluate_message(msg, sbn)

    def evaluate_message(self, msg, sbn):
        # ==========================================
        # AI SCORING SYSTEM (Hệ thống chấm điểm)
        # ==========================================
        score = 0
        
        # 1. Trừ điểm nặng nếu dính từ khóa loại trừ
        if self.pattern_loai and self.pattern_loai.search(msg):
            score -= 10
            Log.d(self.TAG, f"Bo qua: Dinh tu khoa loai tru. Score: {score}")
            return

        # 2. Cộng điểm nếu dính từ khóa nhận
        if self.pattern_nhan and self.pattern_nhan.search(msg):
            score += 5
            
        # 3. Ra quyết định (Score >= 5 là múc)
        if score >= 5:
            Log.d(self.TAG, ">>> CHOT CUOC! DANG GOI LENH MO ZALO <<<")
            if self.is_auto:
                self.trigger_click(sbn)

    def trigger_click(self, sbn):
        # Bắn lệnh giả lập ngón tay bấm vào thông báo
        intent = sbn.getNotification().contentIntent
        if intent:
            try:
                intent.send()
                Log.d(self.TAG, "Thanh cong: Da bay vao nhom Zalo!")
            except Exception as e:
                Log.e(self.TAG, f"Loi mo intent: {e}")

def main():
    # Giữ cho tiến trình Python không bị đóng
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()