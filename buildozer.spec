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
presplash.filename = profile.jpg
presplash.color = #FFFFFF

# =====================================================
# PYTHON / KIVY
# =====================================================
requirements = python3,kivy==2.2.1,kivymd==1.1.1,pyjnius,requests

# =====================================================
# LOG
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
# ARCHITECTURE
# =====================================================
android.archs = arm64-v8a

# =====================================================
# P4A
# =====================================================
p4a.bootstrap = sdl2

# =====================================================
# ANDROIDX
# =====================================================
android.enable_androidx = True

# =====================================================
# JAVA / RESOURCES
# =====================================================
android.add_src = ./java
android.add_res = ./res

# =====================================================
# GRADLE DEPENDENCIES
# =====================================================
android.gradle_dependencies = androidx.core:core:1.12.0,androidx.webkit:webkit:1.7.0

# =====================================================
# APK OUTPUT
# =====================================================
android.release_artifact = apk
android.package_format = apk

# =====================================================
# FOREGROUND SERVICE
# =====================================================
android.foreground_service = True

# =====================================================
# PACKAGE QUERY
# =====================================================
android.manifest_queries = com.zing.zalo

# =====================================================
# PERMISSIONS
# =====================================================
android.permissions = INTERNET,WAKE_LOCK,FOREGROUND_SERVICE,FOREGROUND_SERVICE_DATA_SYNC,POST_NOTIFICATIONS,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,RECEIVE_BOOT_COMPLETED,SYSTEM_ALERT_WINDOW,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS

# =====================================================
# MANIFEST EXTRA
# =====================================================
android.extra_manifest_application = %(source.dir)s/manifest_services.xml

# =====================================================
# JAVA SERVICE
# =====================================================
services = ZaloForegroundService:java

# =====================================================
# JVM MEMORY
# =====================================================
android.gradle_args = -Xmx4096m

# =====================================================
# OPENGL
# =====================================================
android.opengl_es_version = 2

# =====================================================
# BUILD PERFORMANCE
# =====================================================
android.copy_libs = 1

# =====================================================
# DEBUG LOGCAT
# =====================================================
android.logcat_filters = python:D *:S

# =====================================================
# BUILD FIX
# =====================================================
android.skip_update = False

# =====================================================
# EXCLUDE FILES
# =====================================================
source.exclude_dirs = venv,.venv,env,.git,.github,__pycache__,bin,.buildozer

source.exclude_patterns = *.pyc,*.pyo,*.log,*.tmp

# =====================================================
# ASSETS
# =====================================================
android.add_assets = .

# =====================================================
# BUILD CACHE
# =====================================================
build_dir = ./.buildozer
bin_dir = ./bin


[buildozer]

log_level = 2

warn_on_root = 0

build_dir = ./.buildozer
bin_dir = ./bin
