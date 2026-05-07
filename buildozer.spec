[app]
# (str) Title of your application
title = ZAuto VIP

# (str) Package name
package.name = taxi

# (str) Package domain (needed for android packaging)
package.domain = org.zauto

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,json,xml,java,db

# (str) Application version
version = 7.0

# (list) Application requirements
# MD5, SQLite3, và Threading có sẵn trong python3
requirements = python3,kivy==2.2.1,kivymd,pyjnius

# (str) Supported orientation (one of landscape, portrait or all)
orientation = portrait

# (str) Icon of the application
icon.filename = profile.jpg

# ==========================================================
# CẤU HÌNH HỆ THỐNG VÀ QUYỀN CHỐNG KILL (ANTI-KILL)
# ==========================================================

# Cấp đầy đủ quyền cho Android 10 đến Android 15
android.permissions = INTERNET, FOREGROUND_SERVICE, FOREGROUND_SERVICE_DATA_SYNC, RECEIVE_BOOT_COMPLETED, BIND_NOTIFICATION_LISTENER_SERVICE, WAKE_LOCK, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, POST_NOTIFICATIONS, SYSTEM_ALERT_WINDOW, QUERY_ALL_PACKAGES

# Target API mới nhất để chạy ổn định trên các dòng máy 2024-2026
android.api = 34
android.minapi = 24

# Kiến trúc CPU phổ biến nhất cho Box Phone và Máy thật
android.archs = arm64-v8a, armeabi-v7a

# Nạp thư mục mã nguồn Java và tài nguyên XML
android.add_src = java
android.add_resources = res

# Cho phép ứng dụng chạy dịch vụ Foreground chuyên nghiệp
android.foreground_service = True

# ==========================================================
# CHÍCH KHAI BÁO TẤT CẢ DỊCH VỤ NATIVE VÀO MANIFEST
# (Bao gồm: A11y, Notification, Foreground, BootReceiver)
# ==========================================================
android.manifest.extra_manifest_application_arguments = \
    <receiver android:name="org.zauto.BootReceiver" android:enabled="true" android:exported="true"> \
        <intent-filter> \
            <action android:name="android.intent.action.BOOT_COMPLETED" /> \
        </intent-filter> \
    </receiver> \
    <service android:name="org.zauto.ZaloNotificationService" android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE" android:exported="true"> \
        <intent-filter> \
            <action android:name="android.service.notification.NotificationListenerService" /> \
        </intent-filter> \
    </service> \
    <service android:name="org.zauto.ZaloAccessibility" android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE" android:exported="true"> \
        <intent-filter> \
            <action android:name="android.accessibilityservice.AccessibilityService" /> \
        </intent-filter> \
        <meta-data android:name="android.accessibilityservice" android:resource="@xml/accessibility_config" /> \
    </service> \
    <service android:name="org.zauto.ZaloForegroundService" android:exported="false" android:foregroundServiceType="dataSync" />

# ==========================================================
# CẤU HÌNH BUILD
# ==========================================================

# (bool) Use AndroidX (Bắt buộc cho KivyMD mới)
android.enable_androidx = True

# Định dạng đầu ra
android.release_artifact = apk

# Giữ lại dữ liệu khi cập nhật app
android.preserve_data = True

# Mức độ log (1 = Lỗi, 2 = Cảnh báo)
log_level = 1

[buildozer]
# Thư mục build tạm
build_dir = ./.buildozer
bin_dir = ./bin
