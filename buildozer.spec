[app]

# =====================================================
# APP INFO
# =====================================================
title = ZAuto VIP
package.name = zauto
package.domain = org.zauto

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,json,xml,java,db,ttf,otf,txt,html,css,js

version = 7.0

orientation = portrait
fullscreen = 0

icon.filename = profile.jpg
presplash.color = #FFFFFF

# =====================================================
# PYTHON / KIVY (ỔN ĐỊNH NHẤT 2026)
# =====================================================
requirements = python3==3.11.9,kivy==2.2.1,kivymd==1.1.1,pyjnius,requests

# =====================================================
# BUILD SETTINGS
# =====================================================
log_level = 2
warn_on_root = 0

# =====================================================
# ANDROID SDK / NDK
# =====================================================
android.api = 34
android.minapi = 24
android.sdk = 34
android.ndk = 25b

android.accept_sdk_license = True

# =====================================================
# ARCH
# =====================================================
android.archs = arm64-v8a

# =====================================================
# P4A / BOOTSTRAP
# =====================================================
p4a.bootstrap = sdl2
p4a.branch = master

# =====================================================
# ANDROIDX
# =====================================================
android.enable_androidx = True

# =====================================================
# JAVA / RES
# =====================================================
android.add_src = ./java
android.add_res = ./res

# =====================================================
# JAVA DEPENDENCIES
# =====================================================
android.gradle_dependencies = androidx.core:core:1.12.0,androidx.webkit:webkit:1.7.0

# =====================================================
# APK OUTPUT
# =====================================================
android.release_artifact = apk

# =====================================================
# FOREGROUND SERVICE
# =====================================================
android.foreground_service = True

# =====================================================
# QUERY ZALO PACKAGE (ANDROID 11+)
# =====================================================
android.manifest_queries = com.zing.zalo

# =====================================================
# PERMISSIONS
# =====================================================
android.permissions = INTERNET,WAKE_LOCK,FOREGROUND_SERVICE,FOREGROUND_SERVICE_DATA_SYNC,POST_NOTIFICATIONS,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,RECEIVE_BOOT_COMPLETED,SYSTEM_ALERT_WINDOW,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS

# =====================================================
# MANIFEST SERVICES
# =====================================================
android.extra_manifest_application = %(source.dir)s/manifest_services.xml

# =====================================================
# SERVICE CONFIG
# =====================================================
services = ZaloForegroundService:java

# =====================================================
# JVM MEMORY
# =====================================================
android.gradle_args = -Xmx4096m

# =====================================================
# KIVY OPTIMIZATION
# =====================================================
android.presplash_lottie = 0

# =====================================================
# IGNORE FILES KHÔNG CẦN BUILD
# =====================================================
source.exclude_dirs = venv,.venv,env,.git,.github,__pycache__,bin,.buildozer

source.exclude_patterns = *.pyc,*.pyo,*.log,*.tmp

# =====================================================
# UTF-8 FIX
# =====================================================
android.encoding = utf-8

# =====================================================
# DEBUG
# =====================================================
android.logcat_filters = python:D *:S

# =====================================================
# BUILD TIMEOUT FIX
# =====================================================
android.skip_update = False

# =====================================================
# PACKAGE FORMAT
# =====================================================
android.package_format = apk

# =====================================================
# SPLASH
# =====================================================
presplash.filename = profile.jpg

# =====================================================
# ORIENTATION FIX
# =====================================================
orientation = portrait

# =====================================================
# EXTRA ASSETS
# =====================================================
android.add_assets = .

# =====================================================
# OPENGL FIX
# =====================================================
android.opengl_es_version = 2

# =====================================================
# SDL2 FIX
# =====================================================
sdl2_gradle_dependencies = True

# =====================================================
# BUILD CACHE FIX
# =====================================================
build_dir = ./.buildozer
bin_dir = ./bin

# =====================================================
# COMPILER FIX
# =====================================================
android.copy_libs = 1

# =====================================================
# STABILITY FIX
# =====================================================
osx.kivy_version = 2.2.1


[buildozer]

build_dir = ./.buildozer
bin_dir = ./bin

log_level = 2

warn_on_root = 0
