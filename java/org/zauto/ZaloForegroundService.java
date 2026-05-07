package org.zauto;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

public class ZaloForegroundService extends Service {
    private PowerManager.WakeLock wakeLock;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel("ZAuto_Core", "ZAuto Production Engine", NotificationManager.IMPORTANCE_LOW);
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) manager.createNotificationChannel(channel);
        }

        Notification notif = new Notification.Builder(this, "ZAuto_Core")
                .setContentTitle("ZAuto VIP")
                .setContentText("Hệ thống tự động chốt cuốc đang chạy nền")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .build();

        startForeground(199, notif);

        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        if (pm != null) {
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ZAuto::ProdWakeLock");
            wakeLock.acquire(24 * 60 * 60 * 1000L); // Giữ CPU 24h
        }

        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    public static void startService(Context context) {
        Intent intent = new Intent(context, ZaloForegroundService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent);
        else context.startService(intent);
    }
}
