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
# Chú ý: Nên fix cứng bản kivymd==1.1.1 để tránh lỗi update UI của bản 2.0.0
requirements = python3,kivy==2.2.1,kivymd==1.1.1,pyjnius

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (str) Icon of the application
icon.filename = profile.jpg

# (list) Permissions
android.permissions = INTERNET,FOREGROUND_SERVICE,FOREGROUND_SERVICE_DATA_SYNC,RECEIVE_BOOT_COMPLETED,WAKE_LOCK,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,POST_NOTIFICATIONS,SYSTEM_ALERT_WINDOW,QUERY_ALL_PACKAGES,BIND_ACCESSIBILITY_SERVICE,BIND_NOTIFICATION_LISTENER_SERVICE

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (str) Android additional libraries/sources
android.add_src = ./java
android.add_resources = ./res

# (list) Android gradle dependencies
android.gradle_dependencies = androidx.core:core:1.12.0

# (bool) Enable AndroidX support
android.enable_androidx = True

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

[buildozer]

# (str) Path to build artifact storage, absolute or relative to spec file
build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab)
bin_dir = ./bin
