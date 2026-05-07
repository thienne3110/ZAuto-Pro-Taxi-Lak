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

public class ZaloWebManager {
    public static WebView hiddenWebView;

    public static class WebAppInterface {
        Context mContext;
        WebAppInterface(Context c) { mContext = c; }
        @JavascriptInterface
        public void onLoginSuccess() { mContext.sendBroadcast(new Intent("org.zauto.taxi.LOGIN_SUCCESS")); }
    }

    public static void openZaloWebQR(Activity activity) {
        activity.runOnUiThread(() -> {
            Dialog dialog = new Dialog(activity, android.R.style.Theme_NoTitleBar_Fullscreen);
            hiddenWebView = new WebView(activity);
            
            WebSettings settings = hiddenWebView.getSettings();
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(true);
            settings.setDatabaseEnabled(true);
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
            settings.setUserAgentString("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");

            CookieManager cookieManager = CookieManager.getInstance();
            cookieManager.setAcceptCookie(true);
            cookieManager.setAcceptThirdPartyCookies(hiddenWebView, true);

            hiddenWebView.addJavascriptInterface(new WebAppInterface(activity), "ZAutoBridge");

            hiddenWebView.setWebViewClient(new WebViewClient() {
                @Override
                public void onPageFinished(WebView view, String url) {
                    super.onPageFinished(view, url);
                    String jsPayload = 
                        "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});" +
                        "window.sendHiddenMessage = function(text) {" +
                        "  let input = document.getElementById('richInput');" +
                        "  if(input) {" +
                        "    input.focus();" +
                        "    document.execCommand('selectAll', false, null);" +
                        "    document.execCommand('insertText', false, text);" +
                        "    let event = new Event('input', { bubbles: true, cancelable: true });" +
                        "    input.dispatchEvent(event);" +
                        "    setTimeout(() => {" +
                        "       let btn = document.querySelector('[icon=\"icn-Send-Solid\"], .fa-send-solid');" +
                        "       if(btn) btn.click();" +
                        "    }, 400);" +
                        "  }" +
                        "};" +
                        "setInterval(() => {" +
                        "  if(document.querySelectorAll('.nav__tabs__zalo').length > 0 && !window.zauto_logged) {" +
                        "    window.zauto_logged = true;" +
                        "    ZAutoBridge.onLoginSuccess();" +
                        "  }" +
                        "}, 2000);";
                    view.evaluateJavascript(jsPayload, null);
                }
            });

            hiddenWebView.loadUrl("https://chat.zalo.me");
            dialog.setContentView(hiddenWebView);
            dialog.show();
        });
    }

    public static void executeJS(Activity activity, String jsCode) {
        if (hiddenWebView != null) {
            activity.runOnUiThread(() -> hiddenWebView.evaluateJavascript(jsCode, null));
        }
    }
}
