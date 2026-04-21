import json, os, re, time, random, datetime, queue, threading
from jnius import autoclass

PythonService = autoclass('org.kivy.android.PythonService')
service = PythonService.mService
Intent = autoclass('android.content.Intent')

BASE_PATH = '/data/data/org.zauto.taxi/files/'
CONFIG_FILE = BASE_PATH + 'config.json'
HISTORY_FILE = BASE_PATH + 'history.json'
MATCHES_FILE = BASE_PATH + 'matches.json'

class Zaloservice(autoclass('android.service.notification.NotificationListenerService')):
    task_queue = queue.Queue()
    customer_memory = {}

    def onListenerConnected(self):
        threading.Thread(target=self.queue_worker, daemon=True).start()

    def onNotificationPosted(self, sbn):
        if sbn.getPackageName() != "com.zing.zalo": return
        try:
            extras = sbn.getNotification().extras
            raw_title = str(extras.get("android.title", ""))
            group = re.sub(r'\s*\(\d+\s*tin nhắn\).*', '', raw_title).strip()
            if not group: return

            msg = str(extras.get("android.text", ""))
            text_lines = extras.get("android.textLines")
            if text_lines and len(text_lines) > 0: msg = str(text_lines[-1])
            if not msg or msg == "None": return
            if ":" in msg: msg = msg.split(":", 1)[1].strip()

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
                self.task_queue.put((sbn, group, msg_low, cfg, msg))
        except: pass

    def survival_engine_decision(self, group, msg_low):
        now = datetime.datetime.now()
        if group not in self.customer_memory:
            self.customer_memory[group] = {'msgs_sent': 0, 'last_seen': now}
        mem = self.customer_memory[group]
        
        if any(k in msg_low for k in ['xe', 'đi', 'đón', 'bmt', 'lắk', 'km']):
            time.sleep(random.uniform(1.0, 3.0))
        elif len(msg_low) <= 5:
            if random.random() < 0.8: return False 

        if mem['msgs_sent'] >= 4 and (now - mem['last_seen']).total_seconds() < 120:
            time.sleep(30)
            mem['msgs_sent'] = 0 
            
        mem['msgs_sent'] += 1
        mem['last_seen'] = now
        return True

    def queue_worker(self):
        while True:
            time.sleep(random.uniform(3.0, 6.0)) # Hạ nhiệt CPU
            sbn, group, msg_low, cfg, original_msg = self.task_queue.get()
            if self.survival_engine_decision(group, msg_low):
                self.execute_vip_task(sbn, group, msg_low, cfg, original_msg)
            self.task_queue.task_done()

    def execute_vip_task(self, sbn, group, msg_low, cfg, original_msg):
        if random.random() < 0.10: return 

        base_reply = cfg.get('reply_msg', 'Ok nhận')
        reply_variants = [r.strip() for r in base_reply.split('|') if r.strip()]
        reply_text = random.choice(reply_variants) if reply_variants else base_reply
        tong_tien = 0
        
        if cfg.get('ai_active'):
            match = re.search(r'(\d+)\s*(km|cây|cai)', msg_low)
            if match:
                dist = int(match.group(1))
                tong_tien = dist * int(cfg.get('gia_km', 12000))
                reply_text = f"{reply_text}. Cỡ {dist}km, giá {tong_tien:,}đ ạ."

        self.write_log(MATCHES_FILE, group, original_msg, tong_tien)
        
        read_time = len(original_msg) * 0.05 + random.uniform(1.0, 2.0)
        time.sleep(read_time)
        self.send_with_failsafe(sbn, reply_text)

    def send_with_failsafe(self, sbn, text):
        is_sent = False
        try:
            notif = sbn.getNotification()
            if notif.contentIntent: notif.contentIntent.send() 
            ZaloAcc = autoclass('org.zauto.ZaloAccessibility')
            for _ in range(2):
                if ZaloAcc.instance:
                    is_sent = ZaloAcc.instance.simulateHumanTyping(text)
                    if is_sent: break
                time.sleep(1.0)
        except: pass

        if is_sent: return

        try:
            notif = sbn.getNotification()
            for action in notif.actions:
                if action.getRemoteInputs():
                    bundle = autoclass('android.os.Bundle')()
                    bundle.putCharSequence(action.getRemoteInputs()[0].getResultKey(), text)
                    intent = Intent()
                    autoclass('android.app.RemoteInput').addResultsToIntent(action.getRemoteInputs(), intent, bundle)
                    action.actionIntent.send(service, 0, intent)
                    break
        except: pass

    def write_log(self, path, group, msg, revenue=0):
        data = []
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
            except: pass
        data.append({"group": group, "msg": msg, "revenue": revenue})
        with open(path, 'w', encoding='utf-8') as f: json.dump(data[-50:], f, ensure_ascii=False)
