package org.zauto;

import android.app.Activity;
import android.app.Dialog;
import android.content.Intent;
import android.webkit.CookieManager;
import android.webkit.ConsoleMessage;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class ZaloWebManager {
    public static void openZaloWebQR(Activity activity) {
        activity.runOnUiThread(() -> {
            Dialog dialog = new Dialog(activity, android.R.style.Theme_NoTitleBar_Fullscreen);
            WebView wv = new WebView(activity);
            
            WebSettings settings = wv.getSettings();
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(true);
            settings.setDatabaseEnabled(true);
            settings.setSupportMultipleWindows(true);
            settings.setJavaScriptCanOpenWindowsAutomatically(true);
            settings.setLoadWithOverviewMode(true);
            settings.setUseWideViewPort(true);
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
            
            // FAKE PC Bắt Buộc Để Hiện Mã QR
            settings.setUserAgentString("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");

            CookieManager cookieManager = CookieManager.getInstance();
            cookieManager.setAcceptCookie(true);
            cookieManager.setAcceptThirdPartyCookies(wv, true);

            // Bắt sự kiện Login Thành Công (JS trả về Console)
            wv.setWebChromeClient(new WebChromeClient() {
                @Override
                public boolean onConsoleMessage(ConsoleMessage consoleMessage) {
                    if (consoleMessage.message().contains("ZAUTO_LOGIN_SUCCESS")) {
                        activity.sendBroadcast(new Intent("org.zauto.taxi.LOGIN_SUCCESS"));
                        cookieManager.flush();
                        dialog.dismiss();
                    }
                    return super.onConsoleMessage(consoleMessage);
                }
            });

            // Chờ load xong mới Inject JS
            wv.setWebViewClient(new WebViewClient() {
                @Override
                public void onPageFinished(WebView view, String url) {
                    super.onPageFinished(view, url);
                    String jsCode = 
                        "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});" +
                        "setInterval(function() {" +
                        "  if(document.querySelectorAll('.nav__tabs__zalo').length > 0) {" +
                        "    console.log('ZAUTO_LOGIN_SUCCESS');" +
                        "  }" +
                        "}, 2500);";
                    view.evaluateJavascript(jsCode, null);
                }
            });

            wv.loadUrl("https://chat.zalo.me");
            dialog.setContentView(wv);
            dialog.show();
        });
    }
}
