package org.zauto;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.util.Log;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        
        // Kiểm tra đúng tín hiệu máy đã khởi động xong
        if (Intent.ACTION_BOOT_COMPLETED.equals(action) || 
            "android.intent.action.QUICKBOOT_POWERON".equals(action)) {
            
            Log.d("ZAuto", "Máy đã khởi động - Đang bật dịch vụ ZAuto VIP...");

            try {
                // Gọi dịch vụ chạy ngầm ngay lập tức
                ZaloForegroundService.startService(context);
            } catch (Exception e) {
                Log.e("ZAuto", "Lỗi khởi động Boot: " + e.getMessage());
            }
        }
    }
}
