[app]
title = ZAuto VIP
package.name = taxi
package.domain = org.zauto
source.dir = .
source.include_exts = py,png,jpg,kv,json,xml,java
version = 6.0
requirements = python3,kivy==2.2.1,kivymd,pyjnius
orientation = portrait
icon.filename = profile.jpg

# Cấp đầy đủ quyền Anti-Kill và hệ thống
android.permissions = INTERNET, FOREGROUND_SERVICE, RECEIVE_BOOT_COMPLETED, BIND_NOTIFICATION_LISTENER_SERVICE, WAKE_LOCK, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, POST_NOTIFICATIONS, SYSTEM_ALERT_WINDOW

android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a

# Nạp thư mục Java và Res
android.add_src = java
android.add_resources = res

# CHÍCH KHAI BÁO SERVICE NATIVE VÀO MANIFEST MÀ KHÔNG CẦN TẠO FILE CUSTOM XML BÊN NGOÀI
android.manifest.extra_manifest_application_arguments = <service android:name="org.zauto.ZaloAccessibility" android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE" android:exported="true"><intent-filter><action android:name="android.accessibilityservice.AccessibilityService" /></intent-filter><meta-data android:name="android.accessibilityservice" android:resource="@xml/accessibility_config" /></service><service android:name="org.zauto.ZaloForegroundService" android:exported="false" />

android.release_artifact = apk
android.preserve_data = True
log_level = 1
