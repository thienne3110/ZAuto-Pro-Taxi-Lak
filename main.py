import os, time, threading, queue, sqlite3, hashlib, traceback, logging
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty

if platform == 'android':
    BASE_PATH = '/data/data/org.zauto.taxi/files/'
    from jnius import autoclass, cast
    from android.permissions import request_permissions, Permission
    from android.broadcast import BroadcastReceiver
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
else:
    BASE_PATH = './'

# ==========================================
# 1. LOGGING SYSTEM
# ==========================================
logging.basicConfig(
    filename=os.path.join(BASE_PATH, 'zauto_engine.log'), 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ==========================================
# 2. THREAD-SAFE SQLITE DATABASE
# ==========================================
class DBManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(os.path.join(BASE_PATH, 'history_prod.db'), check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        with self.lock:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS messages (hash_id TEXT PRIMARY KEY, group_name TEXT, msg TEXT, timestamp REAL)''')
            self.cursor.execute('''CREATE INDEX IF NOT EXISTS idx_hash ON messages(hash_id)''')
            self.cursor.execute('''CREATE INDEX IF NOT EXISTS idx_time ON messages(timestamp)''')
            self.conn.commit()

    def cleanup_old_data(self):
        cutoff = time.time() - 604800 # Xóa data cũ hơn 7 ngày
        with self.lock:
            self.cursor.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff,))
            self.conn.commit()

    def is_duplicate(self, hash_id):
        with self.lock:
            self.cursor.execute("SELECT 1 FROM messages WHERE hash_id = ?", (hash_id,))
            return self.cursor.fetchone() is not None

    def save_message(self, hash_id, group_name, msg, ts):
        with self.lock:
            self.cursor.execute("INSERT INTO messages VALUES (?, ?, ?, ?)", (hash_id, group_name, msg, ts))
            self.conn.commit()
            
    def close(self):
        if self.conn: self.conn.close()

# ==========================================
# 3. QUEUE WORKER (CHỐNG FREEZE UI & LEAK RAM)
# ==========================================
class AutoReplyWorker(threading.Thread):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.daemon = True
        self.task_queue = queue.Queue(maxsize=1000)
        self.db = DBManager()
        self.last_reply_times = {}

    def run(self):
        while True:
            try:
                task = self.task_queue.get()
                if task is None: break
                self._process_task(task)
                self.task_queue.task_done()
            except Exception as e:
                logging.error(f"Worker Crash: {traceback.format_exc()}")

    def _process_task(self, task):
        group, msg = task['group'], task['msg']
        ts = time.time()
        
        # Băm MD5 chính xác tuyệt đối
        msg_hash = hashlib.md5(f"{group}{msg}".encode('utf-8')).hexdigest()

        if self.db.is_duplicate(msg_hash): return
        self.db.save_message(msg_hash, group, msg, ts)

        # Batch UI Update qua Main Thread
        Clock.schedule_once(lambda dt: self.app.update_ui(group, msg, time.strftime("%H:%M:%S", time.localtime(ts))), 0)

        # Anti-Spam & Race Condition Logic
        if self.app.is_auto_enabled:
            if ts - getattr(self, 'global_last_reply', 0) < 3: return
            if ts - self.last_reply_times.get(group, 0) > 30:
                self.global_last_reply = ts
                self.last_reply_times[group] = ts
                self.app.trigger_reply(group, "Ok nhận")

# ==========================================
# 4. WATCHDOG THREAD (TỰ HỒI SINH)
# ==========================================
class WatchdogThread(threading.Thread):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.daemon = True

    def run(self):
        while True:
            time.sleep(60)
            if not self.app.worker.is_alive():
                logging.warning("Watchdog: Worker dead. Respawning...")
                self.app.worker = AutoReplyWorker(self.app)
                self.app.worker.start()
            self.app.worker.db.cleanup_old_data()

# ==========================================
# 5. UI KIVYMD (RECYCLEVIEW ANTI-LAG)
# ==========================================
KV = '''
<RideCard@MDCard>:
    group_text: ""
    msg_text: ""
    time_text: ""
    orientation: "vertical"
    padding: "16dp"
    spacing: "8dp"
    size_hint_y: None
    height: "140dp"
    elevation: 2
    radius: [12, 12, 12, 12]
    md_bg_color: 1, 1, 1, 1
    
    MDBoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: "20dp"
        MDLabel:
            text: root.group_text
            font_style: "Subtitle2"
            bold: True
            theme_text_color: "Primary"
        MDLabel:
            text: root.time_text
            font_style: "Caption"
            halign: "right"
            theme_text_color: "Hint"
    MDSeparator:
    MDLabel:
        text: root.msg_text
        font_style: "Body1"
        valign: "top"

MDScreen:
    md_bg_color: 0.95, 0.95, 0.96, 1
    MDBoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "ZAuto VIP - Động Cơ Chạy Ngầm"
            elevation: 1
            md_bg_color: 0.1, 0.5, 0.8, 1
        
        MDBoxLayout:
            size_hint_y: None
            height: "50dp"
            padding: "10dp"
            MDRaisedButton:
                text: "LIÊN KẾT ZALO WEB"
                size_hint_x: 0.5
                md_bg_color: 0.1, 0.6, 0.2, 1
                on_release: app.open_web()
            Widget:
                size_hint_x: 0.1
            MDRaisedButton:
                text: "CẤP QUYỀN HỆ THỐNG"
                size_hint_x: 0.4
                md_bg_color: 0.8, 0.4, 0.1, 1
                on_release: app.grant_permissions()

        RecycleView:
            id: rv
            viewclass: 'RideCard'
            RecycleBoxLayout:
                default_size: None, dp(140)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: 'vertical'
                spacing: dp(12)
                padding: dp(12)
'''

class ZAutoProductionApp(MDApp):
    is_auto_enabled = True

    def build(self):
        self.worker = AutoReplyWorker(self)
        self.worker.start()
        self.watchdog = WatchdogThread(self)
        self.watchdog.start()
        self.is_linked = False
        return Builder.load_string(KV)

    def on_start(self):
        if platform == 'android':
            try:
                request_permissions([Permission.INTERNET, Permission.POST_NOTIFICATIONS])
                autoclass('org.zauto.ZaloForegroundService').startService(PythonActivity.mActivity)
                if not hasattr(self, 'receiver'):
                    self.receiver = BroadcastReceiver(self.on_broadcast, actions=[
                        'org.zauto.taxi.NEW_MSG', 'org.zauto.taxi.WEB_NEW_MSG', 'org.zauto.taxi.LOGIN_SUCCESS'
                    ])
                    self.receiver.start()
            except Exception as e: 
                logging.error(f"Boot Error: {traceback.format_exc()}")

    def on_broadcast(self, context, intent):
        action = intent.getAction()
        if action == 'org.zauto.taxi.LOGIN_SUCCESS':
            self.is_linked = True
            return
            
        group = intent.getStringExtra("group")
        msg = intent.getStringExtra("msg")
        if group and msg:
            try: 
                self.worker.task_queue.put_nowait({'group': group, 'msg': msg})
            except queue.Full: 
                logging.warning("Queue Overflow! Message dropped.")

    @mainthread
    def update_ui(self, group, msg, time_str):
        data = self.root.ids.rv.data
        data.insert(0, {'group_text': group, 'msg_text': msg, 'time_text': time_str})
        if len(data) > 100: data.pop() # Giới hạn 100 item chống tràn RAM

    def trigger_reply(self, group, text):
        if platform == 'android':
            try:
                if self.is_linked:
                    cmd = f"window.sendHiddenMessage('{text}');"
                    autoclass('org.zauto.ZaloWebManager').executeJS(PythonActivity.mActivity, cmd)
                else:
                    instance = autoclass('org.zauto.ZaloAccessibility').instance
                    if instance: instance.executeReplyContext(group, text)
            except Exception as e: logging.error(f"Reply Error: {traceback.format_exc()}")

    def open_web(self):
        if platform == 'android':
            try: autoclass('org.zauto.ZaloWebManager').openZaloWebQR(PythonActivity.mActivity)
            except Exception: pass

    def grant_permissions(self):
        if platform == 'android':
            try:
                Intent = autoclass('android.content.Intent')
                Settings = autoclass('android.provider.Settings')
                PythonActivity.mActivity.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                PythonActivity.mActivity.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            except Exception: pass

    def on_stop(self):
        self.worker.db.close()
        if hasattr(self, 'receiver'): self.receiver.stop()

if __name__ == '__main__':
    ZAutoProductionApp().run()
