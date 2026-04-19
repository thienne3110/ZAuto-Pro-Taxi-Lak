import json, os
from jnius import autoclass

# Đường dẫn file
CONFIG_FILE = '/data/data/org.zauto.taxi/files/config.json'

PythonService = autoclass('org.kivy.android.PythonService')
service = PythonService.mService
NotificationListenerService = autoclass('android.service.notification.NotificationListenerService')
Intent = autoclass('android.content.Intent')

class Zaloservice(NotificationListenerService):
    def onNotificationPosted(self, sbn):
        pkg = sbn.getPackageName()
        if pkg != "com.zing.zalo": return

        notif = sbn.getNotification()
        extras = notif.extras
        title = str(extras.getCharSequence("android.title"))
        msg = str(extras.getCharSequence("android.text"))

        self.process_logic(title, msg, sbn)

    def process_logic(self, group, msg, sbn):
        # Đọc cấu hình
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
        except Exception:
            return
        
        # Cập nhật danh sách nhóm mới vào Radar
        if group not in cfg.get('groups', {}):
            if 'groups' not in cfg: cfg['groups'] = {}
            cfg['groups'][group] = False
            try:
                with open(CONFIG_FILE, 'w') as f: json.dump(cfg, f)
            except Exception: pass
        
        # Nếu nhóm đang tắt (Off) thì bỏ qua
        if not cfg['groups'].get(group): return

        # LOGIC CHẤM ĐIỂM VIP
        is_voice = "[Tin nhắn thoại]" in msg
        keywords = cfg.get('nhan', '').split(',')
        is_match = any(k.strip() in msg.lower() for k in keywords if k.strip())

        if is_match or is_voice:
            reply = cfg.get('reply_msg', 'Ok nhận')
            self.execute_auto(sbn, reply, is_voice)

    def execute_auto(self, sbn, reply, is_voice):
        notif = sbn.getNotification()
        
        # CHỈ BẮN TIN NHẮN NGẦM (Không nhắn nếu khách gửi Voice)
        if not is_voice:
            try:
                for action in notif.actions:
                    if action.getRemoteInputs():
                        remote_inputs = action.getRemoteInputs()
                        bundle = autoclass('android.os.Bundle')()
                        bundle.putCharSequence(remote_inputs[0].getResultKey(), reply)
                        intent = Intent()
                        autoclass('android.app.RemoteInput').addResultsToIntent(remote_inputs, intent, bundle)
                        action.actionIntent.send(service, 0, intent)
            except Exception:
                pass

        # ĐÃ XÓA LỆNH MỞ ZALO GỐC. 
        # Hệ thống giờ đây hoạt động ngầm 100%. Anh sẽ giao tiếp qua Zalo Web trên App.

# Khởi chạy Service
if __name__ == '__main__':
    pass
