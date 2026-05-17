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
            final String msgTextToFind,
            final String sentTime) { // ĐÃ THÊM: Nhận tham số nội dung gốc và giờ gửi từ Python

        Activity safeActivity = activityRef != null ? activityRef.get() : activity;
        if (safeActivity == null || hiddenWebView == null) return;

        replyQueue.add(() -> safeActivity.runOnUiThread(() -> {
            try {
                // Khử trùng ký tự đặc biệt an toàn cho Javascript
                String safeReply = text.replace("'", "\\'").replace("\n", "\\n").replace("\"", "\\\"");
                String safeSearchText = msgTextToFind.replace("'", "\\'").replace("\n", " ").replace("\"", "\\\"");
                String safeMsgId = (msgId != null) ? msgId.replace("'", "\\'") : "";
                String safeTime = (sentTime != null) ? sentTime.replace("'", "\\'") : "";

                String jsCode = "(function() {" +
                    "try {" +
                        "var safeReply = '" + safeReply + "';" +
                        "var safeSearchText = '" + safeSearchText + "';" +
                        "var targetMsgId = '" + safeMsgId + "';" +
                        "var targetTime = '" + safeTime + "';" +

                        // 1. ÉP MỞ ĐÚNG NHÓM BẰNG MỌI GIÁ (SCROLL TỚI NHÓM RỒI CLICK REACT)
                        "var groupItem = document.querySelector('.msg-item[anim-data-id=\"' + '" + conversationId + "' + '\"] .conv-item') || document.querySelector('.msg-item[anim-data-id=\"' + '" + conversationId + "' + '\"]');" +
                        "if(groupItem) {" +
                        "    groupItem.scrollIntoView({block: 'center'});" + // Kéo màn hình tới đúng nhóm
                        "    groupItem.click();" + 
                        "    var key = Object.keys(groupItem).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
                        "    if (key && groupItem[key]) {" +
                        "        if (groupItem[key].onClick) groupItem[key].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                        "        else if (groupItem[key].return && groupItem[key].return.memoizedProps.onClick) groupItem[key].return.memoizedProps.onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                        "    }" +
                        "}" +

                        // 2. CHỜ 1 GIÂY (1000ms) ĐỂ MẠNG TẢI KHUNG CHAT LÊN RỒI MỚI QUÉT TIN
                        "setTimeout(function() {" +
                            "var textLower = safeSearchText.toLowerCase();" +
                            "var bubbles = document.querySelectorAll('.message-view__blur, .card--group-message, .chat-message, div[id^=\"msg-\"], .audio-msg, .voice-msg');" +
                            "var targetNode = null;" +
                            "var isVoice = textLower.includes('ghi âm') || textLower.includes('thoại') || textLower.includes('audio') || textLower.includes('voice');" +
                            
                            // TÌM THEO THỜI GIAN
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
                            
                            // TÌM THEO ID (NẾU MẠNG LỖI)
                            "if (!targetNode && targetMsgId && targetMsgId !== 'NOTIFICATION') {" +
                                "for (var j = bubbles.length - 1; j >= 0; j--) {" +
                                    "if (bubbles[j].id && bubbles[j].id.includes(targetMsgId)) {" +
                                        "targetNode = bubbles[j]; break;" +
                                    "}" +
                                "}" +
                            "}" +

                            // 3. HÀM ÉP NHẬP VÀ ÉP NÚT GỬI & ENTER SONG KIẾM HỢP BÍCH
                            "function typeAndSend() {" +
                                "var input = document.querySelector('#richInput') || document.querySelector('.chat-input');" +
                                "if(input) {" +
                                    "input.focus();" + // Bắt buộc Focus để Zalo nhận diện đang gõ phím
                                    "input.innerHTML = safeReply;" +
                                    "input.dispatchEvent(new Event('input', {bubbles: true}));" +
                                    
                                    "setTimeout(function() {" +
                                        // Phương án 1: Bấm nút Gửi của Zalo bằng React
                                        "var btn = document.querySelector('.fa-send-2') || document.querySelector('[icon=\"send-2\"]') || document.querySelector('.send-msg-btn');" +
                                        "if(btn) {" +
                                            "var tgt = btn.closest('.z--btn--v2') || btn.parentNode || btn;" +
                                            "tgt.click();" +
                                            "var bk = Object.keys(tgt).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
                                            "if(bk && tgt[bk] && tgt[bk].onClick) tgt[bk].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                                        "}" +
                                        
                                        // Phương án 2: Thả phím Enter ảo thẳng vào bàn phím
                                        "var enterEvent = new KeyboardEvent('keydown', { bubbles: true, cancelable: true, keyCode: 13, which: 13, key: 'Enter', code: 'Enter' });" +
                                        "input.dispatchEvent(enterEvent);" +
                                    "}, 300);" + // Đợi 300ms sau khi nhét chữ mới bấm gửi
                                "}" +
                            "}" +

                            // 4. KÍCH HOẠT CLICK ĐÚP XUYÊN LÕI REACT
                            "if (targetNode) {" +
                                "var evt = new MouseEvent('dblclick', {bubbles: true, cancelable: true, view: window});" +
                                "targetNode.dispatchEvent(evt);" +
                                
                                "var rKey = Object.keys(targetNode).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
                                "if(rKey && targetNode[rKey]) {" +
                                    "if(targetNode[rKey].onDoubleClick) targetNode[rKey].onDoubleClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                                    "else if(targetNode[rKey].return && targetNode[rKey].return.memoizedProps.onDoubleClick) targetNode[rKey].return.memoizedProps.onDoubleClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                                "}" +
                                
                                // Đợi 500ms cho cái bảng Quote bật lên hoàn toàn rồi mới gọi typeAndSend
                                "setTimeout(typeAndSend, 500);" +
                            "} else {" +
                                "typeAndSend();" +
                            "}" +
                        "}, 1000);" + // Đợi mạng load khung chat mất 1s
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
    // JAVA BRIDGE → GIAO TIẾP GIỮA JAVASCRIPT VÀ ANDROID
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

        // ---> THÊM: KÍCH HOẠT BONG BÓNG LÚC KHỞI ĐỘNG
        @JavascriptInterface
        public void showFloatingBubbleAction() {
            Activity act = activityRef != null ? activityRef.get() : null;
            if (act != null) showFloatingBubble(act);
        }

        // ---> THÊM: BẮN LÊN BONG BÓNG KHI CÓ CUỐC MỚI
        @JavascriptInterface
        public void showNewRideOnBubble(String groupName, String msgText, String convId, String msgId) {
            ZaloWebManager.showNewRideOnBubble(groupName, msgText, convId, msgId);
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

            // 1. HÀM GỬI REPLY 2 LỚP BẢO VỆ (API CHÍNH + DỰ PHÒNG GÕ TAY)
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
            "               let realMsgId = String(fakeMsgId || '');" +
            "               let isSent = false;" +
                            
                            // ==========================================
                            // PHƯƠNG ÁN 1: BẮN API NGẦM (GHIM ĐÚNG TIN)
                            // ==========================================
            "               try {" +
            "                   if (window.zMessenger && typeof window.zMessenger.sendMessage === 'function') {" +
            "                       let req = { toid: convId, msg: text, type: 1 };" +
            // BYPASS VÀO LÕI ZALO: Bơm mọi thuộc tính mà Zalo có thể đòi hỏi để ép nó phải ghim tin
            "                       if (realMsgId && !realMsgId.startsWith('TIME_') && realMsgId.length > 5) {" +
            "                           req.quote_msgId = realMsgId;" +
            "                           req.quote = {" +
            "                               msgId: realMsgId," +
            "                               globalMsgId: realMsgId," +
            "                               cliMsgId: realMsgId" +
            "                           };" +
            "                       }" +
            "                       window.zMessenger.sendMessage(req);" +
            "                       ZAutoBridge.onLoginSuccess('PA1: Đã chốt API', groupName);" + 
            "                       isSent = true;" +
            "                   }" +
            "               } catch(err1) { console.log('ZAuto PA1 Fail', err1); }" +

                            // ==========================================
                            // PHƯƠNG ÁN 2: DỰ PHÒNG GÕ TAY (NẾU PA1 THẤT BẠI)
                            // ==========================================
            "               if (!isSent) {" +
            "                   try {" +
            "                       let input = document.getElementById('richInput');" +
            "                       if(input) {" +
            "                           input.focus();" +
            "                           input.innerHTML = '';" +
            "                           document.execCommand('insertText', false, text);" +
            "                           input.dispatchEvent(new Event('input', {bubbles:true}));" + 
            "                           input.blur();" + 
            "                           let attempts = 0;" +
            "                           let trySend = setInterval(() => {" +
            "                               attempts++;" +
            "                               let btnSend = document.querySelector('#chat-input-container-id .send-msg-btn, .fa-Sent-msg_24_Line, [data-translate-title=\"STR_SEND\"]');" +
            "                               if (btnSend) {" +
            "                                   let tgt = btnSend.closest('.z--btn--v2') || btnSend.parentElement || btnSend;" +
            "                                   tgt.click();" +
            "                                   let key = Object.keys(tgt).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
            "                                   if(key && tgt[key] && tgt[key].onClick) tgt[key].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
            "                               }" +
            "                               let enterEvent = new KeyboardEvent('keydown', { bubbles: true, cancelable: true, keyCode: 13, which: 13, key: 'Enter', code: 'Enter' });" +
            "                               input.dispatchEvent(enterEvent);" +
            "                               if (input.innerHTML === '' || input.innerHTML === '<br>') {" +
            "                                   clearInterval(trySend);" +
            "                                   ZAutoBridge.onLoginSuccess('PA2: Đã chốt gõ tay', groupName);" +
            "                               } else if (attempts > 12) { clearInterval(trySend); }" +
            "                           }, 200);" + 
            "                       }" +
            "                   } catch(err2) { console.log('ZAuto PA2 Fail', err2); }" +
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
            
            // DEEP BYPASS: QUÉT VÉT CẠN MỌI TẦNG REACT FIBER ĐỂ LỘT TRẦN ID BỊ GIẤU
            "           let realMsgId = ''; var fullTxt = '';" +
            "           try {" +
            "               let id1 = msgItemEl.getAttribute('data-msg-id') || (msgItemEl.dataset ? msgItemEl.dataset.msgId : '');" +
            "               if (id1 && id1.length > 5) realMsgId = id1;" +
            
            "               let keys = Object.keys(msgItemEl);" +
            "               let rK = keys.find(k => k.startsWith('__reactFiber') || k.startsWith('__reactProps'));" +
            "               if (rK && msgItemEl[rK]) {" +
            "                   let node = msgItemEl[rK];" +
                                // Khoan ngược lên 4 lớp thư mục cha con của React để bới ID
            "                   for(let step = 0; step < 4; step++) {" +
            "                       if(!node) break;" +
            "                       let p = node.memoizedProps || node.pendingProps;" +
            "                       if (p) {" +
                                        // Liệt kê mọi bí danh mà Zalo có thể đặt cho tin nhắn
            "                           let objs = [p.data?.lastMsg, p.item?.lastMsg, p.lastMsg, p.message, p.msg, p.data, p.item, p];" +
            "                           for (let o of objs) {" +
            "                               if (o && typeof o === 'object') {" +
            "                                   let foundId = o.msgId || o.messageId || o.cliMsgId || o.globalMsgId;" +
            "                                   if (!realMsgId && foundId && String(foundId).length > 5) { realMsgId = String(foundId); }" +
            "                                   if (!fullTxt && typeof o.content === 'string' && o.content.trim() !== '') { fullTxt = o.content; }" +
            "                               }" +
            "                           }" +
            "                       }" +
            "                       node = node.return;" + // Leo lên thế hệ cha
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
            "               // ĐÃ XÓA LỆNH BONG BÓNG Ở ĐÂY ĐỂ TRÁNH HIỆN TIN RÁC " +
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
                    // RA LỆNH HIỆN BONG BÓNG THU NHỎ
            "       ZAutoBridge.showFloatingBubbleAction();" + 
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
    // HỆ THỐNG PHÁT BẢN GHI ÂM (BẢN FIX ĐÍCH DANH ID - KHÔNG BỊ ĐÈ TIN CŨ)
    // =========================================================
    public static void playSpecificAudio(final Activity activity, final String conversationId, final String msgId) {
        Activity safeActivity = activityRef != null ? activityRef.get() : activity;
        if (safeActivity == null || hiddenWebView == null) return;

        safeActivity.runOnUiThread(() -> {
            String js = "(function() {" +
                "   console.log('ZAuto: Bat dau tim nut Play cho ' + '" + msgId + "');" +
                // BƯỚC 1: MỞ NHÓM ZALO
                "   let item = document.querySelector('.msg-item[anim-data-id=\"" + conversationId + "\"] .conv-item');" +
                "   if(item) {" +
                "       let key = Object.keys(item).find(k => k.startsWith('__reactEventHandlers') || k.startsWith('__reactFiber'));" +
                "       if (key && item[key]) {" +
                "           if (item[key].onClick) item[key].onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                "           else if (item[key].return && item[key].return.memoizedProps.onClick) item[key].return.memoizedProps.onClick({preventDefault:()=>{}, stopPropagation:()=>{}});" +
                "       } else { item.click(); }" +
                "   }" +

                // BƯỚC 2: TÌM CHÍNH XÁC ID TIN NHẮN ĐỂ BẤM (KHÔNG BẤM BỪA TIN CUỐI CÙNG)
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
	// =========================================================
    // HỆ THỐNG BONG BÓNG CHAT NỔI (FLOATING BUBBLE VIP)
    // =========================================================
    private static android.view.WindowManager windowManager;
    private static View bubbleView;
    private static FrameLayout bubbleLayout;
    private static boolean isBubbleExpanded = false;

    // Hàm gọi hiển thị Bong bóng từ Python hoặc khi khởi động
    public static void showFloatingBubble(final Activity activity) {
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            try {
                // Kiểm tra quyền vẽ trên ứng dụng khác (SYSTEM_ALERT_WINDOW)
                if (android.os.Build.VERSION.SDK_INT >= 23 && !android.provider.Settings.canDrawOverlays(activity)) {
                    android.widget.Toast.makeText(activity, "Vui lòng cấp quyền 'Hiển thị trên ứng dụng khác' cho ZAuto!", android.widget.Toast.LENGTH_LONG).show();
                    Intent intent = new Intent(android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                            android.net.Uri.parse("package:" + activity.getPackageName()));
                    activity.startActivity(intent);
                    return;
                }

                if (bubbleView != null) return;

                windowManager = (android.view.WindowManager) activity.getSystemService(Context.WINDOW_SERVICE);
                bubbleLayout = new FrameLayout(activity);

                // Tạo giao diện hình tròn cho bong bóng (Dùng tạm text hoặc icon tùy bạn cấu hình nút res)
                android.widget.ImageView iconView = new android.widget.ImageView(activity);
                // Thử lấy ảnh profile làm avatar bong bóng cho đẹp
                try {
                    String imgPath = activity.getFilesDir().getAbsolutePath() + "/profile.jpg";
                    android.graphics.Bitmap bmp = android.graphics.BitmapFactory.decodeFile(imgPath);
                    if(bmp != null) iconView.setImageBitmap(bmp);
                    else iconView.setImageResource(android.R.drawable.ic_menu_call);
                } catch(Exception ignored) {
                    iconView.setImageResource(android.R.drawable.ic_menu_call);
                }

                // Cấu hình bo tròn góc cho bong bóng nổi
                iconView.setBackgroundColor(android.graphics.Color.parseColor("#1A73E8"));
                iconView.setPadding(20, 20, 20, 20);

                final android.view.WindowManager.LayoutParams params = new android.view.WindowManager.LayoutParams(
                        android.view.WindowManager.LayoutParams.WRAP_CONTENT,
                        android.view.WindowManager.LayoutParams.WRAP_CONTENT,
                        android.os.Build.VERSION.SDK_INT >= 26 ? 
                                android.view.WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY : 
                                android.view.WindowManager.LayoutParams.TYPE_PHONE,
                        android.view.WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                        android.graphics.PixelFormat.TRANSLUCENT
                );

                params.gravity = android.view.Gravity.TOP | android.view.Gravity.LEFT;
                params.x = 0;
                params.y = 300; // Chiều cao xuất hiện ban đầu

                bubbleLayout.addView(iconView, new FrameLayout.LayoutParams(150, 150));
                bubbleView = bubbleLayout;

                // Thêm sự kiện Kéo thả (Drag and Drop) di chuyển bong bóng và Click mở App
                bubbleView.setOnTouchListener(new android.view.View.OnTouchListener() {
                    private int lastAction;
                    private int initialX, initialY;
                    private float initialTouchX, initialTouchY;

                    @Override
                    public boolean onTouch(View v, android.view.MotionEvent event) {
                        switch (event.getAction()) {
                            case android.view.MotionEvent.ACTION_DOWN:
                                initialX = params.x; initialY = params.y;
                                initialTouchX = event.getRawX(); initialTouchY = event.getRawY();
                                lastAction = event.getAction();
                                return true;
                            case android.view.MotionEvent.ACTION_UP:
                                if (lastAction == android.view.MotionEvent.ACTION_DOWN) {
                                    // YÊU CẦU: Bấm vào bong bóng để bật lại App lên màn hình chính
                                    Intent intent = activity.getPackageManager().getLaunchIntentForPackage(activity.getPackageName());
                                    if (intent != null) {
                                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                        activity.startActivity(intent);
                                    }
                                }
                                lastAction = event.getAction();
                                return true;
                            case android.view.MotionEvent.ACTION_MOVE:
                                params.x = initialX + (int) (event.getRawX() - initialTouchX);
                                params.y = initialY + (int) (event.getRawY() - initialTouchY);
                                windowManager.updateViewLayout(bubbleView, params);
                                lastAction = event.getAction();
                                return true;
                        }
                        return false;
                    }
                });

                windowManager.addView(bubbleView, params);

            } catch (Exception e) {
                Log.e(TAG, "Loi showFloatingBubble: ", e);
            }
        });
    }

    // Hàm giấu ẩn bong bóng chat khi tắt trong cài đặt
    public static void hideFloatingBubble(final Activity activity) {
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            try {
                if (windowManager != null && bubbleView != null) {
                    windowManager.removeView(bubbleView);
                    bubbleView = null;
                    bubbleLayout = null;
                }
            } catch (Exception ignored) {}
        });
    }

    // YÊU CẦU NÂNG CẤP: Bung rộng khung nhận cuốc kèm nút bấm trực tiếp khi tắt Auto Chốt
    public static void showNewRideOnBubble(final String groupName, final String msgText, final String convId, final String msgId) {
        Activity activity = activityRef != null ? activityRef.get() : null;
        if (activity == null || bubbleLayout == null) return;

        activity.runOnUiThread(() -> {
            try {
                // Xóa bỏ giao diện thu nhỏ cũ
                bubbleLayout.removeAllViews();

                // Tạo khung bảng thông báo cuốc xe nổi
                android.widget.LinearLayout container = new android.widget.LinearLayout(activity);
                container.setOrientation(android.widget.LinearLayout.VERTICAL);
                container.setBackgroundColor(android.graphics.Color.WHITE);
                container.setPadding(30, 30, 30, 30);
                
                // Set khung viền bo góc sắc nét chuẩn VIP
                android.graphics.drawable.GradientDrawable shape = new android.graphics.drawable.GradientDrawable();
                shape.setCornerRadius(25);
                shape.setColor(android.graphics.Color.WHITE);
                shape.setStroke(4, android.graphics.Color.parseColor("#1A73E8"));
                container.setBackground(shape);

                // Thêm chữ tên Nhóm Zalo
                android.widget.TextView tvGroup = new android.widget.TextView(activity);
                tvGroup.setText("🚖 " + groupName);
                tvGroup.setTextSize(16);
                tvGroup.setTextColor(android.graphics.Color.BLACK);
                tvGroup.setTypeface(null, android.graphics.Typeface.BOLD);
                container.addView(tvGroup);

                // Thêm nội dung cuốc xe khách gõ
                android.widget.TextView tvMsg = new android.widget.TextView(activity);
                tvMsg.setText(msgText);
                tvMsg.setTextSize(14);
                tvMsg.setPadding(0, 10, 0, 20);
                tvMsg.setTextColor(android.graphics.Color.DKGRAY);
                container.addView(tvMsg);

                // Hộp ngang chứa 2 nút Nhận và Bỏ Qua
                android.widget.LinearLayout rowButtons = new android.widget.LinearLayout(activity);
                rowButtons.setOrientation(android.widget.LinearLayout.HORIZONTAL);
                rowButtons.setGravity(android.view.Gravity.CENTER);

                // NÚT 1: BỎ QUA CUỐC XE
                android.widget.Button btnIgnore = new android.widget.Button(activity);
                btnIgnore.setText("BỎ QUA");
                btnIgnore.setTextColor(android.graphics.Color.RED);
                btnIgnore.setBackgroundColor(android.graphics.Color.parseColor("#FFEAEA"));
                btnIgnore.setOnClickListener(v -> {
                    // Chạm bỏ qua: Thu nhỏ bong bóng về trạng thái cũ ngay lập tức
                    resetBubbleToIcon(activity);
                });
                rowButtons.addView(btnIgnore, new android.widget.LinearLayout.LayoutParams(250, 110));

                // Khoảng cách giữa 2 nút
                View space = new View(activity);
                rowButtons.addView(space, new android.widget.LinearLayout.LayoutParams(40, 1));

                // NÚT 2: NHẬN CUỐC (Bấm trực tiếp ghi đè chuẩn xác cuốc xe)
                android.widget.Button btnAccept = new android.widget.Button(activity);
                btnAccept.setText("NHẬN CUỐC");
                btnAccept.setTextColor(android.graphics.Color.WHITE);
                btnAccept.setBackgroundColor(android.graphics.Color.parseColor("#1A73E8"));
                btnAccept.setOnClickListener(v -> {
                    // ĐÃ SỬA: Lấy giờ phút thực tế ngay lúc tài xế bấm nút trên bong bóng
                    String clickTime = new java.text.SimpleDateFormat("HH:mm", java.util.Locale.getDefault()).format(new java.util.Date());
                    
                    // Truyền đủ tham số: nội dung cuốc xe (msgText) và thời gian thực (clickTime) xuống lõi xử lý
                    sendReplyToSpecificMessage(activity, convId, msgId, "Ok nhận", msgText, clickTime);
                    resetBubbleToIcon(activity);
                });
                rowButtons.addView(btnAccept, new android.widget.LinearLayout.LayoutParams(350, 110));

                container.addView(rowButtons);
                bubbleLayout.addView(container, new FrameLayout.LayoutParams(750, ViewGroup.LayoutParams.WRAP_CONTENT));

            } catch (Exception e) {
                Log.e(TAG, "Loi showNewRideOnBubble: ", e);
            }
        });
    }

    // Hàm bổ trợ: Đưa bong bóng lớn thu gọn lại thành icon tròn sau khi thao tác xong
    private static void resetBubbleToIcon(Context context) {
        if (bubbleLayout == null) return;
        bubbleLayout.removeAllViews();
        android.widget.ImageView iconView = new android.widget.ImageView(context);
        try {
            String imgPath = context.getFilesDir().getAbsolutePath() + "/profile.jpg";
            android.graphics.Bitmap bmp = android.graphics.BitmapFactory.decodeFile(imgPath);
            if(bmp != null) iconView.setImageBitmap(bmp);
            else iconView.setImageResource(android.R.drawable.ic_menu_call);
        } catch(Exception ignored) {
            iconView.setImageResource(android.R.drawable.ic_menu_call);
        }
        iconView.setBackgroundColor(android.graphics.Color.parseColor("#1A73E8"));
        iconView.setPadding(20, 20, 20, 20);
        bubbleLayout.addView(iconView, new FrameLayout.LayoutParams(150, 150));
    }
}
