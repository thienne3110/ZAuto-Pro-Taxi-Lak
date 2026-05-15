package org.zauto;

import android.app.Notification;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

public class ZaloNotificationService extends NotificationListenerService {
    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        // Chỉ quan tâm thông báo từ Zalo
        if (!"com.zing.zalo".equals(sbn.getPackageName())) return;
        
        Notification notif = sbn.getNotification();
        // Bỏ qua các thông báo gom nhóm (Group Summary) để tránh đọc trùng
        if ((notif.flags & Notification.FLAG_GROUP_SUMMARY) != 0) return;

        Bundle extras = notif.extras;
        if (extras == null) return;

        String group = extras.getString(Notification.EXTRA_TITLE);
        CharSequence textSeq = extras.getCharSequence(Notification.EXTRA_TEXT);
        
        if (group != null && textSeq != null && !group.isEmpty()) {
            try {
                // BYPASS ANDROID 14: NÉM THẲNG VÀO HÀNG ĐỢI RAM CỦA PYTHON THAY VÌ BROADCAST
                ZaloWebManager.pythonMsgQueue.add("WEB_NEW_MSG|||" + group + "|||" + textSeq.toString() + "||||||");
            } catch (Exception e) {
                // Bỏ qua lỗi nếu queue chưa sẵn sàng
            }
        }
    }
}
