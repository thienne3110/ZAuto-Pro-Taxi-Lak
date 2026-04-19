import json, os, re, time
from jnius import autoclass

PythonService = autoclass('org.kivy.android.PythonService')
service = PythonService.mService
Intent = autoclass('android.content.Intent')
TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
Locale = autoclass('java.util.Locale')

CONFIG_FILE = '/data/data/org.zauto.taxi/files/config.json'
HISTORY_FILE = '/data/data/org.zauto.taxi/files/history.json'
MATCHES_FILE = '/data/data/org.zauto.taxi/files/matches.json'

class Zaloservice(autoclass('android.service.notification.NotificationListenerService')):
    tts = None
    
    def onListenerConnected(self):
        try: self.tts = TextToSpeech(service, None)
        except: pass

    def onNotificationPosted(self, sbn):
        if sbn.getPackageName() != "com.zing.zalo": return
        try:
            extras = sbn.getNotification().extras
            group = str(extras.getCharSequence("android.title"))
            msg = str(extras.getCharSequence("android.text"))

            with open(CONFIG_FILE, 'r') as f: cfg = json.load(f)
            
            # Ghi vào Tab 2 (Lịch sử quét)
            self.save_to_json(HISTORY_FILE, {"group": group, "msg": msg})

            if group not in cfg['groups']:
                cfg['groups'][group] = False
                with open(CONFIG_FILE, 'w') as f: json.dump(cfg, f)

            if not cfg['groups'].get(group): return

            # Kiểm tra từ khóa
            loai_kws = cfg.get('loai', '').split(',')
            if any(lk.strip() in msg.lower() for lk in loai_kws if lk.strip()): return

            nhan_kws = cfg.get('nhan', '').split(',')
            if any(nk.strip() in msg.lower() for nk in nhan_kws if nk.strip()):
                # Ghi vào Tab 4 (Cuốc chốt)
                self.save_to_json(MATCHES_FILE, {"group": group, "msg": msg})
                self.execute_vip(sbn, msg, cfg)
        except: pass

    def save_to_json(self, path, new_item):
        data = []
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
        data.append(new_item)
        with open(path, 'w', encoding='utf-8') as f: json.dump(data[-50:], f)

    def execute_vip(self, sbn, msg, cfg):
        try:
            if self.tts:
                self.tts.setLanguage(Locale.VIETNAM)
                self.tts.speak("Anh Thành ơi, CÓ KHÁCH em chốt rồi nhé!", TextToSpeech.QUEUE_FLUSH, None, None)
                km = re.findall(r'(\d+)\s*km', msg.lower())
                if km:
                    total = int(km[0]) * int(cfg.get('gia_km', 0))
                    self.tts.speak(f"Cuốc này khoảng {total} nghìn", TextToSpeech.QUEUE_ADD, None, None)
        except: pass

        self.reply(sbn, cfg.get('reply_msg', 'Ok nhận'))
        time.sleep(1.2)
        self.reply(sbn, "Vị trí xe em: http://googleusercontent.com/maps.google.com/9")

    def reply(self, sbn, text):
        try:
            notif = sbn.getNotification()
            for action in notif.actions:
                if action.getRemoteInputs():
                    bundle = autoclass('android.os.Bundle')()
                    bundle.putCharSequence(action.getRemoteInputs()[0].getResultKey(), text)
                    intent = Intent()
                    autoclass('android.app.RemoteInput').addResultsToIntent(action.getRemoteInputs(), intent, bundle)
                    action.actionIntent.send(service, 0, intent)
        except: pass
