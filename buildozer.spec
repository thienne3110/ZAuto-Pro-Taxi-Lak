[app]
title = ZAuto Pro
package.name = taxi
package.domain = org.zauto
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 5.0
requirements = python3,kivy==2.2.1,kivymd,pyjnius,requests
orientation = portrait

# QUYỀN HỆ THỐNG FULL (Sinh tử để app hoạt động)
android.permissions = INTERNET, FOREGROUND_SERVICE, RECEIVE_BOOT_COMPLETED, BIND_NOTIFICATION_LISTENER_SERVICE, WAKE_LOCK, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, POST_NOTIFICATIONS, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, ACCESS_BACKGROUND_LOCATION

# ÉP PHIÊN BẢN ANDROID MỚI NHẤT & CHẠY NGẦM
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.release_artifact = apk
services = Zaloservice:service.py
android.foreground_service = True
android.preserve_data = True
log_level = 1
