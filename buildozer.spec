[app]
# =====================================================
# APP INFO
# =====================================================
title = ZAuto VIP
package.name = zauto
package.domain = org.zauto
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,json,xml,java,db,ttf,otf,txt
version = 7.0
orientation = portrait
fullscreen = 0
icon.filename = profile.jpg
presplash.color = #FFFFFF

# =====================================================
# REQUIREMENTS (Tuyệt đối KHÔNG có Pillow)
# =====================================================
requirements = python3,kivy==2.2.1,kivymd==1.1.1,pyjnius

# =====================================================
# ANDROID CONFIG (Chuẩn 2026 Ít Lỗi Nhất)
# =====================================================
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a
p4a.bootstrap = sdl2

# =====================================================
# DEPENDENCIES & JAVA NATIVE
# =====================================================
android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.12.0, androidx.webkit:webkit:1.7.0
android.add_src = ./java
android.add_res = ./res
android.release_artifact = apk
android.foreground_service = True

# =====================================================
# PERMISSIONS 
# =====================================================
android.permissions = INTERNET,WAKE_LOCK,FOREGROUND_SERVICE,FOREGROUND_SERVICE_DATA_SYNC,POST_NOTIFICATIONS,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,RECEIVE_BOOT_COMPLETED,SYSTEM_ALERT_WINDOW,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS

# =====================================================
# MANIFEST (Tiêm Service Ngầm Chạy Bất Tử)
# =====================================================
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

# =====================================================
# LOG & SYSTEM
# =====================================================
log_level = 2
[buildozer]
build_dir = ./.buildozer
bin_dir = ./bin
