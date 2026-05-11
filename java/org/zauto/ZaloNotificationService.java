package org.zauto;

import android.app.Notification;
import android.content.Intent;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.util.Log;

public class ZaloNotificationService extends NotificationListenerService {
    private static final String TAG = "ZAuto::NotifService";
    private String lastProcessedMsgId = "";
    private long lastProcessedTime = 0;

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null) return;
        
        // 1. Chỉ lọc duy nhất gói tin nhắn từ Zalo
        if (!"com.zing.zalo".equals(sbn.getPackageName())) return;
        
        try {
            Notification notif = sbn.getNotification();
            if (notif == null) return;

            // Loại bỏ hoàn toàn thông báo gom nhóm (Group Summary) tránh xử lý trùng lặp tin
            if ((notif.flags & Notification.FLAG_GROUP_SUMMARY) != 0) return;

            Bundle extras = notif.extras;
            if (extras == null) return;

            // 2. CƠ CHẾ DÒ TÌM TIÊU ĐỀ NHÓM THÔNG MINH (CHỐNG SÓT TIN)
            String group = "";
            
            // Ưu tiên 1: Lấy tiêu đề cuộc hội thoại nhóm (Conversation Title) - cực kỳ chuẩn cho nhóm Zalo
            Object convTitle = extras.get(Notification.EXTRA_CONVERSATION_TITLE);
            if (convTitle != null) {
                group = convTitle.toString().trim();
            }
            
            // Ưu tiên 2: Fallback nếu không có conversation title, quét EXTRA_TITLE chuẩn
            if (group.isEmpty()) {
                Object title = extras.get(Notification.EXTRA_TITLE);
                if (title != null) {
                    group = title.toString().trim();
                }
            }

            // 3. CƠ CHẾ TRÍCH XUẤT NỘI DUNG TIN NHẮN AN TOÀN TUYỆT ĐỐI
            String msg = "";
            Object textObj = extras.get(Notification.EXTRA_TEXT);
            if (textObj != null) {
                msg = textObj.toString().trim();
            }

            // Nếu tin nhắn trống, quét thêm trường EXTRA_BIG_TEXT phòng hờ tin nhắn quá dài
            if (msg.isEmpty()) {
                Object bigTextObj = extras.get(Notification.EXTRA_BIG_TEXT);
                if (bigTextObj != null) {
                    msg = bigTextObj.toString().trim();
                }
            }

            // 4. KIỂM TRA ĐIỀU KIỆN ĐẦU VÀO TRƯỚC KHI BẮN BROADCAST
            if (group.isEmpty() || msg.isEmpty()) {
                return;
            }

            // Loại bỏ các thông báo rác không phải là cuốc xe (Ví dụ: "Đang kết nối...", "Zalo đang chạy")
            if (msg.contains("đang chạy") || msg.contains("mới nhận") || msg.contains("đang kết nối")) {
                return;
            }

            // 5. CƠ CHẾ CHỐNG LẶP TIN NHẮN TRONG 1.5 GIÂY (CHỐNG QUÁ TẢI PYTHON QUEUE)
            String currentMsgId = group + "_" + msg;
            long currentTime = System.currentTimeMillis();
            if (currentMsgId.equals(lastProcessedMsgId) && (currentTime - lastProcessedTime < 1500)) {
                return; // Tin nhắn trùng lặp xuất hiện quá nhanh -> Bỏ qua
            }
            
            lastProcessedMsgId = currentMsgId;
            lastProcessedTime = currentTime;

            // 6. PHÁT PHÁT Ý ĐỒ (BROADCAST INTENT) SANG PHÍA PYTHON KIVY
            // Đã sửa đổi tên Action thành "org.zauto.taxi.WEB_NEW_MSG" để đồng bộ 100% với hàm on_broadcast_received trong main.py của bạn
            Intent intent = new Intent("org.zauto.taxi.WEB_NEW_MSG");
            intent.putExtra("group", group);
            intent.putExtra("msg", msg);
            intent.putExtra("msg_id", sbn.getKey() != null ? sbn.getKey() : String.valueOf(currentTime));
            intent.putExtra("conversation_id", sbn.getTag() != null ? sbn.getTag() : group);
            
            sendBroadcast(intent);
            Log.d(TAG, "Bắn Broadcast thành công: " + group + " -> " + msg);

        } catch (Exception e) {
            // Bao bọc toàn bộ bằng try-catch để ngăn chặn tuyệt đối việc crash NotificationListenerService
            Log.e(TAG, "Lỗi xử lý thông báo Zalo: " + e.getMessage());
        }
    }
}
