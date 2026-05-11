package org.zauto;

import android.app.Notification;
import android.content.Intent;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

public class ZaloNotificationService extends NotificationListenerService {
    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (!"com.zing.zalo".equals(sbn.getPackageName())) return;
        
        Notification notif = sbn.getNotification();
        if ((notif.flags & Notification.FLAG_GROUP_SUMMARY) != 0) return;

        Bundle extras = notif.extras;
        if (extras == null) return;

        String group = extras.getString(Notification.EXTRA_TITLE);
        CharSequence textSeq = extras.getCharSequence(Notification.EXTRA_TEXT);
        
        if (group != null && textSeq != null && !group.isEmpty()) {
            Intent intent = new Intent("org.zauto.taxi.NEW_MSG");
            intent.putExtra("group", group);
            intent.putExtra("msg", textSeq.toString());
            sendBroadcast(intent);
        }
    }
}
