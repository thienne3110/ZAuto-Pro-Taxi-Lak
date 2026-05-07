package org.zauto;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.os.Bundle;
import android.util.Log;
import java.util.LinkedList;
import java.util.Queue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class ZaloAccessibility extends AccessibilityService {
    public static ZaloAccessibility instance;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    @Override
    protected void onServiceConnected() { super.onServiceConnected(); instance = this; }
    @Override public void onAccessibilityEvent(AccessibilityEvent event) {}
    @Override public void onInterrupt() {}

    public void executeReplyContext(final String groupName, final String replyText) {
        executor.execute(() -> {
            AccessibilityNodeInfo root = null, targetGroup = null, inputBox = null, sendBtn = null;
            try {
                root = waitForStableRoot(3000);
                if (root == null || !"com.zing.zalo".equals(root.getPackageName().toString())) return;

                targetGroup = findNodeByTextBFS(root, groupName);
                if (targetGroup != null) {
                    AccessibilityNodeInfo clickable = getClickableParent(targetGroup);
                    if (clickable != null) {
                        clickable.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                        clickable.recycle();
                    }
                    Thread.sleep(1000); // Chờ UI Load
                } else return; 

                root.recycle(); 
                root = waitForStableRoot(2000);
                if (root == null) return;

                inputBox = findNodeByClassBFS(root, "android.widget.EditText");
                if (inputBox != null) {
                    Bundle args = new Bundle();
                    args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, replyText);
                    inputBox.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);
                    Thread.sleep(300);
                }

                sendBtn = findNodeByDescOrTextBFS(root, "Gửi");
                if (sendBtn != null && sendBtn.isClickable()) {
                    sendBtn.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                    Thread.sleep(500);
                }

                performGlobalAction(GLOBAL_ACTION_BACK);

            } catch (Exception e) {
                Log.e("ZAuto", "A11y Crash: " + e.getMessage());
            } finally {
                if (root != null) root.recycle();
                if (targetGroup != null) targetGroup.recycle();
                if (inputBox != null) inputBox.recycle();
                if (sendBtn != null) sendBtn.recycle();
            }
        });
    }

    private AccessibilityNodeInfo waitForStableRoot(int timeoutMs) throws InterruptedException {
        int waited = 0;
        while (waited < timeoutMs) {
            AccessibilityNodeInfo root = getRootInActiveWindow();
            if (root != null) return root;
            Thread.sleep(200);
            waited += 200;
        }
        return null;
    }

    private AccessibilityNodeInfo findNodeByTextBFS(AccessibilityNodeInfo root, String text) {
        if (root == null) return null;
        Queue<AccessibilityNodeInfo> q = new LinkedList<>();
        q.add(root);
        while (!q.isEmpty()) {
            AccessibilityNodeInfo node = q.poll();
            if (node.getText() != null && node.getText().toString().equals(text)) return node;
            for (int i = 0; i < node.getChildCount(); i++) {
                AccessibilityNodeInfo child = node.getChild(i);
                if (child != null) q.add(child);
            }
        }
        return null;
    }

    private AccessibilityNodeInfo findNodeByClassBFS(AccessibilityNodeInfo root, String cls) {
        if (root == null) return null;
        Queue<AccessibilityNodeInfo> q = new LinkedList<>();
        q.add(root);
        while (!q.isEmpty()) {
            AccessibilityNodeInfo node = q.poll();
            if (node.getClassName() != null && node.getClassName().toString().equals(cls)) return node;
            for (int i = 0; i < node.getChildCount(); i++) {
                AccessibilityNodeInfo child = node.getChild(i);
                if (child != null) q.add(child);
            }
        }
        return null;
    }

    private AccessibilityNodeInfo findNodeByDescOrTextBFS(AccessibilityNodeInfo root, String target) {
        if (root == null) return null;
        Queue<AccessibilityNodeInfo> q = new LinkedList<>();
        q.add(root);
        while (!q.isEmpty()) {
            AccessibilityNodeInfo node = q.poll();
            CharSequence desc = node.getContentDescription();
            CharSequence text = node.getText();
            if ((desc != null && desc.toString().contains(target)) || (text != null && text.toString().equals(target))) return node;
            for (int i = 0; i < node.getChildCount(); i++) {
                AccessibilityNodeInfo child = node.getChild(i);
                if (child != null) q.add(child);
            }
        }
        return null;
    }

    private AccessibilityNodeInfo getClickableParent(AccessibilityNodeInfo node) {
        AccessibilityNodeInfo p = node;
        for (int i = 0; i < 5; i++) {
            if (p == null) return null;
            if (p.isClickable()) return p;
            p = p.getParent();
        }
        return null;
    }
}
