```java
package org.zauto;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import android.graphics.Path;
import android.graphics.Rect;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;

import android.util.Log;

import java.util.LinkedList;
import java.util.List;
import java.util.Queue;

public class ZaloAccessibility extends AccessibilityService {

    public static ZaloAccessibility instance;

    private static final String TAG = "ZAutoVIP";

    private final Handler handler = new Handler(Looper.getMainLooper());

    private boolean isBusy = false;

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();

        instance = this;

        Log.d(TAG, "Accessibility Connected");
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {

    }

    @Override
    public void onInterrupt() {

    }

    // =====================================================
    // MAIN REPLY
    // =====================================================

    public boolean executeReplyContext(
            final String groupName,
            final String replyText
    ) {

        if (isBusy) {
            Log.d(TAG, "BUSY");
            return false;
        }

        isBusy = true;

        handler.post(() -> {

            try {

                openGroupAndReply(groupName, replyText);

            } catch (Exception e) {

                Log.e(TAG, "ERROR: " + e.getMessage());

                isBusy = false;
            }

        });

        return true;
    }

    // =====================================================
    // STEP 1
    // =====================================================

    private void openGroupAndReply(
            final String groupName,
            final String replyText
    ) {

        AccessibilityNodeInfo root = getRootWithRetry();

        if (root == null) {
            isBusy = false;
            return;
        }

        AccessibilityNodeInfo groupNode = findNodeContainsText(root, groupName);

        if (groupNode == null) {

            Log.d(TAG, "Không tìm thấy nhóm");

            isBusy = false;
            return;
        }

        AccessibilityNodeInfo clickable = getClickableParent(groupNode);

        if (clickable == null) {

            isBusy = false;
            return;
        }

        clickable.performAction(AccessibilityNodeInfo.ACTION_CLICK);

        handler.postDelayed(() -> {

            focusInputAndSend(replyText);

        }, 1200);
    }

    // =====================================================
    // STEP 2
    // =====================================================

    private void focusInputAndSend(String replyText) {

        AccessibilityNodeInfo root = getRootWithRetry();

        if (root == null) {

            backHome();

            return;
        }

        AccessibilityNodeInfo input =
                findFirstEditText(root);

        if (input == null) {

            Log.d(TAG, "Không tìm thấy ô nhập");

            backHome();

            return;
        }

        input.performAction(
                AccessibilityNodeInfo.ACTION_FOCUS
        );

        Bundle args = new Bundle();

        args.putCharSequence(
                AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                replyText
        );

        input.performAction(
                AccessibilityNodeInfo.ACTION_SET_TEXT,
                args
        );

        handler.postDelayed(() -> {

            clickSendButton(input);

        }, 500);
    }

    // =====================================================
    // STEP 3
    // =====================================================

    private void clickSendButton(
            AccessibilityNodeInfo input
    ) {

        AccessibilityNodeInfo root = getRootWithRetry();

        if (root == null) {

            backHome();

            return;
        }

        AccessibilityNodeInfo sendBtn =
                findSendButton(root);

        if (sendBtn != null) {

            sendBtn.performAction(
                    AccessibilityNodeInfo.ACTION_CLICK
            );

            Log.d(TAG, "Đã gửi");

        } else {

            Log.d(TAG, "Không tìm thấy nút gửi");

        }

        handler.postDelayed(() -> {

            backHome();

        }, 800);
    }

    // =====================================================
    // BACK
    // =====================================================

    private void backHome() {

        performGlobalAction(GLOBAL_ACTION_BACK);

        handler.postDelayed(() -> {

            isBusy = false;

        }, 600);
    }

    // =====================================================
    // RETRY ROOT
    // =====================================================

    private AccessibilityNodeInfo getRootWithRetry() {

        for (int i = 0; i < 5; i++) {

            AccessibilityNodeInfo root =
                    getRootInActiveWindow();

            if (root != null) {
                return root;
            }

            try {
                Thread.sleep(200);
            } catch (Exception e) {

            }
        }

        return null;
    }

    // =====================================================
    // FIND TEXT
    // =====================================================

    private AccessibilityNodeInfo findNodeContainsText(
            AccessibilityNodeInfo root,
            String text
    ) {

        Queue<AccessibilityNodeInfo> queue =
                new LinkedList<>();

        queue.add(root);

        while (!queue.isEmpty()) {

            AccessibilityNodeInfo node = queue.poll();

            if (node == null) continue;

            CharSequence cs = node.getText();

            if (cs != null) {

                String value =
                        cs.toString().toLowerCase();

                if (value.contains(
                        text.toLowerCase()
                )) {

                    return node;
                }
            }

            for (int i = 0;
                 i < node.getChildCount();
                 i++) {

                queue.add(node.getChild(i));
            }
        }

        return null;
    }

    // =====================================================
    // FIND EDITTEXT
    // =====================================================

    private AccessibilityNodeInfo findFirstEditText(
            AccessibilityNodeInfo root
    ) {

        Queue<AccessibilityNodeInfo> queue =
                new LinkedList<>();

        queue.add(root);

        while (!queue.isEmpty()) {

            AccessibilityNodeInfo node = queue.poll();

            if (node == null) continue;

            if (node.getClassName() != null &&
                    node.getClassName()
                            .toString()
                            .contains("EditText")) {

                return node;
            }

            for (int i = 0;
                 i < node.getChildCount();
                 i++) {

                queue.add(node.getChild(i));
            }
        }

        return null;
    }

    // =====================================================
    // FIND SEND BUTTON
    // =====================================================

    private AccessibilityNodeInfo findSendButton(
            AccessibilityNodeInfo root
    ) {

        Queue<AccessibilityNodeInfo> queue =
                new LinkedList<>();

        queue.add(root);

        while (!queue.isEmpty()) {

            AccessibilityNodeInfo node = queue.poll();

            if (node == null) continue;

            CharSequence desc =
                    node.getContentDescription();

            String viewId =
                    node.getViewIdResourceName();

            // contentDescription
            if (desc != null) {

                String d =
                        desc.toString().toLowerCase();

                if (d.contains("gửi")
                        || d.contains("send")) {

                    return node;
                }
            }

            // resource id
            if (viewId != null) {

                String id =
                        viewId.toLowerCase();

                if (id.contains("send")) {

                    return node;
                }
            }

            // clickable icon
            if (node.isClickable()
                    && node.isEnabled()
                    && node.isVisibleToUser()) {

                Rect r = new Rect();

                node.getBoundsInScreen(r);

                if (r.width() < 250
                        && r.height() < 250
                        && r.right > 700) {

                    return node;
                }
            }

            for (int i = 0;
                 i < node.getChildCount();
                 i++) {

                queue.add(node.getChild(i));
            }
        }

        return null;
    }

    // =====================================================
    // CLICKABLE PARENT
    // =====================================================

    private AccessibilityNodeInfo getClickableParent(
            AccessibilityNodeInfo node
    ) {

        AccessibilityNodeInfo p = node;

        for (int i = 0; i < 6; i++) {

            if (p == null) return null;

            if (p.isClickable()) {

                return p;
            }

            p = p.getParent();
        }

        return null;
    }

}
```
