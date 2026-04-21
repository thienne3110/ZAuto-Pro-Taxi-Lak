import json, os, re, time, random
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
            
            # LỌC SẠCH TÊN NHÓM BỊ ZALO GẮN MÁC
            raw_title = str(extras.get("android.title", ""))
            group = re.sub(r'\s*\(\d+\s*tin nhắn\).*', '', raw_title).strip()
            if not group: return

            # CÀO TIN NHẮN TẬN ĐÁY (textLines)
            msg = str(extras.get("android.text", ""))
            text_lines = extras.get("android.textLines")
            if text_lines and len(text_lines) > 0:
                msg = str(text_lines[-1])

            if not msg or msg == "None": return

            if ":" in msg:
                msg = msg.split(":", 1)[1].strip()

            self.write_log(HISTORY_FILE, group, msg)

            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: cfg = json.load(f)
            
            if group not in cfg['groups']:
                cfg['groups'][group] = False
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(cfg, f, ensure_ascii=False)

            if not cfg['groups'].get(group): return

            msg_low = msg.lower()
            
            loai_keys = [k.strip() for k in cfg.get('loai', '').split(',') if k.strip()]
            if loai_keys and any(lk in msg_low for lk in loai_keys): return

            nhan_keys = [k.strip() for k in cfg.get('nhan', '').split(',') if k.strip()]
            if nhan_keys and any(nk in msg_low for nk in nhan_keys):
                self.execute_vip_task(sbn, group, msg_low, cfg, msg)
        except: pass

    def write_log(self, path, group, msg, revenue=0):
        data = []
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
            except: pass
        data.append({"group": group, "msg": msg, "revenue": revenue})
        with open(path, 'w', encoding='utf-8') as f: json.dump(data[-50:], f, ensure_ascii=False)

    def execute_vip_task(self, sbn, group, msg_low, cfg, original_msg):
        lat, lon = self.get_real_gps()
        gps_link = f"Vị trí xe em: https://www.google.com/maps?q=lat,lon{lat},{lon}"

        reply_text = cfg.get('reply_msg', 'Ok nhận')
        tong_tien = 0
        
        # AI TÍNH TIỀN
        if cfg.get('ai_active'):
            match = re.search(r'(\d+)\s*(km|cây|cai)', msg_low)
            if match:
                dist = int(match.group(1))
                tong_tien = dist * int(cfg.get('gia_km', 12000))
                reply_text = f"{reply_text}. Khoảng {dist}km, giá {tong_tien:,}đ ạ. Xe em đang qua!"

        self.write_log(MATCHES_FILE, group, original_msg, tong_tien)

        try:
            if self.tts:
                self.tts.setLanguage(Locale.VIETNAM)
                self.tts.speak("Anh Thành ơi, CÓ KHÁCH", TextToSpeech.QUEUE_FLUSH, None, None)
        except: pass
        
        # DELAY GIẢ NGƯỜI THẬT
        time.sleep(random.uniform(1.5, 3.0))
        self.send_reply(sbn, reply_text)
        time.sleep(2)
        self.send_reply(sbn, gps_link)

    def get_real_gps(self):
        try:
            LocManager = autoclass('android.location.LocationManager')
            loc_service = service.getSystemService(Context.LOCATION_SERVICE)
            loc = loc_service.getLastKnownLocation(LocManager.GPS_PROVIDER) or \
                  loc_service.getLastKnownLocation(LocManager.NETWORK_PROVIDER)
            if loc: return loc.getLatitude(), loc.getLongitude()
        except: pass
        return 12.4242, 108.1717 

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
