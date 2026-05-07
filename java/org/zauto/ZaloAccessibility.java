package org.zauto;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;

import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;

import android.util.Log;

import android.content.Intent;

import java.util.LinkedList;
import java.util.List;
import java.util.Queue;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class ZaloAccessibility extends AccessibilityService {

    public static ZaloAccessibility instance;

    private final ExecutorService executor =
            Executors.newSingleThreadExecutor();

    private final Handler mainHandler =
            new Handler(Looper.getMainLooper());

    private static final String TAG = "ZAuto";

    private static final String ZALO_PACKAGE =
            "com.zing.zalo";

    // =====================================================
    // SERVICE CONNECT
    // =====================================================

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();

        instance = this;

        AccessibilityServiceInfo info =
                new AccessibilityServiceInfo();

        info.eventTypes =
                AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED |
                AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED |
                AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED;

        info.feedbackType =
                AccessibilityServiceInfo.FEEDBACK_GENERIC;

        info.flags =
                AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS |
                AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS |
                AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS;

        info.notificationTimeout = 100;

        setServiceInfo(info);

        Log.d(TAG, "Accessibility Connected");
    }

    // =====================================================
    // LISTEN EVENTS
    // =====================================================

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {

        try {

            if (event == null) return;

            if (event.getPackageName() == null) return;

            String pkg = event.getPackageName().toString();

            if (!pkg.equals(ZALO_PACKAGE)) return;

            // =========================================
            // ĐỌC TIN NHẮN TỪ THÔNG BÁO
            // =========================================

            if (event.getEventType() ==
                    AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED) {

                List<CharSequence> texts = event.getText();

                if (texts != null && texts.size() > 0) {

                    String full =
                            texts.toString();

                    Log.d(TAG, "Notification: " + full);

                    try {

                        Intent intent =
                                new Intent("org.zauto.taxi.NEW_MSG");

                        intent.putExtra("group", "Zalo");

                        intent.putExtra("msg", full);

                        sendBroadcast(intent);

                    } catch (Exception e) {
                        Log.e(TAG, "Broadcast error");
                    }
                }
            }

        } catch (Exception e) {

            Log.e(TAG,
                    "onAccessibilityEvent Error: "
                            + e.getMessage());
        }
    }

    @Override
    public void onInterrupt() {

        Log.e(TAG, "Accessibility Interrupted");
    }

    @Override
    public boolean onUnbind(Intent intent) {

        instance = null;

        return super.onUnbind(intent);
    }

    // =====================================================
    // AUTO REPLY
    // =====================================================

    public void executeReplyContext(
            final String groupName,
            final String replyText
    ) {

        executor.execute(() -> {

            AccessibilityNodeInfo root = null;

            try {

                Log.d(TAG,
                        "START AUTO REPLY: "
                                + groupName);

                // =====================================
                // LẤY ROOT
                // =====================================

                root = waitForStableRoot(5000);

                if (root == null) {

                    Log.e(TAG, "Root NULL");

                    return;
                }

                // =====================================
                // CHECK PACKAGE
                // =====================================

                if (root.getPackageName() == null) {

                    Log.e(TAG, "Package NULL");

                    return;
                }

                String currentPkg =
                        root.getPackageName().toString();

                if (!currentPkg.equals(ZALO_PACKAGE)) {

                    Log.e(TAG,
                            "Not in Zalo: "
                                    + currentPkg);

                    return;
                }

                // =====================================
                // TÌM GROUP
                // =====================================

                AccessibilityNodeInfo groupNode =
                        findNodeByTextContains(root, groupName);

                if (groupNode == null) {

                    Log.e(TAG,
                            "Group Not Found");

                    return;
                }

                AccessibilityNodeInfo clickable =
                        getClickableParent(groupNode);

                if (clickable != null) {

                    clickable.performAction(
                            AccessibilityNodeInfo.ACTION_CLICK
                    );

                    Log.d(TAG,
                            "Clicked Group");

                    sleep(1200);
                }

                recycleNode(groupNode);

                recycleNode(clickable);

                recycleNode(root);

                // =====================================
                // LOAD CHAT
                // =====================================

                root = waitForStableRoot(4000);

                if (root == null) {

                    Log.e(TAG,
                            "Chat Root NULL");

                    return;
                }

                // =====================================
                // FIND INPUT
                // =====================================

                AccessibilityNodeInfo inputBox =
                        findInputBox(root);

                if (inputBox == null) {

                    Log.e(TAG,
                            "Input Not Found");

                    return;
                }

                Bundle args = new Bundle();

                args.putCharSequence(
                        AccessibilityNodeInfo
                                .ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                        replyText
                );

                boolean setOk =
                        inputBox.performAction(
                                AccessibilityNodeInfo.ACTION_SET_TEXT,
                                args
                        );

                Log.d(TAG,
                        "SET TEXT = " + setOk);

                sleep(500);

                // =====================================
                // FIND SEND BUTTON
                // =====================================

                AccessibilityNodeInfo sendBtn =
                        findSendButton(root);

                if (sendBtn == null) {

                    Log.e(TAG,
                            "Send Button NULL");

                    return;
                }

                boolean clickOk =
                        sendBtn.performAction(
                                AccessibilityNodeInfo.ACTION_CLICK
                        );

                Log.d(TAG,
                        "SEND CLICK = " + clickOk);

                sleep(800);

                // =====================================
                // BACK
                // =====================================

                performGlobalAction(
                        GLOBAL_ACTION_BACK
                );

                Log.d(TAG,
                        "AUTO REPLY SUCCESS");

                recycleNode(inputBox);

                recycleNode(sendBtn);

            } catch (Exception e) {

                Log.e(TAG,
                        "AUTO REPLY ERROR: "
                                + e.getMessage());

            } finally {

                recycleNode(root);
            }
        });
    }

    // =====================================================
    // WAIT ROOT
    // =====================================================

    private AccessibilityNodeInfo waitForStableRoot(
            int timeoutMs
    ) {

        int waited = 0;

        while (waited < timeoutMs) {

            try {

                AccessibilityNodeInfo root =
                        getRootInActiveWindow();

                if (root != null) {

                    return root;
                }

                Thread.sleep(200);

                waited += 200;

            } catch (Exception e) {

                Log.e(TAG,
                        "waitRoot error");
            }
        }

        return null;
    }

    // =====================================================
    // FIND NODE TEXT CONTAINS
    // =====================================================

    private AccessibilityNodeInfo findNodeByTextContains(
            AccessibilityNodeInfo root,
            String target
    ) {

        if (root == null) return null;

        Queue<AccessibilityNodeInfo> queue =
                new LinkedList<>();

        queue.add(root);

        while (!queue.isEmpty()) {

            AccessibilityNodeInfo node =
                    queue.poll();

            if (node == null) continue;

            try {

                CharSequence txt =
                        node.getText();

                if (txt != null) {

                    String t =
                            txt.toString().toLowerCase();

                    if (t.contains(
                            target.toLowerCase()
                    )) {

                        return node;
                    }
                }

                for (int i = 0;
                     i < node.getChildCount();
                     i++) {

                    AccessibilityNodeInfo child =
                            node.getChild(i);

                    if (child != null) {

                        queue.add(child);
                    }
                }

            } catch (Exception ignored) {}
        }

        return null;
    }

    // =====================================================
    // FIND INPUT BOX
    // =====================================================

    private AccessibilityNodeInfo findInputBox(
            AccessibilityNodeInfo root
    ) {

        if (root == null) return null;

        Queue<AccessibilityNodeInfo> queue =
                new LinkedList<>();

        queue.add(root);

        while (!queue.isEmpty()) {

            AccessibilityNodeInfo node =
                    queue.poll();

            if (node == null) continue;

            try {

                CharSequence cls =
                        node.getClassName();

                if (cls != null) {

                    String className =
                            cls.toString();

                    if (
                            className.contains("EditText")
                    ) {

                        return node;
                    }
                }

                for (int i = 0;
                     i < node.getChildCount();
                     i++) {

                    AccessibilityNodeInfo child =
                            node.getChild(i);

                    if (child != null) {

                        queue.add(child);
                    }
                }

            } catch (Exception ignored) {}
        }

        return null;
    }

    // =====================================================
    // FIND SEND BUTTON
    // =====================================================

    private AccessibilityNodeInfo findSendButton(
            AccessibilityNodeInfo root
    ) {

        if (root == null) return null;

        Queue<AccessibilityNodeInfo> queue =
                new LinkedList<>();

        queue.add(root);

        while (!queue.isEmpty()) {

            AccessibilityNodeInfo node =
                    queue.poll();

            if (node == null) continue;

            try {

                CharSequence desc =
                        node.getContentDescription();

                CharSequence txt =
                        node.getText();

                if (desc != null) {

                    String d =
                            desc.toString().toLowerCase();

                    if (
                            d.contains("gửi") ||
                            d.contains("send")
                    ) {

                        return node;
                    }
                }

                if (txt != null) {

                    String t =
                            txt.toString().toLowerCase();

                    if (
                            t.equals("gửi") ||
                            t.equals("send")
                    ) {

                        return node;
                    }
                }

                for (int i = 0;
                     i < node.getChildCount();
                     i++) {

                    AccessibilityNodeInfo child =
                            node.getChild(i);

                    if (child != null) {

                        queue.add(child);
                    }
                }

            } catch (Exception ignored) {}
        }

        return null;
    }

    // =====================================================
    // CLICKABLE PARENT
    // =====================================================

    private AccessibilityNodeInfo getClickableParent(
            AccessibilityNodeInfo node
    ) {

        AccessibilityNodeInfo parent = node;

        for (int i = 0; i < 10; i++) {

            if (parent == null)
                return null;

            if (parent.isClickable())
                return parent;

            parent = parent.getParent();
        }

        return null;
    }

    // =====================================================
    // SAFE RECYCLE
    // =====================================================

    private void recycleNode(
            AccessibilityNodeInfo node
    ) {

        try {

            if (node != null)
                node.recycle();

        } catch (Exception ignored) {}
    }

    // =====================================================
    // SAFE SLEEP
    // =====================================================

    private void sleep(long ms) {

        try {

            Thread.sleep(ms);

        } catch (Exception ignored) {}
    }
}
