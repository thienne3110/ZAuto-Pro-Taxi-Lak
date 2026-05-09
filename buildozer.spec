[app]

title = ZAuto VIP

package.name = taxi
package.domain = org.zauto

source.dir = .

source.include_exts = py,png,jpg,kv,json,xml,java,db

version = 7.0

requirements = python3,kivy==2.2.1,kivymd,pyjnius

orientation = portrait

icon.filename = profile.jpg

android.permissions = INTERNET,FOREGROUND_SERVICE,FOREGROUND_SERVICE_DATA_SYNC,RECEIVE_BOOT_COMPLETED,WAKE_LOCK,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,POST_NOTIFICATIONS,SYSTEM_ALERT_WINDOW,QUERY_ALL_PACKAGES

android.api = 34
android.minapi = 24

android.archs = arm64-v8a, armeabi-v7a

android.add_src = java
android.add_resources = res

android.gradle_dependencies = androidx.core:core:1.12.0

android.enable_androidx = True

android.foreground_service = True

android.release_artifact = apk

android.preserve_data = True

log_level = 1

android.extra_manifest_application = \
    <receiver android:name="org.zauto.BootReceiver" android:enabled="true" android:exported="true"> \
        <intent-filter> \
            <action android:name="android.intent.action.BOOT_COMPLETED" /> \
        </intent-filter> \
    </receiver> \
    <service android:name="org.zauto.ZaloForegroundService" \
             android:exported="false" \
             android:foregroundServiceType="dataSync" />

[buildozer]

build_dir = ./.buildozer
bin_dir = ./bin
