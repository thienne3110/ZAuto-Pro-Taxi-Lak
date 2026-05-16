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
import android.speech.tts.TextToSpeech;
import java.util.Locale;

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

    // =========================================================
    // ỐNG DẪN RAM SIÊU TỐC (BYPASS ANDROID 14 BROADCAST BAN)
    // =========================================================
    public static final ConcurrentLinkedQueue<String> pythonMsgQueue = new ConcurrentLinkedQueue<>();
    public static TextToSpeech tts;
    // =========================================================
    // REPLY QUEUE
    // =========================================================
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
        return s.replace("\\", "\\\\")
                .replace("'", "\\'")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "");
    }

    private static void safeEvaluateJs(String js) {
        if (hiddenWebView != null && hiddenWebView.getParent() != null) {
            hiddenWebView.post(() -> hiddenWebView.evaluateJavascript(js, null));
        }
    }

    // =========================================================
    // SAFE RELOAD 
    // =========================================================
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

    // =========================================================
    // GỬI TIN NHẮN REPLY VÀO NHÓM CỤ THỂ
    // =========================================================
    public static void sendReplyToSpecificMessage(
            final Activity activity,
            final String conversationId,
            final String msgId,
            final String text,
            final String groupName) {

        Activity safeActivity = activityRef != null ? activityRef.get() : activity;
        if (safeActivity == null || hiddenWebView == null) return;

        replyQueue.add(() -> safeActivity.runOnUiThread(() -> {
            try {
                String js = "if(typeof window.zautoSendReply === 'function') { " +
                        "window.zautoSendReply('" + escapeJs(conversationId) + "', '" +
                        escapeJs(msgId) + "', '" + escapeJs(text) + "', '" + escapeJs(groupName) + "'); }";
                safeEvaluateJs(js);
            } catch (Exception e) {
                Log.e(TAG, "Reply Engine Error", e);
            }
        }));

        safeActivity.runOnUiThread(ZaloWebManager::processReplyQueue);
    }

    // =========================================================
    // JAVA BRIDGE → NÉM VÀO RAM PYTHON THAY VÌ BROADCAST
    // =========================================================
    public static class WebAppInterface {
        Context mContext;
        WebAppInterface(Context c) { mContext = c; }

        @JavascriptInterface
        public void onHeartbeat(String ts) {
            lastHeartbeat = System.currentTimeMillis();
        }

        @JavascriptInterface
        public void onLoginSuccess(String name, String avatar) {
            pythonMsgQueue.add("LOGIN_SUCCESS|||" + name + "|||" + avatar);
        }

        @JavascriptInterface
        public void onNewWebMsg(String group, String msg, String msgId, String conversationId) {
            pythonMsgQueue.add("WEB_NEW_MSG|||" + group + "|||" + msg + "|||" + msgId + "|||" + conversationId);
        }

        @JavascriptInterface
        public void onGroupListReceived(String jsonGroups) {
            pythonMsgQueue.add("GROUPS_DATA|||" + jsonGroups);
        }
    }

    // =========================================================
    // KHỞI TẠO WEBVIEW (BẢN FIX CHUẨN TƯƠNG THÍCH MỌI ANDROID)
    // =========================================================
    public static void initWebView(final Activity activity) {
        if (activity == null) return;
        activityRef = new WeakReference<>(activity);

        activity.runOnUiThread(() -> {
            try {
                if (hiddenWebView != null) return;

                webLayout = new FrameLayout(activity);
                hiddenWebView = new WebView(activity);

                // FIX 1: Ép phần cứng render, cấm hệ điều hành Android cũ cho WebView ngủ đông
                hiddenWebView.setLayerType(View.LAYER_TYPE_HARDWARE, null);

                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    hiddenWebView.setRendererPriorityPolicy(WebView.RENDERER_PRIORITY_IMPORTANT, true);
                }

                WebSettings settings = hiddenWebView.getSettings();
                settings.setJavaScriptEnabled(true);
                settings.setDomStorageEnabled(true); // BẮT BUỘC: Cho Zalo lưu LocalStorage
                settings.setDatabaseEnabled(true);
                settings.setAllowFileAccess(true);
                
                // Bổ sung cởi trói bảo mật truy cập nội bộ cho Android cũ
                settings.setAllowContentAccess(true);
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.JELLY_BEAN) {
                    settings.setAllowFileAccessFromFileURLs(true);
                    settings.setAllowUniversalAccessFromFileURLs(true);
                }
                
                settings.setLoadsImagesAutomatically(true);
                settings.setMediaPlaybackRequiresUserGesture(false);
                settings.setOffscreenPreRaster(true); // QUAN TRỌNG: Ép load ngầm
                settings.setCacheMode(WebSettings.LOAD_DEFAULT);
                settings.setNeedInitialFocus(false);
                if (android.os.Build.VERSION.SDK_INT >= 29) {
                    settings.setForceDark(WebSettings.FORCE_DARK_OFF);
                }
                
                // BẮT BUỘC: Cho phép HTTP tải tài nguyên bên trong HTTPS (Tránh lỗi Zalo load thiếu ảnh)
                settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
                settings.setUseWideViewPort(true);
                settings.setLoadWithOverviewMode(true);
                settings.setUserAgentString(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
                );

                CookieManager cookieManager = CookieManager.getInstance();
                cookieManager.setAcceptCookie(true);
                cookieManager.setAcceptThirdPartyCookies(hiddenWebView, true);

                hiddenWebView.addJavascriptInterface(new WebAppInterface(activity), "ZAutoBridge");
                hiddenWebView.setWebChromeClient(new WebChromeClient());

                hiddenWebView.setWebViewClient(new WebViewClient() {
                    
                    // FIX 2: BỎ QUA LỖI CHỨNG CHỈ BẢO MẬT SSL (Cứu sống màn hình trắng do chứng chỉ cũ trên máy cũ)
                    @Override
                    public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                        Log.w(TAG, "Bo qua loi SSL tren Android cu: " + error.toString());
                        handler.proceed(); // BẮT BUỘC PHẢI CÓ LỆNH NÀY!
                    }

                    @Override
                    public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                        if (request.isForMainFrame()) {
                            Log.e(TAG, "Lỗi kết nối Zalo: " + error.getDescription());
                            view.postDelayed(() -> {
                                if (view != null) view.reload();
                            }, 5000);
                        }
                    }

                    @Override
                    public void onPageFinished(WebView view, String url) {
                        super.onPageFinished(view, url);
                        CookieManager.getInstance().flush();
                        view.postDelayed(() -> {
                            try {
                                if (hiddenWebView != null) injectSidebarObserver(hiddenWebView);
                            } catch (Exception e) {
                                Log.e(TAG, "Inject Error", e);
                            }
                        }, 5000);
                    }
                    
                    @Override
                    public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                        Log.e(TAG, "WEBVIEW RENDER DEAD. RECOVERING...");
                        if (webLayout != null) webLayout.removeAllViews();
                        if (hiddenWebView != null) {
                            hiddenWebView.destroy();
                            hiddenWebView = null;
                        }
                        Activity act = activityRef != null ? activityRef.get() : null;
                        if (act != null) initWebView(act);
                        return true;
                    }
                });

                hiddenWebView.loadUrl("https://id.zalo.me/account?continue=https://chat.zalo.me");

                FrameLayout.LayoutParams webParams = new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                );
                webLayout.addView(hiddenWebView, webParams);

                // FIX 3: ĐÁNH LỪA ANDROID CŨ (Tránh View Clipping)
                FrameLayout.LayoutParams rootParams = new FrameLayout.LayoutParams(1080, 2400);
                rootParams.leftMargin = -2000; // Không để -10000 nữa, -2000 là đủ che khỏi màn hình rồi
                rootParams.topMargin = -2000;
                
                // QUAN TRỌNG NHẤT: Không để 0.0f, dùng 0.01f ép GPU Android cũ phải xử lý ngầm mã QR
                webLayout.setAlpha(0.01f); 

                if (webLayout.getParent() != null) {
                    ((ViewGroup) webLayout.getParent()).removeView(webLayout);
                }
                activity.addContentView(webLayout, rootParams);

                hiddenWebView.setVisibility(View.VISIBLE);
                hiddenWebView.bringToFront();
                hiddenWebView.requestFocus();

                if (tts == null) {
                    tts = new TextToSpeech(activity.getApplicationContext(), status -> {
                        if (status == TextToSpeech.SUCCESS) {
                            tts.setLanguage(new Locale("vi", "VN"));
                        }
                    });
                }

                startWatchdog();

            } catch (Exception e) {
                Log.e(TAG, "Init Error", e);
            }
        });
    }

    // =========================================================
    // JS OBSERVER & API INTERNAL (BẢN TỔNG HỢP CUỐI CÙNG - CHUẨN 100%)
    // =========================================================
    public static void injectSidebarObserver(WebView view) {
        String js =
            "(function() {" +
            "   if(window.zauto_started) return;" +
            "   window.zauto_started = true;" +
            "   window.zauto_boot_time = Date.now();" +
            "   window.zauto_seen = {};" +
            "   window.zauto_seen_keys = [];" +

            // 1. HÀM GỬI REPLY ĐA TẦNG (CHỈ QUOTE KHI LÀ ID THẬT CỦA ZALO)
            "   window.zautoSendReply = function(convId, fakeMsgId, text, groupName) {" +
            "       try {" +
            "           let item = document.querySelector('.msg-item[anim-data-id=\"'+convId+'\"] .conv-item');" +
            "           if(item) {" +
            "               let key = Object.keys(item).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
            "               if (key && item[key]) {" +
            "                   if (item[key].onClick) item[key].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
            "                   else if (item[key].return && item[key].return.memoizedProps.onClick) item[key].return.memoizedProps.onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
            "               } else { item.click(); }" +
            "           }" +
            
            "           setTimeout(() => {" +
            "               let realMsgId = fakeMsgId || '';" +
            "               if (window.zMessenger && typeof window.zMessenger.sendMessage === 'function') {" +
            "                   let req = { toid: convId, msg: text, type: 1 };" +
                                // CHIẾN THUẬT QUOTE CHUẨN: Chỉ đè tin nhắn nếu ID bắt đầu bằng "msg_"
            "                   if (realMsgId && realMsgId.startsWith('msg_')) {" +
            "                       req.quote_msgId = realMsgId;" +
            "                   }" +
            "                   window.zMessenger.sendMessage(req);" +
            "                   ZAutoBridge.onLoginSuccess('Đã chốt xong:', groupName);" + 
            "               } else {" +
            "                   let input = document.getElementById('richInput');" +
            "                   if(input) {" +
            "                       input.focus();" +
            "                       input.innerHTML = '';" +
            "                       document.execCommand('insertText', false, text);" +
            "                       input.dispatchEvent(new Event('input', {bubbles:true}));" + 
            "                       input.blur();" + 
            "                       let attempts = 0;" +
            "                       let trySend = setInterval(() => {" +
            "                           attempts++;" +
            "                           let btnSend = null;" +
            "                           let primarySelector = '#chat-input-container-id > div.chat-input-container__right-layout > div.normal-buttons-group > div.send-msg-btn';" +
            "                           let fallbackSelectors = ['.fa-Sent-msg_24_Line', '[data-translate-title=\"STR_SEND\"]'];" +
            "                           let el = document.querySelector(primarySelector);" +
            "                           if (el) { btnSend = el; } else {" +
            "                               for (let sel of fallbackSelectors) {" +
            "                                   let fallbackEl = document.querySelector(sel);" +
            "                                   if (fallbackEl) { btnSend = fallbackEl.closest('.z--btn--v2') || fallbackEl.parentElement || fallbackEl; break; }" +
            "                               }" +
            "                           }" +
            "                           if (btnSend) {" +
            "                               btnSend.click();" +
            "                               let key = Object.keys(btnSend).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
            "                               if(key && btnSend[key] && btnSend[key].onClick) btnSend[key].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
            "                           }" +
            "                           let enterEvent = new KeyboardEvent('keydown', { bubbles: true, cancelable: true, keyCode: 13, which: 13, key: 'Enter', code: 'Enter' });" +
            "                           input.dispatchEvent(enterEvent);" +
            "                           if (input.innerHTML === '' || input.innerHTML === '<br>') {" +
            "                               clearInterval(trySend);" +
            "                               ZAutoBridge.onLoginSuccess('Đã chốt xong:', groupName);" +
            "                           } else if (attempts > 12) { clearInterval(trySend); }" +
            "                       }, 250);" + 
            "                   }" +
            "               }" +
            "           }, 800);" + 
            "       } catch(e) {}" +
            "   };" +

            // 2. HÀM QUÉT SIDEBAR (FULL TEXT + VOICE + ỔN ĐỊNH RAM)
            "   function scanConvItem(msgItemEl) {" +
            "       try {" +
            "           let convItem = msgItemEl.querySelector('.conv-item') || msgItemEl;" +
            "           if(!convItem) return;" +
            "           let nameEl = convItem.querySelector('.conv-item-title__name');" +
            "           let bodyEl = convItem.querySelector('.conv-item-body');" +
            "           if(!nameEl || !bodyEl) return;" +
            "           let groupName = (nameEl.textContent || nameEl.innerText || '').trim();" +
            "           let msgText   = (bodyEl.textContent || bodyEl.innerText || '').trim();" +
            "           let convId = msgItemEl.getAttribute('anim-data-id') || msgItemEl.id || '';" +
            
            "           let realMsgId = msgItemEl.getAttribute('data-msg-id') || '';" +
            "           if (!realMsgId && msgItemEl.dataset) { realMsgId = msgItemEl.dataset.msgId || ''; }" +
            "           var fullTxt = '';" +
            
            "           try {" +
            "               var rK = null; var keys = Object.keys(msgItemEl);" +
            "               for (var i = 0; i < keys.length; i++) { if (keys[i].indexOf('__reactFiber') === 0 || keys[i].indexOf('__reactProps') === 0) { rK = keys[i]; break; } }" +
            "               if (rK && msgItemEl[rK]) {" +
            "                   var p = msgItemEl[rK].memoizedProps; if (!p && msgItemEl[rK].return) { p = msgItemEl[rK].return.memoizedProps; }" +
            "                   if (p) {" +
            "                       var paths = [p.data && p.data.lastMsg, p.item && p.item.lastMsg, p.lastMsg, p.message, p.msg, p.data, p.item, p];" +
            "                       for (var j=0; j<paths.length; j++) {" +
            "                           var o = paths[j];" +
            "                           if (o && typeof o === 'object') {" +
            "                               if (!realMsgId && (o.msgId || o.messageId)) { realMsgId = o.msgId || o.messageId; }" +
            "                               if (!fullTxt && typeof o.content === 'string' && o.content.trim() !== '') { fullTxt = o.content; }" +
            "                           }" +
            "                       }" +
            "                   }" +
            "               }" +
            "           } catch(err) {}" +
            
            "           if (fullTxt && fullTxt.length > msgText.length && !fullTxt.startsWith('{\"')) {" +
            "               msgText = fullTxt.trim();" +
            "           }" +
            
            "           let isVoiceNode = bodyEl.querySelector('[class*=\"audio\"], [class*=\"voice\"], [class*=\"Voice\"], svg');" +
            "           let isTimeOnly = /^[0-9]{1,2}:[0-9]{2}$/.test(msgText) || /^[0-9]{1,2}:[0-9]{2}$/.test(bodyEl.innerText.trim());" + 
            "           if (isVoiceNode || isTimeOnly) {" +
            "               msgText = '[Tin nhắn thoại]';" +
            "           }" +

            "           if(!groupName || !msgText) return;" +

            "           let timeEl = convItem.querySelector('.conv-item-title__time, [class*=\"time\"]');" +
            "           let timeString = timeEl ? (timeEl.textContent || '').trim() : '';" +

                        // KHÔNG DÙNG MATH.RANDOM ĐỂ CHỐNG SPAM RAM. DÙNG THỜI GIAN LÀM ID GIẢ ỔN ĐỊNH.
            "           if (!realMsgId || realMsgId === '') {" +
            "               realMsgId = 'TIME_' + timeString;" +
            "           }" +

            "           let fp = convId + '|' + realMsgId + '|' + timeString + '|' + msgText.substring(0, 40);" +
            "           if(window.zauto_seen[fp]) return;" +
            "           window.zauto_seen[fp] = true;" +
            "           window.zauto_seen_keys.push(fp);" +
            "           if(window.zauto_seen_keys.length > 800) { let old = window.zauto_seen_keys.splice(0, 100); old.forEach(k => delete window.zauto_seen[k]); }" +
            "           if (Date.now() - window.zauto_boot_time > 8000) {" +
            "               ZAutoBridge.onNewWebMsg(groupName, msgText, realMsgId, convId);" +
            "           }" +
            "       } catch(e) {}" +
            "   }" +

            // 3. HÀM THU THẬP DANH SÁCH NHÓM
            "   function collectGroups() {" +
            "       try {" +
            "           let groups = []; let nameEls = document.querySelectorAll('.conv-item-title__name');" +
            "           nameEls.forEach(el => { let n = (el.innerText || el.textContent || '').trim(); if(n && n.length > 1 && n.length < 80 && !groups.includes(n)) groups.push(n); });" +
            "           if(groups.length > 0) ZAutoBridge.onGroupListReceived(JSON.stringify(groups));" +
            "       } catch(e) {}" +
            "   }" +

            // 4. OBSERVE CONTAINER SIDEBAR
            "   function startSidebarObserver() {" +
            "       let container = document.getElementById('conversationListId');" +
            "       if(!container) { setTimeout(startSidebarObserver, 1500); return; }" +
            "       if(window.zauto_sidebar_observer) window.zauto_sidebar_observer.disconnect();" +
            "       window.zauto_sidebar_observer = new MutationObserver(mutations => {" +
            "           mutations.forEach(m => { try { let targetNode = m.target.nodeType === 3 ? m.target.parentNode : m.target; let msgItem = targetNode.closest('.msg-item'); if(msgItem) scanConvItem(msgItem); } catch(e) {} });" +
            "       });" +
            "       window.zauto_sidebar_observer.observe(container, { childList: true, subtree: true, characterData: true });" +
            "       document.querySelectorAll('.msg-item').forEach(scanConvItem);" +
            "       collectGroups();" +
            "       ZAutoBridge.onLoginSuccess('Đã kết nối', '');" + 
            "   }" +

            // 5. WATCHDOG TỰ ĐỘNG BẤM ĐỒNG BỘ VÀ BÁO KẾT NỐI
            "   function systemWatchdog() {" +
            "       ZAutoBridge.onHeartbeat(Date.now().toString());" +
            "       if(!navigator.onLine) { setTimeout(systemWatchdog, 10000); return; }" +
            "       try {" +
            "           let syncBtn = document.querySelector('.sync-msg-btn');" +
            "           if(!syncBtn) {" +
            "               let btns = document.querySelectorAll('button, div, span, a');" +
            "               for(let b of btns) { if(b.innerText && (b.innerText.includes('Đồng bộ') || b.innerText.includes('Khôi phục') || b.innerText.includes('Nhấn để'))) { syncBtn = b; break; } }" +
            "           }" +
            "           if(syncBtn) syncBtn.click();" +
            "       } catch(e) {}" +
            "       let isLoginScreen = document.querySelector('.qrcode') || document.querySelector('.login-container');" +
            "       if(isLoginScreen) {" +
            "           if(!window.login_start_time) window.login_start_time = Date.now();" +
            "           if(Date.now() - window.login_start_time > 300000) { window.login_start_time = Date.now(); location.reload(); }" +
            "       } else {" +
            "           window.login_start_time = null;" +
            "           if (!window.zauto_logged_in_flag) { window.zauto_logged_in_flag = true; ZAutoBridge.onLoginSuccess('Đã kết nối', ''); }" +
            "           let container = document.getElementById('conversationListId');" +
            "           if(!container || !window.zauto_sidebar_observer) { window.zauto_sidebar_observer = null; startSidebarObserver(); }" +
            "           window.zauto_group_tick = (window.zauto_group_tick || 0) + 1;" +
            "           if(window.zauto_group_tick % 5 === 0) collectGroups();" +
            "       }" +
            "       let nextTick = document.hidden ? 15000 : 3000;" +
            "       setTimeout(systemWatchdog, nextTick);" +
            "   }" +
            "   setInterval(() => { let container = document.getElementById('conversationListId'); if(container) document.querySelectorAll('.msg-item').forEach(scanConvItem); }, 2000);" +
            "   setTimeout(startSidebarObserver, 1000);" +
            "   setTimeout(systemWatchdog, 3000);" +
            "})();";

        safeEvaluateJs(js);
    }

    // =========================================================
    // JAVA WATCHDOG (kiểm tra heartbeat từ JS)
    // =========================================================
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
                        safeEvaluateJs("if(!window.zauto_started) location.reload();");
                    }
                }
                watchdogHandler.postDelayed(this, 15000);
            }
        };
        watchdogHandler.postDelayed(watchdogRunnable, 15000);
    }

    // =========================================================
    // CÁC HÀM TIỆN ÍCH - CẬP NHẬT TỌA ĐỘ (ĐÃ FIX CHỐNG NGỦ ĐÔNG MÁY CŨ)
    // =========================================================
    public static void updateWebViewBounds(
            final Activity activity,
            final int x, final int y,
            final int width, final int height,
            final boolean visible) {

        Activity safeActivity = activityRef != null ? activityRef.get() : activity;
        if (safeActivity == null) return;

        safeActivity.runOnUiThread(() -> {
            try {
                if (webLayout == null) return;
                FrameLayout.LayoutParams params =
                        (FrameLayout.LayoutParams) webLayout.getLayoutParams();
                if (!visible) {
                    // ÉP CHẠY NGẦM BẰNG CÁCH DÙNG ĐỘ TRONG SUỐT CỰC THẤP
                    webLayout.setAlpha(0.01f); 
                    params.leftMargin = -2000; 
                    params.topMargin = -2000;
                    params.width = 1080;
                    params.height = 2400;
                } else {
                    webLayout.setAlpha(1.0f);
                    params.leftMargin = x;
                    params.topMargin = y;
                    params.width = width;
                    params.height = height;
                    if (hiddenWebView != null) {
                        hiddenWebView.invalidate();
                        hiddenWebView.requestLayout();
                    }
                }
                webLayout.setLayoutParams(params);
            } catch (Exception e) {
                Log.e(TAG, "updateWebViewBounds Error", e);
            }
        });
    }
    // HÀM ĐỌC GIỌNG NÓI TỪ PYTHON GỌI XUỐNG
    public static void speak(String text) {
        if (tts != null) {
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, null);
        }
    }
    public static void reloadWeb(final Activity activity) {
        safeReload();
    }

    public static void onResume(final Activity activity) {
        Activity safeActivity = activityRef != null ? activityRef.get() : activity;
        if (safeActivity == null) return;
        safeActivity.runOnUiThread(() -> {
            try {
                if (hiddenWebView != null) hiddenWebView.onResume();
            } catch (Exception ignored) {}
        });
    }

    public static void onPause() {
        try {
            // ĐÃ XÓA LỆNH: hiddenWebView.onPause(); -> Để Javascript vẫn chạy khi app ẩn
        } catch (Exception ignored) {}
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

    // =========================================================
    // HỆ THỐNG SĂN TÌM VÀ PHÁT BẢN GHI ÂM (BẢN FIX LỖI CLICK)
    // =========================================================
    public static void playLastAudio(final Activity activity, final String conversationId) {
        Activity safeActivity = activityRef != null ? activityRef.get() : activity;
        if (safeActivity == null || hiddenWebView == null) return;

        safeActivity.runOnUiThread(() -> {
            String js = "(function() {" +
                "   console.log('ZAuto: Bat dau tim nut Play cho ' + '" + conversationId + "');" +
                // BƯỚC 1: MỞ NHÓM (Dùng kỹ thuật React Fiber để kích hoạt Click chuẩn)
                "   let item = document.querySelector('.msg-item[anim-data-id=\"" + conversationId + "\"] .conv-item');" +
                "   if(item) {" +
                "       let key = Object.keys(item).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
                "       if (key && item[key]) {" +
                "           if (item[key].onClick) item[key].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                "           else if (item[key].return && item[key].return.memoizedProps.onClick) item[key].return.memoizedProps.onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                "       } else { item.click(); }" +
                "   }" +

                // BƯỚC 2: QUÉT ĐA ĐIỂM SAU KHI ĐỢI LOAD
                // Tăng delay lên 1500ms vì tin nhắn thoại trên Zalo load rất chậm
                "   setTimeout(() => {" +
                "       let findAndPlay = () => {" +
                "           let playBtn = null;" +
                            // Bổ sung mọi Selector mà Zalo có thể giấu nút Play
                "           let selectors = [" +
                "               '.fa-PlayCircle_24_Filled', '[class*=\"PlayCircle\"]', '[class*=\"play-circle\"]', " +
                "               '.v-audio', '.icon-play-audio', '[class*=\"voice-message\"] i', " +
                "               '.chat-message-audio i', 'i[class*=\"play\"]', 'div[class*=\"play-btn\"]', 'svg[class*=\"play\"]'" +
                "           ];" +
                
                "           for (let sel of selectors) {" +
                "               let els = document.querySelectorAll(sel);" +
                "               if(els.length > 0) { playBtn = els[els.length - 1]; break; }" +
                "           }" +

                "           if (!playBtn) {" +
                "               let allMsgs = document.querySelectorAll('.chat-item');" +
                "               if (allMsgs.length > 0) {" +
                "                   let lastMsg = allMsgs[allMsgs.length - 1];" +
                "                   playBtn = lastMsg.querySelector('i[class*=\"play\"], div[role=\"button\"], [class*=\"play\"], svg');" +
                "               }" +
                "           }" +

                "           if(playBtn) {" +
                "               console.log('ZAuto: Da tim thay nut Play!');" +
                "               playBtn.click();" +
                "               let k = Object.keys(playBtn).find(key => key.startsWith('__reactEventHandlers') || key.startsWith('__reactFiber'));" +
                "               if(k && playBtn[k] && playBtn[k].onClick) playBtn[k].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                "               return true;" +
                "           }" +
                "           return false;" +
                "       };" +

                "       if (!findAndPlay()) {" +
                "           let retryCount = 0;" +
                "           let interval = setInterval(() => {" +
                "               retryCount++;" +
                "               if (findAndPlay() || retryCount > 8) clearInterval(interval);" +
                "           }, 500);" + // Thử lại liên tục 8 lần (4 giây)
                "       }" +
                "   }, 1500);" + 
                "})();";
            hiddenWebView.evaluateJavascript(js, null);
        });
    }
}
