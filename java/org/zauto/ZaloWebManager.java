package org.zauto;

import android.app.Activity;
import android.app.Dialog;
import android.content.Context;
import android.content.Intent;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.util.Log;

public class ZaloWebManager {
    public static WebView hiddenWebView; // Lưu lại để Python gọi hàm JS

    // LỚP CẦU NỐI NHẬN DỮ LIỆU TỪ JS
    public static class WebAppInterface {
        Context mContext;
        WebAppInterface(Context c) { mContext = c; }

        @JavascriptInterface
        public void onLoginSuccess() {
            mContext.sendBroadcast(new Intent("org.zauto.taxi.LOGIN_SUCCESS"));
        }

        @JavascriptInterface
        public void onNewMessage(String group, String message) {
            Intent intent = new Intent("org.zauto.taxi.WEB_NEW_MSG");
            intent.putExtra("group", group);
            intent.putExtra("msg", message);
            mContext.sendBroadcast(intent);
        }

        @JavascriptInterface
        public void onGroupsScraped(String jsonGroupList) {
            Intent intent = new Intent("org.zauto.taxi.WEB_GROUPS");
            intent.putExtra("data", jsonGroupList);
            mContext.sendBroadcast(intent);
        }
    }

    public static void openZaloWebQR(Activity activity) {
        activity.runOnUiThread(() -> {
            Dialog dialog = new Dialog(activity, android.R.style.Theme_NoTitleBar_Fullscreen);
            hiddenWebView = new WebView(activity);
            
            WebSettings settings = hiddenWebView.getSettings();
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(true);
            settings.setDatabaseEnabled(true);
            settings.setSupportMultipleWindows(true);
            settings.setJavaScriptCanOpenWindowsAutomatically(true);
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
            settings.setUserAgentString("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");

            CookieManager cookieManager = CookieManager.getInstance();
            cookieManager.setAcceptCookie(true);
            cookieManager.setAcceptThirdPartyCookies(hiddenWebView, true);

            // Gắn Cầu Nối: JS gọi window.ZAutoBridge.ham_cua_java()
            hiddenWebView.addJavascriptInterface(new WebAppInterface(activity), "ZAutoBridge");

            hiddenWebView.setWebViewClient(new WebViewClient() {
                @Override
                public void onPageFinished(WebView view, String url) {
                    super.onPageFinished(view, url);
                    
                    // =========================================================
                    // MÃ JAVASCRIPT ĐƯỢC TIÊM (INJECT) VÀO ZALO WEB
                    // =========================================================
                    String jsPayload = 
                        "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});" +
                        "setInterval(function() {" +
                        "  if(document.querySelectorAll('.nav__tabs__zalo').length > 0 && !window.zauto_logged) {" +
                        "    window.zauto_logged = true;" +
                        "    ZAutoBridge.onLoginSuccess();" + // Báo về Java
                        "    startDOMObserver();" + // Khởi động mắt thần
                        "  }" +
                        "}, 2000);" +
                        
                        // HÀM MẮT THẦN: Lắng nghe DOM để bắt tin nhắn mới không cần chờ Notification
                        "function startDOMObserver() {" +
                        "  const observer = new MutationObserver(mutations => {" +
                        "    mutations.forEach(m => {" +
                        "      if(m.addedNodes.length > 0) {" +
                        "         try {" +
                        "           let msgNode = document.querySelector('.message-view__bubble__text');" + // Class text của Zalo Web
                        "           let groupNode = document.querySelector('.header-title');" +
                        "           if(msgNode && groupNode && msgNode.innerText !== window.lastMsg) {" +
                        "               window.lastMsg = msgNode.innerText;" +
                        "               ZAutoBridge.onNewMessage(groupNode.innerText, msgNode.innerText);" +
                        "           }" +
                        "         } catch(e) {}" +
                        "      }" +
                        "    });" +
                        "  });" +
                        "  observer.observe(document.body, {childList: true, subtree: true});" +
                        "};" +

                        // HÀM GỬI TIN NGẦM TỪ PYTHON GỌI XUỐNG
                        "window.sendHiddenMessage = function(text) {" +
                        "  let input = document.getElementById('richInput');" + // ID ô nhập liệu Zalo Web
                        "  if(input) {" +
                        "    input.innerHTML = text;" +
                        "    let event = new Event('input', { bubbles: true });" +
                        "    input.dispatchEvent(event);" +
                        "    setTimeout(() => {" +
                        "       let btn = document.querySelector('[icon=\"icn-Send-Solid\"]');" + // Nút gửi
                        "       if(btn) btn.click();" +
                        "    }, 300);" +
                        "  }" +
                        "};";
                    
                    view.evaluateJavascript(jsPayload, null);
                }
            });

            hiddenWebView.loadUrl("https://chat.zalo.me");
            dialog.setContentView(hiddenWebView);
            dialog.show();
            
            // Ẩn Dialog đi, để WebView chạy ngầm phía sau
            // dialog.dismiss(); <- Nếu anh muốn nó chạy hoàn toàn ngầm không hiện UI
        });
    }

    // Python sẽ gọi hàm này để ra lệnh cho JS gửi tin
    public static void executeJS(Activity activity, String jsCode) {
        if (hiddenWebView != null) {
            activity.runOnUiThread(() -> {
                hiddenWebView.evaluateJavascript(jsCode, null);
            });
        }
    }
}
