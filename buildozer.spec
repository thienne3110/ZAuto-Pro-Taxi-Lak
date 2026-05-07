[app]
# (str) Tiêu đề ứng dụng
title = ZAuto VIP

# (str) Tên gói
package.name = taxi

# (str) Tên miền gói
package.domain = org.zauto

# (str) Thư mục chứa mã nguồn main.py
source.dir = .

# (list) Các loại file bao gồm khi build
source.include_exts = py,png,jpg,kv,json,xml,java,db

# (str) Phiên bản ứng dụng
version = 7.0

# (list) Thư viện yêu cầu
requirements = python3,kivy==2.2.1,kivymd,pyjnius

# (str) Hướng màn hình
orientation = portrait

# (str) Icon ứng dụng
icon.filename = profile.jpg

# ==========================================================
# CẤU HÌNH HỆ THỐNG VÀ QUYỀN CHỐNG KILL (ANTI-KILL)
# ==========================================================

# Cấp đầy đủ quyền bao gồm cả Trợ năng (BIND_ACCESSIBILITY_SERVICE)
android.permissions = INTERNET, FOREGROUND_SERVICE, FOREGROUND_SERVICE_DATA_SYNC, RECEIVE_BOOT_COMPLETED, BIND_NOTIFICATION_LISTENER_SERVICE, WAKE_LOCK, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, POST_NOTIFICATIONS, SYSTEM_ALERT_WINDOW, QUERY_ALL_PACKAGES, BIND_ACCESSIBILITY_SERVICE

# Target API mới nhất 2024-2026
android.api = 34
android.minapi = 24

# Kiến trúc CPU cho Box Phone và Máy thật
android.archs = arm64-v8a, armeabi-v7a

# Nạp mã nguồn Java và tài nguyên XML (Thư mục res/xml/accessibility_config.xml)
android.add_src = java
android.add_resources = res

# Chạy dịch vụ Foreground
android.foreground_service = True

# ==========================================================
# KHAI BÁO DỊCH VỤ NATIVE VÀO MANIFEST (FIX TÊN FILE XML)
# ==========================================================
android.extra_manifest_application = \
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
# CẤU HÌNH BUILD NÂNG CAO
# ==========================================================

# Sử dụng AndroidX cho KivyMD
android.enable_androidx = True

# Định dạng APK
android.release_artifact = apk

# Giữ dữ liệu khi cài đè
android.preserve_data = True

# Mức độ log
log_level = 1

[buildozer]
build_dir = ./.buildozer
bin_dir = ./bin
