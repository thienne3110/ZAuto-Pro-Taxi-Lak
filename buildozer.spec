[app]
title = ZAuto Pro
package.name = taxi
package.domain = org.zauto

source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 2.0

requirements = python3,kivy,kivymd,pyjnius

orientation = portrait
fullscreen = 0

# Target Android 12/13, Min Android 8
android.api = 33
android.minapi = 26

# CẤP QUYỀN SINH TỬ
android.permissions = INTERNET, FOREGROUND_SERVICE, RECEIVE_BOOT_COMPLETED, BIND_NOTIFICATION_LISTENER_SERVICE, WAKE_LOCK

# KHAI BÁO DỊCH VỤ CHẠY NGẦM
services = Zaloservice:service.py
android.foreground_service = True

# Tắt console log khi build thật để app nhẹ hơn
log_level = 1
