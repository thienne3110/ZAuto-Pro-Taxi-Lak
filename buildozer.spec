[app]
title = ZAuto Pro
package.name = taxi
package.domain = org.zauto

source.dir = .
# Đảm bảo có đủ các đuôi file để nạp hình ảnh và cấu hình
source.include_exts = py,png,jpg,kv,json
version = 2.0

# Bổ sung requests để hỗ trợ các tính năng web sau này nếu cần
requirements = python3,kivy==2.2.1,kivymd,pyjnius,requests

orientation = portrait
fullscreen = 0

# Target Android 13 (API 33) là chuẩn nhất hiện nay
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

# ÉP ĐÚC RA FILE APK 
android.release_artifact = apk

# CẤP QUYỀN SINH TỬ (Đã thêm quyền POST_NOTIFICATIONS cho Android 13)
android.permissions = INTERNET, FOREGROUND_SERVICE, RECEIVE_BOOT_COMPLETED, BIND_NOTIFICATION_LISTENER_SERVICE, WAKE_LOCK, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, POST_NOTIFICATIONS

# KHAI BÁO DỊCH VỤ CHẠY NGẦM (Giữ nguyên tên Zaloservice khớp với code)
services = Zaloservice:service.py
android.foreground_service = True

# Chấp nhận license tự động để build không bị dừng giữa chừng
android.accept_sdk_license = True

# Tắt console log để app mượt và nhẹ máy
log_level = 1
