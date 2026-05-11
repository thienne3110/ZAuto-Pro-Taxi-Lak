package org.zauto;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.util.Log;

public class ZaloForegroundService extends Service {
    private static final String TAG = "ZAuto::Foreground";
    private static final String CHANNEL_ID = "ZAuto_Core";
    private static final int NOTIFICATION_ID = 199;
    private PowerManager.WakeLock wakeLock = null;

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "Foreground Service đang được khởi tạo...");
        
        try {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null) {
                wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ZAuto::ProdWakeLock");
            }
        } catch (Exception e) {
            Log.e(TAG, "Lỗi khởi tạo WakeLock: " + e.getMessage());
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "onStartCommand được gọi.");

        // 1. Dùng số 26 thay cho VERSION_CODES.O (Android 8.0)
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, 
                    "ZAuto Production Engine", 
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Duy trì kết nối đồng bộ tin nhắn chạy ngầm ổn định cho ZAuto VIP");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }

        Intent notificationIntent = new Intent();
        try {
            notificationIntent.setClassName(getPackageName(), "org.kivy.android.PythonActivity");
        } catch (Exception e) {
            Log.e(TAG, "Không tìm thấy lớp PythonActivity: " + e.getMessage());
        }

        int pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT;
        // 2. Dùng số 31 thay cho VERSION_CODES.S (Android 12+) để tránh crash
        if (Build.VERSION.SDK_INT >= 31) {
            pendingFlags |= PendingIntent.FLAG_IMMUTABLE;
        }

        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, notificationIntent, pendingFlags
        );

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= 26) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }

        Notification notif = builder
                .setContentTitle("ZAuto VIP")
                .setContentText("Hệ thống tự động chốt cuốc đang chạy nền")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .build();

        // 3. CHỐT CHẶN CHÍ MẠNG: Dùng số 34 thay cho UPSIDE_DOWN_CAKE để lách Compiler API 33
        try {
            if (Build.VERSION.SDK_INT >= 34) {
                // Tiêu chuẩn Android 14+
                startForeground(
                        NOTIFICATION_ID, 
                        notif, 
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
                );
                Log.d(TAG, "Bật Foreground Service chế độ DATA_SYNC chuẩn Android 14+");
            } else if (Build.VERSION.SDK_INT >= 29) { // 29 là Android 10 (Q)
                // Tiêu chuẩn Android 10 đến 13
                startForeground(
                        NOTIFICATION_ID, 
                        notif, 
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
                );
                Log.d(TAG, "Bật Foreground Service chế độ DATA_SYNC chuẩn Android 10+");
            } else {
                startForeground(NOTIFICATION_ID, notif);
                Log.d(TAG, "Bật Foreground Service chế độ legacy");
            }
        } catch (Exception e) {
            Log.e(TAG, "Lỗi khi chạy startForeground: " + e.getMessage());
            try {
                startForeground(NOTIFICATION_ID, notif);
            } catch (Exception ex) {}
        }

        if (wakeLock != null) {
            try {
                if (wakeLock.isHeld()) {
                    wakeLock.release(); 
                }
                wakeLock.acquire(24 * 60 * 60 * 1000L);
                Log.d(TAG, "Đã kích hoạt khóa CPU WakeLock 24h.");
            } catch (Exception e) {
                Log.e(TAG, "Lỗi kích hoạt WakeLock: " + e.getMessage());
            }
        }

        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        try {
            if (wakeLock != null && wakeLock.isHeld()) {
                wakeLock.release();
                Log.d(TAG, "Đã giải phóng WakeLock thành công.");
            }
        } catch (Exception e) {}
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    public static void startService(Context context) {
        if (context == null) return;
        try {
            Intent intent = new Intent(context, ZaloForegroundService.class);
            if (Build.VERSION.SDK_INT >= 26) {
                context.startForegroundService(intent);
            } else {
                context.startService(intent);
            }
        } catch (Exception e) {
            Log.e(TAG, "Không thể khởi động Service: " + e.getMessage());
        }
    }
}
