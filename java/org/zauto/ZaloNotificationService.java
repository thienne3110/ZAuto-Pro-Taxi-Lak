package org.zauto;

import android.app.Notification;
import android.os.Build;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.text.TextUtils;
import android.util.Log;

public class ZaloNotificationService extends NotificationListenerService {

    private static final String TAG = "ZAutoNotif";
    private static final String ZALO_PACKAGE = "com.zing.zalo";

    @Override
    public void onListenerConnected() {
        super.onListenerConnected();
        Log.d(TAG, "Notification Listener Connected");
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {

        try {

            // =====================================================
            // NULL CHECK CHỐNG CRASH
            // =====================================================
            if (sbn == null) return;

            String packageName = sbn.getPackageName();

            if (packageName == null) return;

            // =====================================================
            // CHỈ NHẬN THÔNG BÁO ZALO
            // =====================================================
            if (!ZALO_PACKAGE.equals(packageName)) {
                return;
            }

            Notification notif = sbn.getNotification();

            if (notif == null) return;

            // =====================================================
            // BỎ QUA GROUP SUMMARY
            // TRÁNH ĐỌC TRÙNG THÔNG BÁO
            // =====================================================
            if ((notif.flags & Notification.FLAG_GROUP_SUMMARY) != 0) {
                return;
            }

            // =====================================================
            // LẤY EXTRAS
            // =====================================================
            Bundle extras = notif.extras;

            if (extras == null) {
                return;
            }

            // =====================================================
            // LẤY TIÊU ĐỀ & NỘI DUNG
            // =====================================================
            CharSequence titleSeq =
                    extras.getCharSequence(Notification.EXTRA_TITLE);

            CharSequence textSeq =
                    extras.getCharSequence(Notification.EXTRA_TEXT);

            String group =
                    titleSeq != null ? titleSeq.toString().trim() : "";

            String message =
                    textSeq != null ? textSeq.toString().trim() : "";

            // =====================================================
            // CHỐNG MESSAGE RỖNG
            // =====================================================
            if (TextUtils.isEmpty(group)) return;

            if (TextUtils.isEmpty(message)) return;

            // =====================================================
            // CHỐNG LOOP THÔNG BÁO HỆ THỐNG
            // =====================================================
            if (message.contains("tin nhắn mới")) {
                return;
            }

            // =====================================================
            // CHỐNG DUPLICATE
            // =====================================================
            String notifKey;

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                notifKey = sbn.getKey();
            } else {
                notifKey = String.valueOf(System.currentTimeMillis());
            }

            // =====================================================
            // PUSH VÀO HÀNG ĐỢI RAM
            // =====================================================
            String payload =
                    "WEB_NEW_MSG|||"
                    + group
                    + "|||"
                    + message
                    + "|||"
                    + notifKey
                    + "|||NOTIFICATION";

            ZaloWebManager.pythonMsgQueue.add(payload);

            Log.d(TAG,
                    "NEW ZALO MSG => "
                    + group
                    + " | "
                    + message);

        } catch (Exception e) {

            Log.e(TAG,
                    "Notification Error: "
                    + e.getMessage());

        }
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // Có thể dùng sau này nếu muốn sync trạng thái
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "Notification Listener Destroyed");
    }
}
