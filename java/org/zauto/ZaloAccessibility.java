package org.zauto;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.app.Notification;
import android.os.Bundle;
import android.graphics.Rect;
import android.util.Log;
import java.util.LinkedList;
import java.util.Queue;
import java.util.List;

public class ZaloAccessibility extends AccessibilityService {
    public static ZaloAccessibility instance;
    private static final String TAG = "ZAutoVIP";

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // Đọc Notifications từ Zalo
        if (event.getEventType() == AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED) {
            if ("com.zing.zalo".equals(event.getPackageName()) && event.getParcelableData() instanceof Notification) {
                Notification notification = (Notification) event.getParcelableData();
                Bundle extras = notification.extras;
                if (extras != null) {
                    String title = extras.getString(Notification.EXTRA_TITLE, "");
                    CharSequence text = extras.getCharSequence(Notification.EXTRA_TEXT);
                    String msg = text != null ? text.toString() : "";

                    if (!title.isEmpty() && !msg.isEmpty()) {
                        Intent intent = new Intent("org.zauto.taxi.NEW_MSG");
                        intent.putExtra("group", title);
                        intent.putExtra("msg", msg);
                        sendBroadcast(intent);
                    }
                }
            }
        }
    }

    @Override
    public void onInterrupt() {}

    // Auto Reply với Context (Bọc trong Thread chống Lag)
    public boolean executeReplyContext(final String groupName, final String replyText) {
        new Thread(() -> {
            try {
                AccessibilityNodeInfo root = getRootInActiveWindow();
                if (root == null) return;

                // 1. Tìm tên nhóm và Click mở chat
                List<AccessibilityNodeInfo> groupNodes = root.findAccessibilityNodeInfosByText(groupName);
                boolean isChatOpened = false;
                if (groupNodes != null && !groupNodes.isEmpty()) {
                    for (AccessibilityNodeInfo node : groupNodes) {
                        AccessibilityNodeInfo clickableParent = getClickableParent(node);
                        if (clickableParent != null) {
                            clickableParent.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                            isChatOpened = true;
                            Thread.sleep(800); // Chờ load khung chat
                            break;
                        }
                    }
                }
                if (!isChatOpened) return;

                // 2. Tìm ô nhập liệu bằng Thuật toán BFS
                root = getRootInActiveWindow();
                AccessibilityNodeInfo inputBox = findNodeByClassBFS(root, "android.widget.EditText");
                if (inputBox == null) {
                    performGlobalAction(GLOBAL_ACTION_BACK);
                    return;
                }

                // 3. Copy text và Paste
                ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                ClipData clip = ClipData.newPlainText("zauto", replyText);
                clipboard.setPrimaryClip(clip);
                inputBox.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
                inputBox.performAction(AccessibilityNodeInfo.ACTION_PASTE);
                Thread.sleep(300);

                // 4. Tìm Nút Gửi bên cạnh Ô nhập (Bypass giấu ID)
                root = getRootInActiveWindow(); 
                Rect inputRect = new Rect();
                inputBox.getBoundsInScreen(inputRect);
                AccessibilityNodeInfo sendBtn = findSendButtonBySpatial(inputBox, inputRect);
                
                if (sendBtn != null) {
                    sendBtn.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                    Thread.sleep(500);
                }

                // 5. Back ra ngoài chờ cuốc mới
                performGlobalAction(GLOBAL_ACTION_BACK);

            } catch (Exception e) {
                Log.e(TAG, "Lỗi Auto Thread: " + e.getMessage());
            }
        }).start();
        return true;
    }

    private AccessibilityNodeInfo getClickableParent(AccessibilityNodeInfo node) {
        AccessibilityNodeInfo p = node;
        for (int i = 0; i < 3; i++) {
            if (p == null) return null;
            if (p.isClickable()) return p;
            p = p.getParent();
        }
        return null;
    }

    private AccessibilityNodeInfo findNodeByClassBFS(AccessibilityNodeInfo root, String className) {
        Queue<AccessibilityNodeInfo> queue = new LinkedList<>();
        queue.add(root);
        while (!queue.isEmpty()) {
            AccessibilityNodeInfo node = queue.poll();
            if (node == null) continue;
            if (className.equals(node.getClassName().toString())) return node;
            for (int i = 0; i < node.getChildCount(); i++) queue.add(node.getChild(i));
        }
        return null;
    }

    private AccessibilityNodeInfo findSendButtonBySpatial(AccessibilityNodeInfo inputBox, Rect inputRect) {
        AccessibilityNodeInfo p = inputBox.getParent();
        if (p == null) return null;
        for (int i = 0; i < p.getChildCount(); i++) {
            AccessibilityNodeInfo sibling = p.getChild(i);
            if (sibling != null && sibling.isClickable() && !sibling.equals(inputBox)) {
                Rect r = new Rect();
                sibling.getBoundsInScreen(r);
                if (r.left >= inputRect.right) return sibling; // Nút ở bên phải input
            }
        }
        return null;
    }
}
