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
            group = str(extras.getCharSequence("android.title")) 
            msg = str(extras.getCharSequence("android.text"))

            # 1. GHI NHẬN MỌI TIN NHẮN (HIỆN Ở TAB LIVE CHAT)
            self.write_log(HISTORY_FILE, group, msg)

            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: cfg = json.load(f)
            
            # Cập nhật danh sách nhóm/người tự động
            if group not in cfg['groups']:
                cfg['groups'][group] = False
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(cfg, f, ensure_ascii=False)

            # Bỏ qua nếu nhóm này đang Tắt
            if not cfg['groups'].get(group): return

            msg_low = msg.lower()

            # Bỏ qua nếu dính từ khóa LOẠI (Chỉ khi ô LOẠI có chữ)
            loai_keys = [k.strip() for k in cfg.get('loai', '').split(',') if k.strip()]
            if loai_keys and any(lk in msg_low for lk in loai_keys): return

            # Chốt cuốc nếu dính từ khóa NHẬN
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
        
        # AI TÍNH GIÁ TIỀN & DOANH THU
        if cfg.get('ai_active'):
            match = re.search(r'(\d+)\s*(km|cây|cai)', msg_low)
            if match:
                dist = int(match.group(1))
                tong_tien = dist * int(cfg.get('gia_km', 12000))
                reply_text = f"{reply_text}. Khoảng {dist}km, giá {tong_tien:,}đ ạ. Xe em đang qua!"

        # LƯU VÀO TAB CHỐT CUỐC
        self.write_log(MATCHES_FILE, group, original_msg, tong_tien)

        # PHÁT LOA TTS
        try:
            if self.tts:
                self.tts.setLanguage(Locale.VIETNAM)
                self.tts.speak("Anh Thành ơi, CÓ KHÁCH em chốt rồi nhé!", TextToSpeech.QUEUE_FLUSH, None, None)
        except: pass
        
        # HUMAN DELAY (GIẢ NGƯỜI THẬT CHỐNG BOT)
        delay = random.uniform(1.5, 3.5)
        time.sleep(delay)
        
        # GỬI TIN NHẮN CHỐT & GPS VÀO ZALO
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
