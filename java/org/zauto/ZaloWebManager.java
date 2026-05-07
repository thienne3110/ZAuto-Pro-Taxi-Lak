package org.zauto;

import android.app.Activity;
import android.app.Dialog;
import android.content.Context;
import android.content.Intent;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.graphics.Color;
import android.view.Gravity;
import android.widget.Button;
import android.widget.FrameLayout;

public class ZaloWebManager {
    public static WebView hiddenWebView;

    public static class WebAppInterface {
        Context mContext;
        WebAppInterface(Context c) { mContext = c; }

        @JavascriptInterface
        public void onLoginSuccess(String name, String avatar) { 
            // Gửi Broadcast kèm theo Tên và Avatar lấy được từ Web
            Intent intent = new Intent("org.zauto.taxi.LOGIN_SUCCESS");
            intent.putExtra("zalo_name", name);
            intent.putExtra("zalo_avatar", avatar);
            mContext.sendBroadcast(intent); 
        }
    }

    public static void openZaloWebQR(Activity activity) {
        activity.runOnUiThread(() -> {
            Dialog dialog = new Dialog(activity, android.R.style.Theme_NoTitleBar_Fullscreen);
            
            // Tạo Layout để chứa WebView và nút Đóng
            FrameLayout layout = new FrameLayout(activity);
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
                    
                    // Đoạn Script thần thánh để lấy thông tin tài khoản
                    String jsPayload = 
                        "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});" +
                        "window.sendHiddenMessage = function(text) {" +
                        "  let input = document.getElementById('richInput');" +
                        "  if(input) {" +
                        "    input.focus();" +
                        "    document.execCommand('insertText', false, text);" +
                        "    let event = new Event('input', { bubbles: true });" +
                        "    input.dispatchEvent(event);" +
                        "    setTimeout(() => {" +
                        "       let btn = document.querySelector('[icon=\"icn-Send-Solid\"], .fa-send-solid');" +
                        "       if(btn) btn.click();" +
                        "    }, 400);" +
                        "  }" +
                        "};" +
                        "setInterval(() => {" +
                        "  let nav = document.querySelector('.nav__tabs__zalo');" +
                        "  if(nav && !window.zauto_logged) {" +
                        "    let name = 'Tài khoản Zalo';" +
                        "    let avatar = 'profile.jpg';" +
                        "    try {" +
                        "       let imgEl = document.querySelector('.main-nav__profile img');" +
                        "       if(imgEl) avatar = imgEl.src;" +
                        "       /* Tìm tên người dùng trong tooltip hoặc title */" +
                        "       let profileEl = document.querySelector('.main-nav__profile');" +
                        "       if(profileEl) name = profileEl.getAttribute('title') || 'Đã kết nối';" +
                        "    } catch(e) {}" +
                        "    window.zauto_logged = true;" +
                        "    ZAutoBridge.onLoginSuccess(name, avatar);" +
                        "  }" +
                        "}, 3000);";
                    view.evaluateJavascript(jsPayload, null);
                }
            });

            hiddenWebView.loadUrl("https://chat.zalo.me");
            
            // Thêm nút "X ĐÓNG & CHẠY NGẦM" như anh yêu cầu
            Button btnClose = new Button(activity);
            btnClose.setText("X ĐÓNG & CHẠY NGẦM");
            btnClose.setBackgroundColor(Color.RED);
            btnClose.setTextColor(Color.WHITE);
            FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, 
                FrameLayout.LayoutParams.WRAP_CONTENT
            );
            lp.gravity = Gravity.TOP | Gravity.RIGHT;
            lp.setMargins(0, 30, 30, 0);
            btnClose.setLayoutParams(lp);
            btnClose.setOnClickListener(v -> dialog.dismiss());

            layout.addView(hiddenWebView);
            layout.addView(btnClose);
            
            dialog.setContentView(layout);
            dialog.show();
        });
    }

    public static void executeJS(Activity activity, String jsCode) {
        if (hiddenWebView != null) {
            activity.runOnUiThread(() -> hiddenWebView.evaluateJavascript(jsCode, null));
        }
    }
}
