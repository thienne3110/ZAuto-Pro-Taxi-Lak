package org.zauto;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.os.Bundle;
import android.graphics.Rect;
import java.util.LinkedList;
import java.util.Queue;

public class ZaloAccessibility extends AccessibilityService {
    public static ZaloAccessibility instance;
    private AccessibilityNodeInfo cachedInputBox = null; 

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {}
    @Override
    public void onInterrupt() {}

    public boolean simulateHumanTyping(final String text) {
        try {
            if (cachedInputBox == null || !cachedInputBox.refresh()) {
                AccessibilityNodeInfo root = getRootInActiveWindow();
                cachedInputBox = findNodeByClassBFS(root, "android.widget.EditText");
                if (root != null) root.recycle();
            }
            if (cachedInputBox == null) return false;

            cachedInputBox.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
            Thread.sleep(300);
            Rect inputRect = new Rect();
            cachedInputBox.getBoundsInScreen(inputRect);

            ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            StringBuilder currentText = new StringBuilder();

            for (int i = 0; i < text.length(); i++) {
                currentText.append(text.charAt(i));
                String typingText = currentText.toString();

                ClipData clip = ClipData.newPlainText("zauto", typingText);
                clipboard.setPrimaryClip(clip);
                cachedInputBox.performAction(AccessibilityNodeInfo.ACTION_PASTE);
                Thread.sleep(50);

                AccessibilityNodeInfo testSend = findSendButtonBySpatial(cachedInputBox, inputRect);
                if (testSend == null || !testSend.isEnabled()) {
                    Bundle arguments = new Bundle();
                    arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, typingText);
                    cachedInputBox.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments);
                }
                if (testSend != null) testSend.recycle();
                Thread.sleep((long)(Math.random() * 80 + 30)); 
            }

            Thread.sleep(500);

            AccessibilityNodeInfo sendBtn = findSendButtonBySpatial(cachedInputBox, inputRect);
            boolean isSent = false;
            if (sendBtn != null) {
                sendBtn.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                isSent = true;
                sendBtn.recycle();
            }
            return isSent;
        } catch (Exception e) { return false; }
    }

    private AccessibilityNodeInfo findNodeByClassBFS(AccessibilityNodeInfo root, String className) {
        if (root == null) return null;
        Queue<AccessibilityNodeInfo> queue = new LinkedList<>();
        queue.add(root);
        int count = 0;
        while (!queue.isEmpty() && count < 200) { 
            AccessibilityNodeInfo node = queue.poll();
            if (node == null) continue;
            if (className.equals(node.getClassName().toString())) return node;
            for (int i = 0; i < node.getChildCount(); i++) {
                AccessibilityNodeInfo child = node.getChild(i);
                if (child != null) queue.add(child);
            }
            count++;
        }
        return null;
    }

    private AccessibilityNodeInfo findSendButtonBySpatial(AccessibilityNodeInfo inputBox, Rect inputRect) {
        if (inputBox == null) return null;
        AccessibilityNodeInfo p = inputBox;
        
        for (int level = 0; level < 3; level++) {
            p = p.getParent();
            if (p == null) break;
            for (int i = 0; i < p.getChildCount(); i++) {
                AccessibilityNodeInfo sibling = p.getChild(i);
                if (sibling == null || sibling.equals(inputBox)) continue;
                if (sibling.isClickable() && sibling.isEnabled()) {
                    Rect siblingRect = new Rect();
                    sibling.getBoundsInScreen(siblingRect);
                    int diffY = Math.abs(siblingRect.centerY() - inputRect.centerY());
                    if (siblingRect.left > inputRect.right && diffY < 80) {
                        return sibling; 
                    }
                }
            }
        }
        return null;
    }
}
