[app]

# (str) Title of your application
title = ZAuto VIP

# (str) Package name
package.name = taxi

# (str) Package domain (needed for android/ios packaging)
package.domain = org.zauto

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,json,xml,java,db

# (str) Application versioning
version = 7.0

# (list) Application requirements
# ĐÃ FIX: Chốt cứng phiên bản Kivy, KivyMD, Pyjnius và gỡ bỏ sqlite3, android để trình biên dịch dùng built-in tối ưu nhất
requirements = python3==3.11.1, hostpython3==3.11.1, kivy==2.2.1, kivymd==1.1.1, pyjnius

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (str) Icon of the application
icon.filename = profile.jpg

# (list) Permissions
# ĐÃ FIX: Gộp đầy đủ chuỗi quyền chạy ngầm, quản lý sóng Wifi và trạng thái luồng mạng cho Android 13/14/15
android.permissions = INTERNET, WAKE_LOCK, FOREGROUND_SERVICE, FOREGROUND_SERVICE_DATA_SYNC, FOREGROUND_SERVICE_SPECIAL_USE, POST_NOTIFICATIONS, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, RECEIVE_BOOT_COMPLETED, SYSTEM_ALERT_WINDOW, QUERY_ALL_PACKAGES, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, CHANGE_WIFI_STATE

# (int) Target Android API, should be as high as possible.
# ĐÃ FIX: Hướng tới Android 15 chuẩn Google Play Store
android.api = 35

# (int) Minimum API your APK / AAB will support.
# ĐÃ FIX: Chỉ hỗ trợ từ Android 10 trở lên để loại bỏ rác thư viện legacy
android.minapi = 29

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (str) Android additional libraries/sources
android.add_src = ./java
android.add_resources = ./res

# (list) Android gradle dependencies
# ĐÃ FIX: Thêm thư viện webkit để WebView bám dính tọa độ mượt mà không crash layout
android.gradle_dependencies = androidx.core:core:1.12.0, androidx.webkit:webkit:1.7.0

# (bool) Enable AndroidX support
# ĐÃ FIX: Bật AndroidX và tự động chấp nhận SDK License khi build
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
# LƯU Ý QUAN TRỌNG: Phải có dấu gạch chéo ngược "\" ở cuối mỗi dòng để nối chuỗi
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
    <service android:name="org.zauto.ZaloAccessibility" android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE" android:exported="true" android:label="ZAuto VIP"> \
        <intent-filter> \
            <action android:name="android.accessibilityservice.AccessibilityService" /> \
        </intent-filter> \
        <meta-data android:name="android.accessibilityservice" android:resource="@xml/accessibility_config" /> \
    </service> \
    <service android:name="org.zauto.ZaloForegroundService" android:exported="false" android:foregroundServiceType="dataSync" />

# ĐÃ FIX: Các cấu hình bổ sung bắt buộc để tối ưu hóa màn hình chờ và ép chế độ chạy dọc
p4a.local_recipes = 
fullscreen = 0
android.presplash_color = #FFFFFF

[buildozer]

# (str) Path to build artifact storage, absolute or relative to spec file
build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab)
bin_dir = ./bin
