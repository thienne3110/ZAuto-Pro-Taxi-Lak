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
        
        // Khởi tạo WakeLock an toàn, chống trùng lặp tiến trình
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

        // 1. Tạo Notification Channel chuẩn Android 8.0+ (Oreo) trở lên
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
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

        // 2. Tạo Intent quay lại ứng dụng khi tài xế bấm vào thông báo chạy nền
        Intent notificationIntent = new Intent();
        try {
            notificationIntent.setClassName(getPackageName(), "org.kivy.android.PythonActivity");
        } catch (Exception e) {
            Log.e(TAG, "Không tìm thấy lớp PythonActivity: " + e.getMessage());
        }

        // Cấu hình cờ PendingIntent an toàn, tương thích Android 12-15 (FLAG_IMMUTABLE)
        int pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            pendingFlags |= PendingIntent.FLAG_IMMUTABLE;
        }

        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, notificationIntent, pendingFlags
        );

        // 3. Xây dựng giao diện thông báo hệ thống
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
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

        // 4. CHỐT CHẶN CHÍ MẠNG: Rẽ nhánh gán SERVICE TYPE cho Android 10+ và 14+ (Chống Crash)
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                // Tiêu chuẩn Android 14+ (API 34/35): Ép gán FOREGROUND_SERVICE_TYPE_DATA_SYNC
                startForeground(
                        NOTIFICATION_ID, 
                        notif, 
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
                );
                Log.d(TAG, "Bật Foreground Service chế độ DATA_SYNC chuẩn Android 14+");
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                // Tiêu chuẩn Android 10 đến 13 (API 29-33): Gán loại hình dịch vụ đồng bộ dữ liệu ngầm
                startForeground(
                        NOTIFICATION_ID, 
                        notif, 
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
                );
                Log.d(TAG, "Bật Foreground Service chế độ DATA_SYNC chuẩn Android 10+");
            } else {
                // Android 9 trở xuống
                startForeground(NOTIFICATION_ID, notif);
                Log.d(TAG, "Bật Foreground Service chế độ legacy");
            }
        } catch (Exception e) {
            Log.e(TAG, "Lỗi khi chạy startForeground: " + e.getMessage());
            try {
                // Fallback cố gắng duy trì chạy thường để tránh sụp app lập tức
                startForeground(NOTIFICATION_ID, notif);
            } catch (Exception ex) {
                Log.e(TAG, "Không thể fallback: " + ex.getMessage());
            }
        }

        // 5. KÍCH HOẠT WAKELOCK AN TOÀN CHỐNG TRÙNG LẶP (Giữ CPU chạy ngầm)
        if (wakeLock != null) {
            try {
                if (wakeLock.isHeld()) {
                    wakeLock.release(); // Giải phóng lần giữ cũ trước khi kích hoạt lần mới
                }
                // Giữ nhịp CPU hoạt động tối đa 24 giờ liên tục
                wakeLock.acquire(24 * 60 * 60 * 1000L);
                Log.d(TAG, "Đã kích hoạt khóa CPU WakeLock 24h.");
            } catch (Exception e) {
                Log.e(TAG, "Lỗi kích hoạt WakeLock: " + e.getMessage());
            }
        }

        // START_STICKY: Tự động khởi động lại dịch vụ nếu hệ thống thiếu RAM và kill nhầm app
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        Log.d(TAG, "onDestroy được gọi. Đang dọn dẹp tài nguyên nền...");
        // Nhả triệt để WakeLock để tối ưu hóa pin khi tắt app
        try {
            if (wakeLock != null && wakeLock.isHeld()) {
                wakeLock.release();
                Log.d(TAG, "Đã giải phóng WakeLock thành công.");
            }
        } catch (Exception e) {
            Log.e(TAG, "Lỗi giải phóng WakeLock: " + e.getMessage());
        }
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
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent);
            } else {
                context.startService(intent);
            }
            Log.d(TAG, "Đã gửi lệnh kích hoạt Service thành công.");
        } catch (Exception e) {
            Log.e(TAG, "Không thể khởi động Service: " + e.getMessage());
        }
    }
}
