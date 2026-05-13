package org.zauto;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.SslErrorHandler;
import android.net.http.SslError;
import android.widget.FrameLayout;
import android.view.ViewGroup;
import android.view.View;
import android.util.Log;
import java.lang.ref.WeakReference;
import java.util.concurrent.ConcurrentLinkedQueue;

public class ZaloWebManager {

    public static WebView hiddenWebView;
    public static FrameLayout webLayout;
    private static final String TAG = "ZAutoWebManager";
    
    private static Handler watchdogHandler;
    private static Runnable watchdogRunnable;
    public static long lastHeartbeat = System.currentTimeMillis();
    
    private static long lastReloadTime = 0; 
    private static int reloadCountWindow = 0;
    private static long firstReloadInWindow = 0;
    
    private static WeakReference<Activity> activityRef;

    private static final ConcurrentLinkedQueue<Runnable> replyQueue = new ConcurrentLinkedQueue<>();
    private static boolean isSending = false;

    private static void processReplyQueue() {
        if (isSending || replyQueue.isEmpty()) return;
        isSending = true;
        
        Runnable task = replyQueue.poll();
        if (task != null) {
            task.run(); 
            new Handler(Looper.getMainLooper()).postDelayed(() -> {
                isSending = false;
                processReplyQueue(); 
            }, 2500);
        } else {
            isSending = false;
        }
    }

    private static String escapeJs(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("'", "\\'").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "");
    }

    private static void safeEvaluateJs(String js) {
        if (hiddenWebView != null && hiddenWebView.getParent() != null) {
            hiddenWebView.evaluateJavascript(js, null);
        }
    }

    public static void safeReload() {
        long now = System.currentTimeMillis();
        if (now - firstReloadInWindow > 60000) {
            reloadCountWindow = 0;
            firstReloadInWindow = now;
        }
        if (reloadCountWindow >= 3) {
            Log.e(TAG, "ANTI-LOOP: Blocked too many reloads!");
            return;
        }
        
        if (now - lastReloadTime > 15000) { 
            Log.w(TAG, "PERFORMING SAFE RELOAD...");
            reloadCountWindow++;
            if (hiddenWebView != null) {
                hiddenWebView.post(() -> hiddenWebView.reload());
            }
            lastReloadTime = now;
        }
    }

    public static void sendReplyToSpecificMessage(final Activity activity, final String conversationId, final String msgId, final String text, final String groupName) {
        Activity safeActivity = activityRef != null ? activityRef.get() : activity;
        if (safeActivity == null || hiddenWebView == null) return;

        replyQueue.add(() -> {
            safeActivity.runOnUiThread(() -> {
                try {
                    String js = "if(typeof window.zautoSendReply === 'function') { " +
                                "window.zautoSendReply('" + escapeJs(conversationId) + "', '" + 
                                escapeJs(msgId) + "', '" + escapeJs(text) + "', '" + escapeJs(groupName) + "'); }";
                    safeEvaluateJs(js);
                } catch (Exception e) { Log.e(TAG, "Reply Engine Error", e); }
            });
        });
        
        safeActivity.runOnUiThread(ZaloWebManager::processReplyQueue);
    }

    public static class WebAppInterface {
        Context mContext;
        WebAppInterface(Context c) { mContext = c; }

        @JavascriptInterface
        public void onHeartbeat(String ts) {
            lastHeartbeat = System.currentTimeMillis();
        }

        @JavascriptInterface
        public void onLoginSuccess(String name, String avatar) {
            try {
                Intent intent = new Intent("org.zauto.LOGIN_SUCCESS");
                intent.setPackage(mContext.getPackageName());
                intent.putExtra("zalo_name", name);
                intent.putExtra("zalo_avatar", avatar);
                mContext.sendBroadcast(intent);
            } catch (Exception e) {}
        }

        @JavascriptInterface
        public void onNewWebMsg(String group, String msg, String msgId, String conversationId) {
            try {
                Intent intent = new Intent("org.zauto.WEB_NEW_MSG");
                intent.setPackage(mContext.getPackageName());
                intent.putExtra("group", group);
                intent.putExtra("msg", msg);
                intent.putExtra("msg_id", msgId);
                intent.putExtra("conversation_id", conversationId);
                mContext.sendBroadcast(intent);
            } catch (Exception e) {}
        }

        @JavascriptInterface
        public void onGroupListReceived(String jsonGroups) {
            try {
                Intent intent = new Intent("org.zauto.GROUPS_DATA");
                intent.setPackage(mContext.getPackageName());
                intent.putExtra("groups_list", jsonGroups);
                mContext.sendBroadcast(intent);
            } catch (Exception e) {}
        }
    }

    public static void initWebView(final Activity activity) {
        if (activity == null) return;
        activityRef = new WeakReference<>(activity); 
        
        activity.runOnUiThread(() -> {
            try {
                if (hiddenWebView != null) return;

                webLayout = new FrameLayout(activity);
                hiddenWebView = new WebView(activity);
                
                // FIX 3: Tránh lỗi trắng màn hình do Hardware Acceleration trên Android 13/14
                hiddenWebView.setLayerType(View.LAYER_TYPE_NONE, null);

                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    hiddenWebView.setRendererPriorityPolicy(WebView.RENDERER_PRIORITY_IMPORTANT, true);
                }

                WebSettings settings = hiddenWebView.getSettings();
                settings.setJavaScriptEnabled(true);
                settings.setDomStorageEnabled(true);
                settings.setDatabaseEnabled(true);
                settings.setAllowFileAccess(true);
                settings.setLoadsImagesAutomatically(true);
                settings.setMediaPlaybackRequiresUserGesture(false);
                settings.setOffscreenPreRaster(true); 

                // FIX 4: Tương thích Android 14+
                settings.setCacheMode(WebSettings.LOAD_DEFAULT);
                settings.setNeedInitialFocus(false);
                if (android.os.Build.VERSION.SDK_INT >= 29) {
                    settings.setForceDark(WebSettings.FORCE_DARK_OFF);
                }

                settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
                settings.setUseWideViewPort(true);
                settings.setLoadWithOverviewMode(true);
                
                // FIX 8: Cập nhật UA mới nhất nhưng dùng bản Desktop để tránh Zalo block mã QR
                settings.setUserAgentString("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36");

                CookieManager cookieManager = CookieManager.getInstance();
                cookieManager.setAcceptCookie(true);
                cookieManager.setAcceptThirdPartyCookies(hiddenWebView, true);

                hiddenWebView.addJavascriptInterface(new WebAppInterface(activity), "ZAutoBridge");
                hiddenWebView.setWebChromeClient(new WebChromeClient());
                
                hiddenWebView.setWebViewClient(new WebViewClient() {
                    @Override
                    public void onPageFinished(WebView view, String url) {
                        super.onPageFinished(view, url);
                        CookieManager.getInstance().flush();
                        
                        view.postDelayed(() -> {
                            try {
                                if (hiddenWebView != null) injectRealtimeObserver(hiddenWebView);
                            } catch (Exception e) {}
                        }, 5000);
                    }

                    @Override
                    public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                        if (request.isForMainFrame()) safeReload();
                    }

                    // FIX 2: Không hủy toàn bộ SSL, xử lý riêng SSL_UNTRUSTED
                    @Override
                    public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                        int type = error.getPrimaryError();
                        if (type == SslError.SSL_UNTRUSTED) {
                            Log.e(TAG, "SSL UNTRUSTED: " + error.toString());
                            handler.cancel();
                        } else {
                            handler.proceed();
                        }
                    }

                    @Override
                    public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                        Log.e(TAG, "WEBVIEW RENDER DEAD. RECOVERING...");
                        if (webLayout != null) webLayout.removeAllViews(); 
                        if (hiddenWebView != null) {
                            hiddenWebView.destroy();
                            hiddenWebView = null;
                        }
                        Activity act = activityRef.get();
                        if (act != null) initWebView(act);
                        return true;
                    }
                });

                hiddenWebView.loadUrl("https://id.zalo.me/account?continue=https://chat.zalo.me");
                
                // FIX ĐOẠN QUAN TRỌNG NHẤT: BỐ CỤC WEBVIEW ĐỂ LOAD QR CHUẨN
                FrameLayout.LayoutParams webParams = new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                );
                webLayout.addView(hiddenWebView, webParams);

                FrameLayout.LayoutParams rootParams = new FrameLayout.LayoutParams(2, 2);
                webLayout.setAlpha(0.05f);

                // FIX 5: Kiểm tra View Parent để tránh crash "View already has a parent"
                if (webLayout.getParent() != null) {
                    ((ViewGroup) webLayout.getParent()).removeView(webLayout);
                }

                activity.addContentView(webLayout, rootParams);

                // FIX 7: Bắt buộc WebView hiện lên mặt trước để Android cấp tài nguyên vẽ QR
                hiddenWebView.setVisibility(View.VISIBLE);
                hiddenWebView.bringToFront();
                hiddenWebView.requestFocus();
                
                startWatchdog(); 

            } catch (Exception e) { Log.e(TAG, "Init Error", e); }
        });
    }

    public static void injectRealtimeObserver(WebView view) {
        String jsPayload = 
            "(function() {" +
            "   if(window.zauto_started) return;" +
            "   window.zauto_started = true;" +
            "   window.zauto_cache = {};" +
            "   window.zauto_cache_keys = [];" + 
            "   window.zauto_observer = null;" +
            "   window.zauto_observer_target = null;" +
            
            "   window.zautoSendReply = function(convId, msgId, text, groupName) {" +
            "       try {" +
            "           let chatNode = document.getElementById(convId) || document.querySelector('.conv-item[title=\"' + groupName + '\"]') || document.querySelector('.conv-item.active') || document.querySelector('.conv-item.selected');" +
            "           if(chatNode && !chatNode.classList.contains('active') && !chatNode.classList.contains('selected')) chatNode.click();" +
            "           setTimeout(() => {" +
            "               let input = document.getElementById('richInput') || document.querySelector('.chat-input');" +
            "               if(!input) return;" +
            "               input.focus();" +
            "               if(document.execCommand) { document.execCommand('insertText', false, text); }" +
            "               input.innerHTML = text; input.textContent = text;" + 
            "               input.dispatchEvent(new InputEvent('input', {bubbles:true}));" +
            "               setTimeout(() => {" +
            "                   ['keydown', 'keypress', 'keyup'].forEach(type => {" +
            "                       let evt = new KeyboardEvent(type, {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true});" +
            "                       input.dispatchEvent(evt);" +
            "                   });" +
            "                   setTimeout(() => {" +
            "                       let btn = document.querySelector('.btn-send, [icon=\"icn-send\"]');" +
            "                       if(btn) btn.click();" +
            "                   }, 100);" +
            "               }, 300);" +
            "           }, 600);" +
            "       } catch(e) {}" +
            "   };" +

            "   function sendMessage(node) {" +
            "       try {" +
            "           if(node.dataset.zauto_done === '1') return;" +
            "           node.dataset.zauto_done = '1';" +
            
            "           let text = node.innerText || node.textContent || '';" +
            "           if(!text || text.length < 1) return;" +
            "           let groupName = 'Nhóm Zalo';" +
            "           let header = document.querySelector('.chat-box-head__title') || document.querySelector('.header-title');" +
            "           if(header) groupName = header.innerText || header.textContent;" +
            
            "           let msgId = node.getAttribute('data-id') || node.id;" +
            "           let fingerprint = msgId ? msgId : (groupName + '|' + text.substring(0, Math.min(text.length, 20)));" + 
            
            "           if(window.zauto_cache[fingerprint]) return;" +
            "           window.zauto_cache[fingerprint] = true;" +
            "           window.zauto_cache_keys.push(fingerprint);" + 
            
            "           let activeConv = document.querySelector('.conv-item.active') || document.querySelector('.conv-item.selected');" +
            "           let conversationId = activeConv ? activeConv.getAttribute('id') : '';" +
            
            "           if(!text.includes('Ok nhận')) {" +
            "               ZAutoBridge.onNewWebMsg(groupName, text, msgId || '', conversationId);" +
            "           }" +
            "       } catch(e) {}" +
            "   }" +

            "   window.startObserver = function() {" +
            "       let chatContainer = document.querySelector('.chat-box-content');" +
            "       if(!chatContainer) return;" +
            
            "       window.zauto_observer_target = chatContainer;" +
            "       if(window.zauto_observer) window.zauto_observer.disconnect();" +
            
            "       window.zauto_observer = new MutationObserver((mutations) => {" +
            "           mutations.forEach((mutation) => {" +
            "               mutation.addedNodes.forEach((node) => {" +
            "                   try {" +
            "                       if(node.nodeType !== 1) return;" +
            "                       if((node.matches && (node.matches('.msg-item') || node.matches('[data-id]'))) || (node.classList && node.classList.contains('message-item'))) {" +
            "                           sendMessage(node);" +
            "                       }" +
            "                       if(node.querySelectorAll) {" +
            "                           let nested = node.querySelectorAll('[data-id]');" +
            "                           nested.forEach(sendMessage);" +
            "                       }" +
            "                   } catch(err) {}" +
            "               });" +
            "           });" +
            "       });" +
            "       window.zauto_observer.observe(chatContainer, {childList: true, subtree: true});" +
            "       ZAutoBridge.onLoginSuccess('Đã kết nối', '');" +
            "   };" +

            "   function systemWatchdog() {" +
            "       ZAutoBridge.onHeartbeat(Date.now().toString());" + 
            "       if(!navigator.onLine) return;" +
            
            "       if(location.href.includes('login') || document.querySelector('.qrcode')) {" +
            "           window.last_login_reload = window.last_login_reload || 0;" +
            "           if(Date.now() - window.last_login_reload > 60000) {" +
            "               window.last_login_reload = Date.now();" +
            "               location.reload();" +
            "           }" +
            "       }" +

            "       if(window.zauto_cache_keys.length > 1000) {" +
            "           let toRemove = window.zauto_cache_keys.splice(0, 100);" + 
            "           toRemove.forEach(k => delete window.zauto_cache[k]);" +
            "       }" +

            "       if(window.zauto_observer_target && !document.body.contains(window.zauto_observer_target)) {" +
            "           window.startObserver();" +
            "       }" +
            
            "       let nextInterval = document.hidden ? 15000 : 3000;" + 
            "       setTimeout(systemWatchdog, nextInterval);" +
            "   };" +
            "   setTimeout(systemWatchdog, 3000);" + 
            
            "   setTimeout(() => {" +
            "       let first = document.querySelector('.conv-item');" + 
            "       if(first) first.click();" +
            "       setTimeout(window.startObserver, 2000);" +
            "   }, 3000);" +
            "})();";

        safeEvaluateJs(jsPayload);
    }

    private static void startWatchdog() {
        if (watchdogHandler == null) watchdogHandler = new Handler(Looper.getMainLooper());
        if (watchdogRunnable != null) watchdogHandler.removeCallbacks(watchdogRunnable);
        
        watchdogRunnable = new Runnable() {
            @Override
            public void run() {
                if (hiddenWebView != null) {
                    long now = System.currentTimeMillis();
                    if (now - lastHeartbeat > 60000) {
                        Log.e(TAG, "HEARTBEAT LOST. REQUESTING RELOAD...");
                        safeReload();
                    } else if (now - lastHeartbeat > 20000) {
                        safeEvaluateJs("(function(){return !!window.zauto_started})()");
                    }
                }
                watchdogHandler.postDelayed(this, 15000); 
            }
        };
        watchdogHandler.postDelayed(watchdogRunnable, 15000);
    }

    public static void destroy() {
        if (watchdogHandler != null && watchdogRunnable != null) {
            watchdogHandler.removeCallbacks(watchdogRunnable);
        }
        replyQueue.clear();
        if (webLayout != null) {
            webLayout.removeAllViews();
            webLayout = null;
        }
        if (hiddenWebView != null) {
            hiddenWebView.clearHistory();
            hiddenWebView.clearCache(true);
            hiddenWebView.destroy();
            hiddenWebView = null;
        }
        if (activityRef != null) {
            activityRef.clear();
            activityRef = null;
        }
    }

    public static void updateWebViewBounds(final Activity activity, final int x, final int y, final int width, final int height, final boolean visible) {
        Activity safeActivity = activityRef != null ? activityRef.get() : activity;
        if (safeActivity == null) return;
        
        safeActivity.runOnUiThread(() -> {
            try {
                if (webLayout != null) {
                    if (!visible) {
                        webLayout.setAlpha(0.05f); 
                        FrameLayout.LayoutParams params = (FrameLayout.LayoutParams) webLayout.getLayoutParams();
                        params.leftMargin = 0; params.topMargin = 0; params.width = 2; params.height = 2;
                        webLayout.setLayoutParams(params);
                    } else {
                        webLayout.setAlpha(1.0f);
                        FrameLayout.LayoutParams params = (FrameLayout.LayoutParams) webLayout.getLayoutParams();
                        params.leftMargin = x; params.topMargin = y; params.width = width; params.height = height;
                        webLayout.setLayoutParams(params);
                        
                        // FIX 6: Force Redraw
                        if (hiddenWebView != null) {
                            hiddenWebView.invalidate();
                            hiddenWebView.requestLayout();
                        }
                    }
                }
            } catch (Exception e) {}
        });
    }

    public static void reloadWeb(final Activity activity) {
        safeReload();
    }

    // FIX 1: Chống treo Chromium khi Pause
    public static void onResume(final Activity activity) {
        Activity safeActivity = activityRef != null ? activityRef.get() : activity;
        if (safeActivity == null) return;
        safeActivity.runOnUiThread(() -> {
            try {
                if (hiddenWebView != null) {
                    hiddenWebView.onResume();
                }
            } catch (Exception ignored) {}
        });
    }

    public static void onPause() {
        if (hiddenWebView != null) {
            try {
                hiddenWebView.onPause();
            } catch (Exception ignored) {}
        }
    }
}
