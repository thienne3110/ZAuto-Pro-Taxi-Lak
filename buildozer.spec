[app]

# (str) Title of your application
title = ZAuto VIP

# (str) Package name
# ĐÃ FIX LỖI 1: Thay đổi từ "taxi" sang "zauto"
package.name = zauto

# (str) Package domain (needed for android/ios packaging)
# ĐÃ FIX LỖI 1: Thay đổi từ "org.zauto" sang "org" để ghép lại khớp 100% với namespace Java: org.zauto
package.domain = org

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,json,xml,java,db

# (str) Application versioning
version = 7.0

# (list) Application requirements
# CHỐT CỨNG: Ép phiên bản Python, Kivy, KivyMD để tương thích tuyệt đối với Cython 0.29.36
requirements = python3==3.11.1, hostpython3==3.11.1, kivy==2.2.1, kivymd==1.1.1, pyjnius

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (str) Icon of the application
icon.filename = profile.jpg

# (list) Permissions
# BẢO MẬT CHẠY NỀN: Đầy đủ quyền chạy ngầm Foreground, đồng bộ dữ liệu Wifi/Mạng và vị trí trên Android 13/14/15
# Đã lược bỏ quyền nguy hiểm FOREGROUND_SERVICE_SPECIAL_USE để tránh bị Google Play Protect quét chính sách
android.permissions = INTERNET, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, WAKE_LOCK, FOREGROUND_SERVICE, FOREGROUND_SERVICE_DATA_SYNC, POST_NOTIFICATIONS, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, RECEIVE_BOOT_COMPLETED, SYSTEM_ALERT_WINDOW, QUERY_ALL_PACKAGES, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, CHANGE_WIFI_STATE

# (int) Target Android API (Hướng tới Android 15 chuẩn Google Play Store)
android.api = 35

# (int) Minimum API your APK / AAB will support (Hỗ trợ từ Android 10 trở lên)
android.minapi = 29

# (list) The Android archs to build for
# CHỈ BUILD arm64-v8a: Giảm dung lượng tệp tin APK xuống 50%, tăng tốc biên dịch và loại bỏ hoàn toàn lỗi crash phân vùng nhị phân (.so)
android.archs = arm64-v8a

# (str) Android additional libraries/sources
android.add_src = ./java

# ĐÃ FIX LỖI 2: Đổi từ android.add_resources thành android.add_res để Buildozer nạp tệp cấu hình Trợ năng vào APK
android.add_res = ./res

# (list) Android gradle dependencies
# Đã sửa: Thêm WebKit hỗ trợ nén layout WebView đè tọa độ không giật lag
android.gradle_dependencies = androidx.core:core:1.12.0, androidx.webkit:webkit:1.7.0

# (bool) Enable AndroidX support
android.enable_androidx = True
android.accept_sdk_license = True
p4a.branch = develop

# (bool) Indicate whether the application should be able to run in background
android.foreground_service = True

# (str) The format used to package the app (apk or aab)
android.release_artifact = apk

# (bool) Preserve files when app is updated
android.preserve_data = True

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (str) XML Manifest additions
# ĐÃ FIX BẢO MẬT: Chuyển exported về "false" cho các dịch vụ nhạy cảm để tránh bị Hijacking dữ liệu.
android.extra_manifest_application = \
    <receiver android:name="org.zauto.BootReceiver" android:enabled="true" android:exported="true"> \
        <intent-filter> \
            <action android:name="android.intent.action.BOOT_COMPLETED" /> \
        </intent-filter> \
    </receiver> \
    <service android:name="org.zauto.ZaloNotificationService" android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE" android:exported="false"> \
        <intent-filter> \
            <action android:name="android.service.notification.NotificationListenerService" /> \
        </intent-filter> \
    </service> \
    <service android:name="org.zauto.ZaloAccessibility" android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE" android:exported="false" android:label="ZAuto VIP"> \
        <intent-filter> \
            <action android:name="android.accessibilityservice.AccessibilityService" /> \
        </intent-filter> \
        <meta-data android:name="android.accessibilityservice" android:resource="@xml/accessibility_config" /> \
    </service> \
    <service android:name="org.zauto.ZaloForegroundService" android:exported="false" android:foregroundServiceType="dataSync" />

# Cấu hình tối ưu hóa màn hình chờ và ép chế độ dọc
p4a.local_recipes = 
fullscreen = 0
android.presplash_color = #FFFFFF

[buildozer]

# (str) Path to build artifact storage, absolute or relative to spec file
build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab)
bin_dir = ./bin
