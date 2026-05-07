package org.zauto;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;

public class ZaloForegroundService extends Service {
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String CHANNEL_ID = "ZAuto_Channel";
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "ZAuto System", NotificationManager.IMPORTANCE_LOW);
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) manager.createNotificationChannel(channel);
        }

        Notification notification = new Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("ZAuto VIP")
                .setContentText("Hệ thống radar đang chạy ngầm bảo vệ.")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .build();

        startForeground(1, notification);
        return START_STICKY; 
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }
    
    public static void startService(android.content.Context context) {
        Intent serviceIntent = new Intent(context, ZaloForegroundService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(serviceIntent);
        } else {
            context.startService(serviceIntent);
        }
    }
}
