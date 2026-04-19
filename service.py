import json, os, re, time
from jnius import autoclass

PythonService = autoclass('org.kivy.android.PythonService')
service = PythonService.mService
Intent = autoclass('android.content.Intent')
Context = autoclass('android.content.Context')
TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
Locale = autoclass('java.util.Locale')

BASE_PATH = '/data/data/org.zauto.taxi/files/'
CONFIG_FILE = BASE_PATH + 'config.json'
HISTORY_FILE = BASE_PATH + 'history.json'
MATCHES_FILE = BASE_PATH + 'matches.json'

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

            self.write_log(HISTORY_FILE, group, msg)

            with open(CONFIG_FILE, 'r') as f: cfg = json.load(f)
            
            if group not in cfg['groups']:
                cfg['groups'][group] = False
                with open(CONFIG_FILE, 'w') as f: json.dump(cfg, f)

            if not cfg['groups'].get(group): return

            # Lọc từ khóa LOẠI
            if any(lk.strip() in msg.lower() for lk in cfg.get('loai', '').split(',') if lk.strip()): return

            # Khớp từ khóa NHẬN
            if any(nk.strip() in msg.lower() for nk in cfg.get('nhan', '').split(',') if nk.strip()):
                self.write_log(MATCHES_FILE, group, msg)
                self.execute_vip_task(sbn, msg, cfg)
        except: pass

    def write_log(self, path, group, msg):
        data = []
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
        data.append({"group": group, "msg": msg})
        with open(path, 'w', encoding='utf-8') as f: json.dump(data[-50:], f)

    def execute_vip_task(self, sbn, msg, cfg):
        # 1. LẤY TỌA ĐỘ GPS THẬT
        lat, lon = self.get_real_gps()
        gps_link = f"Vị trí xe em: https://www.google.com/maps?q=lat,lon{lat},{lon}"

        # 2. PHÁT LOA BÁO CÁO
        try:
            if self.tts:
                self.tts.setLanguage(Locale.VIETNAM)
                self.tts.speak("Anh Thành ơi, CÓ KHÁCH em chốt rồi nhé!", TextToSpeech.QUEUE_FLUSH, None, None)
                km = re.findall(r'(\d+)\s*km', msg.lower())
                if km:
                    total = int(km[0]) * int(cfg.get('gia_km', 0))
                    self.tts.speak(f"Cuốc này thu khoảng {total} nghìn", TextToSpeech.QUEUE_ADD, None, None)
        except: pass
        
        # 3. CHỐT TIN 1 & TIN 2 (GPS)
        self.send_reply(sbn, cfg.get('reply_msg', 'Ok nhận'))
        time.sleep(1.5)
        self.send_reply(sbn, gps_link)

    def get_real_gps(self):
        try:
            LocManager = autoclass('android.location.LocationManager')
            loc_service = service.getSystemService(Context.LOCATION_SERVICE)
            loc = loc_service.getLastKnownLocation(LocManager.GPS_PROVIDER) or \
                  loc_service.getLastKnownLocation(LocManager.NETWORK_PROVIDER)
            if loc: return loc.getLatitude(), loc.getLongitude()
        except: pass
        return 12.4242, 108.1717 # Mặc định Huyện Lắk nếu lỗi GPS

    def send_reply(self, sbn, text):
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
