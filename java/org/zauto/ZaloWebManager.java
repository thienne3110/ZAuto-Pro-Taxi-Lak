package org.zauto;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.view.View;
import android.widget.FrameLayout;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.util.Log;

public class ZaloWebManager {

    public static WebView hiddenWebView;
    private static FrameLayout.LayoutParams layoutParams;
    private static boolean isInitialized = false;

    // =========================================================
    // BRIDGE JAVA <-> JAVASCRIPT
    // =========================================================
    public static class WebAppInterface {
        Context mContext;

        WebAppInterface(Context c) {
            mContext = c;
        }

        @JavascriptInterface
        public void onLoginSuccess(String name, String avatar) {
            try {
                Intent intent = new Intent("org.zauto.taxi.LOGIN_SUCCESS");
                intent.putExtra("zalo_name", name);
                intent.putExtra("zalo_avatar", avatar);
                mContext.sendBroadcast(intent);
                Log.d("ZAUTO", "LOGIN SUCCESS: " + name);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        @JavascriptInterface
        public void onNewWebMsg(String group, String msg) {
            try {
                Intent intent = new Intent("org.zauto.taxi.WEB_NEW_MSG");
                intent.putExtra("group", group);
                intent.putExtra("msg", msg);
                mContext.sendBroadcast(intent);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        @JavascriptInterface
        public void onGroupListReceived(String jsonGroups) {
            try {
                Intent intent = new Intent("org.zauto.taxi.GROUPS_DATA");
                intent.putExtra("groups_list", jsonGroups);
                mContext.sendBroadcast(intent);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    // =========================================================
    // KHỞI TẠO WEBVIEW (CHẠY NGẦM BAN ĐẦU)
    // =========================================================
    public static void initWebView(final Activity activity) {
        if (isInitialized) return;

        activity.runOnUiThread(() -> {
            // [FIX] Bật Debug để kiểm tra qua Chrome Inspect nếu cần
            WebView.setWebContentsDebuggingEnabled(true);

            hiddenWebView = new WebView(activity);
            
            // [FIX ANDROID 14] Ép render bằng phần cứng, chống lỗi không hiện WebView
            hiddenWebView.setLayerType(View.LAYER_TYPE_HARDWARE, null);

            WebSettings settings = hiddenWebView.getSettings();
            
            // Cài đặt bắt buộc cho JS
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(true);
            settings.setDatabaseEnabled(true);
            
            // Cài đặt hỗ trợ file & nội dung
            settings.setAllowFileAccess(true);
            settings.setAllowContentAccess(true);
            settings.setMediaPlaybackRequiresUserGesture(false);
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
            settings.setUseWideViewPort(true);
            settings.setLoadWithOverviewMode(true);
            settings.setSupportZoom(false);
            settings.setBuiltInZoomControls(false);
            settings.setDisplayZoomControls(false);
            settings.setCacheMode(WebSettings.LOAD_DEFAULT);

            // [THÊM SETTINGS CỰC QUAN TRỌNG] Chống trắng QR, mở khóa JS tối đa
            settings.setJavaScriptCanOpenWindowsAutomatically(true);
            settings.setSupportMultipleWindows(true);
            settings.setLoadsImagesAutomatically(true);
            settings.setBlockNetworkImage(false);
            settings.setBlockNetworkLoads(false);
            settings.setAllowUniversalAccessFromFileURLs(true);
            settings.setAllowFileAccessFromFileURLs(true);

            // Giả lập máy tính để lấy QR Zalo Web
            settings.setUserAgentString(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                    "AppleWebKit/537.36 (KHTML, like Gecko) " +
                    "Chrome/122.0.0.0 Safari/537.36"
            );

            CookieManager cookieManager = CookieManager.getInstance();
            cookieManager.setAcceptCookie(true);
            cookieManager.setAcceptThirdPartyCookies(hiddenWebView, true);

            hiddenWebView.addJavascriptInterface(new WebAppInterface(activity), "ZAutoBridge");
            hiddenWebView.setWebChromeClient(new WebChromeClient());
            
            hiddenWebView.setWebViewClient(new WebViewClient() {
                @Override
                public void onPageFinished(WebView view, String url) {
                    super.onPageFinished(view, url);
                    
                    view.postDelayed(() -> {
                        try {
                            String jsPayload =
                                    "Object.defineProperty(navigator,'platform',{get:()=> 'Win32'});" +
                                    "window.sendHiddenMessage = function(text) {" +
                                    "   try {" +
                                    "       let input = document.querySelector('[contenteditable=\"true\"]');" +
                                    "       if(input) {" +
                                    "           input.focus();" +
                                    "           document.execCommand('insertText', false, text);" +
                                    "           input.dispatchEvent(new Event('input',{bubbles:true}));" +
                                    "           setTimeout(() => {" +
                                    "               let btn = document.querySelector('[icon=\"icn-send\"], button[type=\"submit\"]');" +
                                    "               if(btn) btn.click();" +
                                    "           }, 500);" +
                                    "       }" +
                                    "   } catch(e) {}" +
                                    "};" +
                                    "window.getZaloGroups = function() {" +
                                    "   try {" +
                                    "       let groups = [];" +
                                    "       let elements = document.querySelectorAll('.conv-item-title__name, .group-name, span.truncate');" +
                                    "       elements.forEach(el => {" +
                                    "           try {" +
                                    "               let txt = el.innerText;" +
                                    "               if(txt && txt.length > 1 && txt.length < 60) {" +
                                    "                   if(!groups.includes(txt)) {" +
                                    "                       groups.push(txt);" +
                                    "                   }" +
                                    "               }" +
                                    "           } catch(e) {}" +
                                    "       });" +
                                    "       if(groups.length > 0) {" +
                                    "           ZAutoBridge.onGroupListReceived(JSON.stringify(groups.slice(0,100)));" +
                                    "       }" +
                                    "   } catch(e) {}" +
                                    "};" +
                                    "setInterval(() => {" +
                                    "   try {" +
                                    "       if(window.location.href.includes('chat.zalo.me')) {" +
                                    "           if(!window.zauto_logged) {" +
                                    "               let name = 'Đã kết nối';" +
                                    "               let avatar = '';" +
                                    "               try {" +
                                    "                   let imgs = document.querySelectorAll('img');" +
                                    "                   imgs.forEach(i => {" +
                                    "                       try {" +
                                    "                           if(i.src && i.src.includes('avatar')) {" +
                                    "                               avatar = i.src;" +
                                    "                           }" +
                                    "                       } catch(e) {}" +
                                    "                   });" +
                                    "                   let titleEl = document.querySelector('[data-translate-inner]');" +
                                    "                   if(titleEl) {" +
                                    "                       name = titleEl.innerText;" +
                                    "                   }" +
                                    "               } catch(e) {}" +
                                    "               window.zauto_logged = true;" +
                                    "               ZAutoBridge.onLoginSuccess(name, avatar);" +
                                    "           }" +
                                    "           window.getZaloGroups();" +
                                    "           try {" +
                                    "               let msgs = document.querySelectorAll('.msg-item');" +
                                    "               if(msgs.length > 0) {" +
                                    "                   let lastMsgEl = msgs[msgs.length - 1];" +
                                    "                   let msgText = lastMsgEl.innerText;" +
                                    "                   let msgId = lastMsgEl.getAttribute('data-id') || msgText;" +
                                    "                   let groupName = 'Nhóm Zalo';" +
                                    "                   let header = document.querySelector('.header-title');" +
                                    "                   if(header) {" +
                                    "                       groupName = header.innerText;" +
                                    "                   }" +
                                    "                   if(window.last_zauto_id !== msgId) {" +
                                    "                       window.last_zauto_id = msgId;" +
                                    "                       if(!msgText.includes('Ok nhận')) {" +
                                    "                           ZAutoBridge.onNewWebMsg(groupName, msgText);" +
                                    "                       }" +
                                    "                   }" +
                                    "               }" +
                                    "           } catch(e) {}" +
                                    "       }" +
                                    "   } catch(e) {}" +
                                    "}, 2000);";

                            view.evaluateJavascript(jsPayload, null);
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }, 5000);
                }
            });

            // Tải trang Zalo
            hiddenWebView.loadUrl("https://id.zalo.me/account?continue=https://chat.zalo.me");
            
            // [FIX QR TRẮNG] Khởi động lại Timer & State ngay lập tức để ép WebView hoạt động
            hiddenWebView.resumeTimers();
            hiddenWebView.onResume();

            hiddenWebView.setVisibility(View.GONE);

            layoutParams = new FrameLayout.LayoutParams(0, 0);
            activity.addContentView(hiddenWebView, layoutParams);
            
            isInitialized = true;
            Log.d("ZAUTO", "Embedded WebView Initialized Success with Full Hardware fixes");
        });
    }

    // =========================================================
    // HIỂN THỊ VÀ ĐỊNH VỊ WEBVIEW ĐÈ LÊN KHUNG
    // =========================================================
    public static void showWebView(final Activity activity, final int x, final int y, final int w, final int h) {
        if (hiddenWebView == null) return;
        activity.runOnUiThread(() -> {
            // Fix lỗi width=0 height=0
            layoutParams.width = (w > 0) ? w : FrameLayout.LayoutParams.MATCH_PARENT;
            layoutParams.height = (h > 0) ? h : FrameLayout.LayoutParams.MATCH_PARENT;
            layoutParams.leftMargin = x;
            layoutParams.topMargin = y;
            hiddenWebView.setLayoutParams(layoutParams);
            
            hiddenWebView.setVisibility(View.VISIBLE);
            hiddenWebView.bringToFront();
        });
    }

    // =========================================================
    // ẨN WEBVIEW
    // =========================================================
    public static void hideWebView() {
        if (hiddenWebView == null) return;
        hiddenWebView.post(() -> hiddenWebView.setVisibility(View.GONE));
    }

    // =========================================================
    // THỰC THI JS
    // =========================================================
    public static void executeJS(Activity activity, String jsCode) {
        try {
            if (hiddenWebView != null) {
                activity.runOnUiThread(() -> {
                    try {
                        hiddenWebView.evaluateJavascript(jsCode, null);
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                });
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // =========================================================
    // ĐĂNG XUẤT
    // =========================================================
    public static void logoutAndClearData(Activity activity) {
        if (hiddenWebView != null) {
            activity.runOnUiThread(() -> {
                CookieManager cookieManager = CookieManager.getInstance();
                cookieManager.removeAllCookies(null);
                cookieManager.flush();
                
                hiddenWebView.clearCache(true);
                hiddenWebView.clearHistory();
                
                hiddenWebView.loadUrl("https://id.zalo.me/account?continue=https://chat.zalo.me");
                hiddenWebView.resumeTimers();
                hiddenWebView.onResume();
                
                Log.d("ZAUTO", "Đã xoá phiên đăng nhập Zalo Web");
                
                hiddenWebView.evaluateJavascript("window.zauto_logged = false;", null);
            });
        }
    }
}
