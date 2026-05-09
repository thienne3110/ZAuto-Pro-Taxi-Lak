[app]

title = ZAuto VIP

package.name = taxi
package.domain = org.zauto

source.dir = .

source.include_exts = py,png,jpg,kv,json,xml,java,db,html

version = 7.0

requirements = python3,kivy==2.2.1,kivymd==1.1.1,pyjnius

orientation = portrait

fullscreen = 0

icon.filename = profile.jpg

android.api = 34
android.minapi = 24
android.ndk = 25b

android.archs = arm64-v8a, armeabi-v7a

android.enable_androidx = True

android.accept_sdk_license = True

android.allow_backup = False
android.presplash_color = #ffffff

android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE,FOREGROUND_SERVICE_DATA_SYNC,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,QUERY_ALL_PACKAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

android.add_src = java

android.add_resources = res

android.gradle_dependencies = androidx.core:core:1.12.0,androidx.webkit:webkit:1.8.0

android.foreground_service = True

android.release_artifact = apk

android.preserve_data = True

android.logcat_filters = *:S python:D ZAUTO:D chromium:D WebView:D

log_level = 2

p4a.branch = master

android.extra_manifest_application = \
    <receiver android:name="org.zauto.BootReceiver" android:enabled="true" android:exported="true"> \
        <intent-filter> \
            <action android:name="android.intent.action.BOOT_COMPLETED"/> \
        </intent-filter> \
    </receiver> \
    <service android:name="org.zauto.ZaloForegroundService" \
             android:enabled="true" \
             android:exported="false" \
             android:foregroundServiceType="dataSync"/>

android.extra_manifest_xml = \
    <uses-feature android:name="android.hardware.touchscreen" android:required="false"/> \
    <uses-permission android:name="android.permission.INTERNET"/> \
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>

[buildozer]

build_dir = ./.buildozer
bin_dir = ./bin
