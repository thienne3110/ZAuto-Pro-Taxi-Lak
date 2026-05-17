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
    // GỬI TIN NHẮN REPLY VÀO NHÓM CỤ THỂ (NÂNG CẤP CLICK ĐÚP + ENTER)
    // =========================================================
    public static void sendReplyToSpecificMessage(
            final Activity activity,
            final String conversationId,
            final String msgId,
            final String text,
            final String msgTextToFind,
            final String sentTime) {

        Activity safeActivity = activityRef != null ? activityRef.get() : activity;
        if (safeActivity == null || hiddenWebView == null) return;

        replyQueue.add(() -> safeActivity.runOnUiThread(() -> {
            try {
                String safeReply = text.replace("'", "\\'").replace("\n", "\\n").replace("\"", "\\\"");
                String safeSearchText = (msgTextToFind != null) ? msgTextToFind.replace("'", "\\'").replace("\n", " ").replace("\"", "\\\"") : "";
                String safeMsgId = (msgId != null) ? msgId.replace("'", "\\'") : "";
                String safeTime = (sentTime != null) ? sentTime.replace("'", "\\'") : "";

                String jsCode = "(function() {" +
                    "try {" +
                        "var safeReply = '" + safeReply + "';" +
                        "var safeSearchText = '" + safeSearchText + "';" +
                        "var targetMsgId = '" + safeMsgId + "';" +
                        "var targetTime = '" + safeTime + "';" +

                        "var groupItem = document.querySelector('.msg-item[anim-data-id=\"' + '" + conversationId + "' + '\"] .conv-item') || document.querySelector('.msg-item[anim-data-id=\"' + '" + conversationId + "' + '\"]');" +
                        "if(groupItem) {" +
                        "    groupItem.scrollIntoView({block: 'center'});" + 
                        "    groupItem.click();" + 
                        "    var key = Object.keys(groupItem).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
                        "    if (key && groupItem[key]) {" +
                        "        if (groupItem[key].onClick) groupItem[key].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                        "        else if (groupItem[key].return && groupItem[key].return.memoizedProps.onClick) groupItem[key].return.memoizedProps.onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                        "    }" +
                        "}" +

                        "setTimeout(function() {" +
                            "var textLower = safeSearchText.toLowerCase();" +
                            "var bubbles = document.querySelectorAll('.message-view__blur, .card--group-message, .chat-message, div[id^=\"msg-\"], .audio-msg, .voice-msg, .text-msg');" +
                            "var targetNode = null;" +
                            "var isVoice = textLower.includes('ghi âm') || textLower.includes('thoại') || textLower.includes('audio') || textLower.includes('voice');" +
                            
                            "if (isVoice) {" +
                                "for (var v = bubbles.length - 1; v >= 0; v--) {" +
                                    "var cellText = bubbles[v].innerText ? bubbles[v].innerText : '';" +
                                    "var cellHtml = bubbles[v].innerHTML ? bubbles[v].innerHTML.toLowerCase() : '';" +
                                    "var hasVoiceStructure = cellHtml.includes('audio') || cellHtml.includes('player') || cellHtml.includes('ico-voice') || /\\\\d{2}:\\\\d{2}/.test(cellText);" +
                                    "if (hasVoiceStructure && cellText.includes(targetTime)) { targetNode = bubbles[v]; break; }" +
                                "}" +
                                "if (!targetNode && bubbles.length > 0) { targetNode = bubbles[bubbles.length - 1]; }" +
                            "} else if (safeSearchText.length > 2) {" +
                                "for (var i = bubbles.length - 1; i >= 0; i--) {" +
                                    "if (bubbles[i].innerText && bubbles[i].innerText.includes(safeSearchText) && bubbles[i].innerText.includes(targetTime)) {" +
                                        "targetNode = bubbles[i]; break;" +
                                    "}" +
                                "}" +
                            "}" +
                            
                            "if (!targetNode && targetMsgId && targetMsgId !== 'NOTIFICATION') {" +
                                "for (var j = bubbles.length - 1; j >= 0; j--) {" +
                                    "if (bubbles[j].id && bubbles[j].id.includes(targetMsgId)) {" +
                                        "targetNode = bubbles[j]; break;" +
                                    "}" +
                                "}" +
                            "}" +

                            "function typeAndSend() {" +
                                "var input = document.querySelector('#richInput') || document.querySelector('.chat-input');" +
                                "if(input) {" +
                                    "input.focus();" + 
                                    "input.innerHTML = safeReply;" +
                                    "input.dispatchEvent(new Event('input', {bubbles: true}));" +
                                    
                                    "setTimeout(function() {" +
                                        "var btn = document.querySelector('.fa-send-2') || document.querySelector('[icon=\"send-2\"]') || document.querySelector('.send-msg-btn');" +
                                        "if(btn) {" +
                                            "var tgt = btn.closest('.z--btn--v2') || btn.parentNode || btn;" +
                                            "tgt.click();" +
                                            "var bk = Object.keys(tgt).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
                                            "if(bk && tgt[bk] && tgt[bk].onClick) tgt[bk].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                                        "}" +
                                        
                                        "var enterEvent = new KeyboardEvent('keydown', { bubbles: true, cancelable: true, keyCode: 13, which: 13, key: 'Enter', code: 'Enter' });" +
                                        "input.dispatchEvent(enterEvent);" +
                                    "}, 300);" + 
                                "}" +
                            "}" +

                            "if (targetNode) {" +
                                "var evt = new MouseEvent('dblclick', {bubbles: true, cancelable: true, view: window});" +
                                "targetNode.dispatchEvent(evt);" +
                                
                                "var rKey = Object.keys(targetNode).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
                                "if(rKey && targetNode[rKey]) {" +
                                    "if(targetNode[rKey].onDoubleClick) targetNode[rKey].onDoubleClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                                    "else if(targetNode[rKey].return && targetNode[rKey].return.memoizedProps.onDoubleClick) targetNode[rKey].return.memoizedProps.onDoubleClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                                "}" +
                                
                                "setTimeout(typeAndSend, 500);" +
                            "} else {" +
                                "typeAndSend();" +
                            "}" +
                        "}, 1000);" + 
                    "} catch(e) { console.log(e); }" +
                "})();";

                hiddenWebView.evaluateJavascript(jsCode, null);
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
    // KHỞI TẠO WEBVIEW
    // =========================================================
    public static void initWebView(final Activity activity) {
        if (activity == null) return;
        activityRef = new WeakReference<>(activity);

        activity.runOnUiThread(() -> {
            try {
                if (hiddenWebView != null) return;

                webLayout = new FrameLayout(activity);
                hiddenWebView = new WebView(activity);

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
                settings.setCacheMode(WebSettings.LOAD_DEFAULT);
                settings.setNeedInitialFocus(false);
                if (android.os.Build.VERSION.SDK_INT >= 29) {
                    settings.setForceDark(WebSettings.FORCE_DARK_OFF);
                }
                settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
                settings.setUseWideViewPort(true);
                settings.setLoadWithOverviewMode(true);
                settings.setUserAgentString(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                    "AppleWebKit/537.36 (KHTML, like Gecko) " +
                    "Chrome/136.0.0.0 Safari/537.36"
                );

                CookieManager cookieManager = CookieManager.getInstance();
                cookieManager.setAcceptCookie(true);
                cookieManager.setAcceptThirdPartyCookies(hiddenWebView, true);

                hiddenWebView.addJavascriptInterface(new WebAppInterface(activity), "ZAutoBridge");
                hiddenWebView.setWebChromeClient(new WebChromeClient());

                hiddenWebView.setWebViewClient(new WebViewClient() {
                    // --- ĐOẠN QUAN TRỌNG: TỰ ĐỘNG REFRESH KHI MẤT MẠNG ---
                    @Override
                    public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                        if (request.isForMainFrame()) {
                            Log.e(TAG, "Lỗi kết nối Zalo: " + error.getDescription());
                            // Nếu tắt màn hình bị mất mạng, khi có mạng lại nó sẽ tự tải lại trang sau 5 giây
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

                // ĐÁNH LỪA ANDROID CŨ (Tránh View Clipping / Ngủ đông GPU)
                FrameLayout.LayoutParams rootParams = new FrameLayout.LayoutParams(1080, 2400);
                rootParams.leftMargin = -2000; 
                rootParams.topMargin = -2000;
                webLayout.setAlpha(0.01f); // QUAN TRỌNG: 0.01f giúp Web chạy ngầm 100% công suất

                if (webLayout.getParent() != null) {
                    ((ViewGroup) webLayout.getParent()).removeView(webLayout);
                }
                activity.addContentView(webLayout, rootParams);

                hiddenWebView.setVisibility(View.VISIBLE);
                hiddenWebView.bringToFront();
                hiddenWebView.requestFocus();

                // KHỞI TẠO GIỌNG NÓI TIẾNG VIỆT
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
    // JS OBSERVER & API INTERNAL (CHẠY NGẦM 100%)
    // =========================================================
    public static void injectSidebarObserver(WebView view) {
        String js =
            "(function() {" +
            "   if(window.zauto_started) return;" +
            "   window.zauto_started = true;" +
            "   window.zauto_boot_time = Date.now();" +
            "   window.zauto_seen = {};" +
            "   window.zauto_seen_keys = [];" +

            // HÀM GỬI REPLY ĐA TẦNG (DÙNG SELECTOR CHUẨN + ENTER + BÁO CÁO TOAST)
            "   window.zautoSendReply = function(convId, fakeMsgId, text, groupName) {" +
            "       try {" +
                        // 1. CHUYỂN SANG NHÓM CẦN CHỐT
            "           let item = document.querySelector('.msg-item[anim-data-id=\"'+convId+'\"] .conv-item');" +
            "           if(item) {" +
            "               let key = Object.keys(item).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
            "               if (key && item[key]) {" +
            "                   if (item[key].onClick) item[key].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
            "                   else if (item[key].return && item[key].return.memoizedProps.onClick) item[key].return.memoizedProps.onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
            "               } else { item.click(); }" +
            "           }" +
            
            "           setTimeout(() => {" +
            "               let realMsgId = '';" +
            "               try {" +
            "                   let msgs = document.querySelectorAll('[id^=\"msg_\"]');" +
            "                   if (msgs && msgs.length > 0) {" +
            "                       let lastMsg = msgs[msgs.length - 1];" +
            "                       realMsgId = lastMsg.getAttribute('id').substring(4);" +
            "                   }" +
            "               } catch(err) { realMsgId = ''; }" +
            
                        // 2. THỬ GỬI BẰNG API NGẦM TRƯỚC
            "               if (window.zMessenger && typeof window.zMessenger.sendMessage === 'function') {" +
            "                   let req = { toid: convId, msg: text, type: 1 };" +
            "                   if (realMsgId && realMsgId !== '') req.quote_msgId = realMsgId;" +
            "                   window.zMessenger.sendMessage(req);" +
            "                   ZAutoBridge.onLoginSuccess('Đã chốt xong:', groupName);" + 
            "               } else {" +
                        // 3. NẾU BỊ CHẶN API -> DÙNG PHƯƠNG ÁN UI (ĐẬP PHÍM)
            "                   let input = document.getElementById('richInput');" +
            "                   if(input) {" +
            "                       input.focus();" +
            "                       input.innerHTML = '';" +
            "                       document.execCommand('insertText', false, text);" +
            "                       input.dispatchEvent(new Event('input', {bubbles:true}));" + 
            "                       input.blur();" + // CHẶN BÀN PHÍM: Hủy focus ngay lập tức để Android không kịp nhô bàn phím lên
            "                       let attempts = 0;" +
            
            "                       let trySend = setInterval(() => {" +
            "                           attempts++;" +
            "                           let btnSend = null;" +
                                        // QUÉT CÁC SELECTOR CHUẨN XÁC TỪ DỮ LIỆU CỦA BẠN
            "                           let primarySelector = '#chat-input-container-id > div.chat-input-container__right-layout > div.normal-buttons-group > div.send-msg-btn';" +
            "                           let fallbackSelectors = ['.fa-Sent-msg_24_Line', '[data-translate-title=\"STR_SEND\"]'];" +
            
            "                           let el = document.querySelector(primarySelector);" +
            "                           if (el) {" +
            "                               btnSend = el;" +
            "                           } else {" +
            "                               for (let sel of fallbackSelectors) {" +
            "                                   let fallbackEl = document.querySelector(sel);" +
            "                                   if (fallbackEl) {" +
            "                                       btnSend = fallbackEl.closest('.z--btn--v2') || fallbackEl.parentElement || fallbackEl;" +
            "                                       break;" +
            "                                   }" +
            "                               }" +
            "                           }" +
            
                                        // THỰC HIỆN CLICK VÀO NÚT
            "                           if (btnSend) {" +
            "                               btnSend.click();" +
            "                               let key = Object.keys(btnSend).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
            "                               if(key && btnSend[key] && btnSend[key].onClick) btnSend[key].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
            "                           }" +
            
                                        // BỒI THÊM PHÍM ENTER ẢO VÀO KHUNG CHAT
            "                           let enterEvent = new KeyboardEvent('keydown', { bubbles: true, cancelable: true, keyCode: 13, which: 13, key: 'Enter', code: 'Enter' });" +
            "                           input.dispatchEvent(enterEvent);" +
            
                                        // KIỂM TRA THÀNH CÔNG VÀ DỪNG VÒNG LẶP
            "                           if (input.innerHTML === '' || input.innerHTML === '<br>') {" +
            "                               clearInterval(trySend);" +
            "                               ZAutoBridge.onLoginSuccess('Đã chốt xong:', groupName);" + // Báo cáo Toast về Kivy
            "                           } else if (attempts > 12) {" +
                                            // Dừng lại sau 3 giây (12 lần) để chống treo máy
            "                               clearInterval(trySend);" +
            "                           }" +
            "                       }, 250);" + 
            "                   }" +
            "               }" +
            "           }, 800);" + // Đợi 0.8 giây để Zalo load màn hình chat
            "       } catch(e) {}" +
            "   };" +
            // HÀM QUÉT SIDEBAR (ĐÃ FIX ZALO ĐỔI GIAO DIỆN & TÌM ĐÚNG ID TIN)
            "   function scanConvItem(msgItemEl) {" +
            "       try {" +
            "           let convItem = msgItemEl.querySelector('.conv-item') || msgItemEl;" + // Đã gỡ bỏ .gridv2
            "           if(!convItem) return;" +
            // ĐOẠN MỚI:
			"           let nameEl = convItem.querySelector('.conv-item-title__name, [class*=\"name\"]');" +
			"           let bodyEl = convItem.querySelector('.conv-item-body, [class*=\"snippet\"], [class*=\"message-text\"]');" +
			"           if(!nameEl) return;" + // Chỉ bắt buộc tìm thấy Tên nhóm
			"           let groupName = (nameEl.textContent || nameEl.innerText || '').trim();" +
			"           let msgText = bodyEl ? (bodyEl.textContent || bodyEl.innerText || '').trim() : '';" +
            "           let convId = msgItemEl.getAttribute('anim-data-id') || msgItemEl.id || '';" +
            
            // DEEP BYPASS: QUÉT VÉT CẠN MỌI TẦNG REACT FIBER ĐỂ LỘT TRẦN ID BỊ GIẤU
            "           let realMsgId = ''; var fullTxt = '';" +
            "           try {" +
            "               let id1 = msgItemEl.getAttribute('data-msg-id') || (msgItemEl.dataset ? msgItemEl.dataset.msgId : '');" +
            "               if (id1 && id1.length > 5) realMsgId = id1;" +
            
            "               let keys = Object.keys(msgItemEl);" +
            "               let rK = keys.find(k => k.startsWith('__reactFiber') || k.startsWith('__reactProps'));" +
            "               if (rK && msgItemEl[rK]) {" +
            "                   let node = msgItemEl[rK];" +
            "                   for(let step = 0; step < 4; step++) {" +
            "                       if(!node) break;" +
            "                       let p = node.memoizedProps || node.pendingProps;" +
            "                       if (p) {" +
            "                           let objs = [p.data?.lastMsg, p.item?.lastMsg, p.lastMsg, p.message, p.msg, p.data, p.item, p];" +
            "                           for (let o of objs) {" +
            "                               if (o && typeof o === 'object') {" +
            "                                   let foundId = o.msgId || o.messageId || o.cliMsgId || o.globalMsgId;" +
            "                                   if (!realMsgId && foundId && String(foundId).length > 5) { realMsgId = String(foundId); }" +
            "                                   if (!fullTxt && typeof o.content === 'string' && o.content.trim() !== '') { fullTxt = o.content; }" +
            "                               }" +
            "                           }" +
            "                       }" +
            "                       node = node.return;" +
            "                   }" +
            "               }" +
            "           } catch(err) {}" +
            
            "           if (fullTxt && fullTxt.length > msgText.length && !fullTxt.startsWith('{\"')) {" +
            "               msgText = fullTxt.trim();" +
            "           }" +
            
            "           let isVoiceNode = bodyEl.querySelector('[class*=\"audio\"], [class*=\"voice\"], [class*=\"Voice\"], svg');" +
            "           let isTimeOnly = /^[0-9]{1,2}:[0-9]{2}$/.test(msgText) || /^[0-9]{1,2}:[0-9]{2}$/.test(bodyEl.innerText.trim());" + 
            "           if (isVoiceNode || isTimeOnly) {" +
            "               let rawBody = bodyEl.textContent || bodyEl.innerText || '';" +
            "               if (rawBody.indexOf(': ') > -1) {" +
            "                   msgText = rawBody.split(': ')[0] + ': [Tin nhắn thoại]';" +
            "               } else {" +
            "                   msgText = '[Tin nhắn thoại]';" +
            "               }" +
            "               " +
            "               let seconds = -1;" + // Mặc định gán -1 (Báo hiệu quét lỗi/Không tìm thấy)
            "               try {" +
            "                   let timeNode = msgItemEl.querySelector('[class*=\"audio-time\"], [class*=\"duration\"], span[class*=\"time\"]');" +
            "                   if (timeNode) {" +
            "                       let durationText = timeNode.innerText.trim();" + // Lấy chuỗi dạng "0:04"
            "                       if (durationText.includes(':')) {" +
            "                           let parts = durationText.split(':');" +
            "                           seconds = parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);" +
            "                       }" +
            "                   }" +
            "               } catch(err) { seconds = -1; }" +
            "               " +
            "               msgText = msgText + '%%%' + seconds;" + // Ghép số giây vào cuối nội dung để gửi về Python
            "           }" +

            "           if(!groupName || !msgText) return;" +

            "           let timeEl = convItem.querySelector('.conv-item-title__time, [class*=\"time\"]');" +
            "           let timeString = timeEl ? (timeEl.textContent || '').trim() : '';" +

            "           if (!realMsgId || realMsgId === '') {" +
            "               realMsgId = 'TIME_' + timeString;" +
            "           }" +

            "           let fp = convId + '|' + realMsgId + '|' + timeString + '|' + msgText.substring(0, 40);" +
            "           if(window.zauto_seen[fp]) return;" +
            "           window.zauto_seen[fp] = true;" +
            "           window.zauto_seen_keys.push(fp);" +
            "           if(window.zauto_seen_keys.length > 800) { let old = window.zauto_seen_keys.splice(0, 100); old.forEach(k => delete window.zauto_seen[k]); }" +
            "           if (Date.now() - window.zauto_boot_time > 8000) {" +
            // ĐÃ FIX: TRUYỀN ĐẦY ĐỦ THÔNG SỐ VỀ CHO PYTHON ĐỂ XỬ LÝ (Có ID để chống trùng)
            "               ZAutoBridge.onNewWebMsg(groupName, msgText, realMsgId, convId);" +
            "           }" +
            "       } catch(e) {}" +
            "   }" +

            // HÀM THU THẬP DANH SÁCH NHÓM
            "   function collectGroups() {" +
            "       try {" +
            "           let groups = [];" +
            "           let nameEls = document.querySelectorAll('.conv-item-title__name');" +
            "           nameEls.forEach(el => {" +
            "               let n = (el.innerText || el.textContent || '').trim();" +
            "               if(n && n.length > 1 && n.length < 80 && !groups.includes(n)) groups.push(n);" +
            "           });" +
            "           if(groups.length > 0) ZAutoBridge.onGroupListReceived(JSON.stringify(groups));" +
            "       } catch(e) {}" +
            "   }" +

            // OBSERVE CONTAINER SIDEBAR
            "   function startSidebarObserver() {" +
            "       let container = document.getElementById('conversationListId');" +
            "       if(!container) {" +
            "           setTimeout(startSidebarObserver, 1500);" +
            "           return;" +
            "       }" +
            "       if(window.zauto_sidebar_observer) window.zauto_sidebar_observer.disconnect();" +
            "       window.zauto_sidebar_observer = new MutationObserver(mutations => {" +
            "           mutations.forEach(m => {" +
            "               try {" +
            "                   let targetNode = m.target.nodeType === 3 ? m.target.parentNode : m.target;" +
            "                   let msgItem = targetNode.closest('.msg-item');" +
            "                   if(msgItem) scanConvItem(msgItem);" +
            "               } catch(e) {}" +
            "           });" +
            "       });" +
            "       window.zauto_sidebar_observer.observe(container, { childList: true, subtree: true, characterData: true });" +
            "       document.querySelectorAll('.msg-item').forEach(scanConvItem);" +
            "       collectGroups();" +
            "       ZAutoBridge.onLoginSuccess('Đã kết nối', '');" +
            "   }" +

            // WATCHDOG + NÚT ĐỒNG BỘ
            "   function systemWatchdog() {" +
            "       ZAutoBridge.onHeartbeat(Date.now().toString());" +
            "       if(!navigator.onLine) { setTimeout(systemWatchdog, 10000); return; }" +
            "       try {" +
            "           let syncBtn = document.querySelector('.sync-msg-btn');" +
            "           if(!syncBtn) {" +
            "               let btns = document.querySelectorAll('button, div, span');" +
            "               for(let b of btns) { if(b.innerText && (b.innerText.includes('Đồng bộ') || b.innerText.includes('Khôi phục'))) { syncBtn = b; break; } }" +
            "           }" +
            "           if(syncBtn) syncBtn.click();" +
            "       } catch(e) {}" +
            "       let isLoginScreen = document.querySelector('.qrcode') || document.querySelector('.login-container');" +
            "       if(isLoginScreen) {" +
            "           if(!window.login_start_time) window.login_start_time = Date.now();" +
            "           if(Date.now() - window.login_start_time > 180000) { window.login_start_time = Date.now(); location.reload(); }" +
            "       } else {" +
            "           window.login_start_time = null;" +
            "           let container = document.getElementById('conversationListId');" +
            "           if(!container || !window.zauto_sidebar_observer) {" +
            "               window.zauto_sidebar_observer = null;" +
            "               startSidebarObserver();" +
            "           }" +
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
    // CÁC HÀM TIỆN ÍCH - GIỮ NGUYÊN KÍCH THƯỚC KHỔNG LỒ
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
                    webLayout.setAlpha(0.01f); // QUAN TRỌNG: 0.01f
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
    // HỆ THỐNG PHÁT BẢN GHI ÂM CHUẨN XÁC THEO ID
    // =========================================================
    public static void playSpecificAudio(final Activity activity, final String conversationId, final String msgId) {
        Activity safeActivity = activityRef != null ? activityRef.get() : activity;
        if (safeActivity == null || hiddenWebView == null) return;

        safeActivity.runOnUiThread(() -> {
            String js = "(function() {" +
                "   console.log('ZAuto: Bat dau tim nut Play cho ' + '" + msgId + "');" +
                "   let item = document.querySelector('.msg-item[anim-data-id=\"" + conversationId + "\"] .conv-item');" +
                "   if(item) {" +
                "       let key = Object.keys(item).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
                "       if (key && item[key]) {" +
                "           if (item[key].onClick) item[key].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                "           else if (item[key].return && item[key].return.memoizedProps.onClick) item[key].return.memoizedProps.onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                "       } else { item.click(); }" +
                "   }" +

                "   setTimeout(() => {" +
                "       let findAndPlay = () => {" +
                "           let msgNode = document.querySelector('[data-msg-id=\"" + msgId + "\"]');" +
                "           if (!msgNode) msgNode = document.querySelector('div[id*=\"" + msgId + "\"]');" +
                "           if (!msgNode) {" +
                "               let allMsgs = document.querySelectorAll('.chat-item');" +
                "               if(allMsgs.length > 0) msgNode = allMsgs[allMsgs.length - 1];" +
                "           }" +
                "           if (!msgNode) return false;" +
                
                "           let playBtn = msgNode.querySelector('.fa-PlayCircle_24_Filled, [class*=\"PlayCircle\"], .v-audio, .icon-play-audio, i[class*=\"play\"], div[class*=\"play-btn\"], svg[class*=\"play\"]');" +
                
                "           if(playBtn) {" +
                "               console.log('ZAuto: Da tim thay nut Play dung ID!');" +
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
                "           }, 500);" +
                "       }" +
                "   }, 1500);" + 
                "})();";
            hiddenWebView.evaluateJavascript(js, null);
        });
    }
}
