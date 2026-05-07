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
import android.util.Log;

public class ZaloWebManager {
    public static WebView hiddenWebView;

    public static class WebAppInterface {
        Context mContext;
        WebAppInterface(Context c) { mContext = c; }

        // 1. Nhận tín hiệu đăng nhập thành công
        @JavascriptInterface
        public void onLoginSuccess(String name, String avatar) { 
            Intent intent = new Intent("org.zauto.taxi.LOGIN_SUCCESS");
            intent.putExtra("zalo_name", name);
            intent.putExtra("zalo_avatar", avatar);
            mContext.sendBroadcast(intent); 
        }

        // 2. Nhận tin nhắn mới trực tiếp từ Web
        @JavascriptInterface
        public void onNewWebMsg(String group, String msg) {
            Intent intent = new Intent("org.zauto.taxi.WEB_NEW_MSG");
            intent.putExtra("group", group);
            intent.putExtra("msg", msg);
            mContext.sendBroadcast(intent);
        }

        // 3. Nhận danh sách nhóm để Python hiển thị
        @JavascriptInterface
        public void onGroupListReceived(String jsonGroups) {
            Intent intent = new Intent("org.zauto.taxi.GROUPS_DATA");
            intent.putExtra("groups_list", jsonGroups);
            mContext.sendBroadcast(intent);
        }
    }

    public static void openZaloWebQR(Activity activity) {
        activity.runOnUiThread(() -> {
            Dialog dialog = new Dialog(activity, android.R.style.Theme_NoTitleBar_Fullscreen);
            
            FrameLayout layout = new FrameLayout(activity);
            hiddenWebView = new WebView(activity);
            
            WebSettings settings = hiddenWebView.getSettings();
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(true);
            settings.setDatabaseEnabled(true);
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
            
            // Giả lập trình duyệt Máy tính để Zalo cho phép quét QR
            settings.setUserAgentString("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36");

            CookieManager cookieManager = CookieManager.getInstance();
            cookieManager.setAcceptCookie(true);
            cookieManager.setAcceptThirdPartyCookies(hiddenWebView, true);

            hiddenWebView.addJavascriptInterface(new WebAppInterface(activity), "ZAutoBridge");

            hiddenWebView.setWebViewClient(new WebViewClient() {
                @Override
                public void onPageFinished(WebView view, String url) {
                    super.onPageFinished(view, url);
                    
                    // --- ĐỘNG CƠ JAVASCRIPT TỔNG HỢP ---
                    String jsPayload = 
                        "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});" +
                        
                        // HÀM 1: GỬI TIN NHẮN
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
                        "    }, 500);" +
                        "  }" +
                        "};" +

                        // HÀM 2: QUÉT DANH SÁCH NHÓM
                        "window.getZaloGroups = function() {" +
                        "  let groups = [];" +
                        "  document.querySelectorAll('.conv-item-title__name').forEach(el => {" +
                        "    groups.push(el.innerText);" +
                        "  });" +
                        "  if(groups.length > 0) ZAutoBridge.onGroupListReceived(JSON.stringify(groups));" +
                        "};" +

                        // HÀM 3: THEO DÕI TIN NHẮN MỚI & TRẠNG THÁI ĐĂNG NHẬP
                        "setInterval(() => {" +
                        "  let nav = document.querySelector('.nav__tabs__zalo');" +
                        "  if(nav) {" +
                        "    /* Kiểm tra login lần đầu */" +
                        "    if(!window.zauto_logged) {" +
                        "      let name = 'Tài khoản Zalo';" +
                        "      let avatar = 'profile.jpg';" +
                        "      try {" +
                        "         let imgEl = document.querySelector('.main-nav__profile img');" +
                        "         if(imgEl) avatar = imgEl.src;" +
                        "         let profileEl = document.querySelector('.main-nav__profile');" +
                        "         if(profileEl) name = profileEl.getAttribute('title') || 'Đã kết nối';" +
                        "      } catch(e) {}" +
                        "      window.zauto_logged = true;" +
                        "      ZAutoBridge.onLoginSuccess(name, avatar);" +
                        "    }" +
                        "    /* Cập nhật danh sách nhóm định kỳ */" +
                        "    window.getZaloGroups();" +
                        "    " +
                        "    /* Đọc tin nhắn cuối cùng trên màn hình */" +
                        "    try {" +
                        "      let lastMsgEl = document.querySelector('.msg-item:last-child');" +
                        "      if(lastMsgEl) {" +
                        "        let msgId = lastMsgEl.getAttribute('data-id');" +
                        "        let msgText = lastMsgEl.innerText;" +
                        "        let groupName = document.querySelector('.header-title').innerText;" +
                        "        if(window.last_zauto_id !== msgId) {" +
                        "          window.last_zauto_id = msgId;" +
                        "          /* Chỉ báo tin nếu không phải tin mình vừa gửi */" +
                        "          if(!msgText.includes('em nhận') && !msgText.includes('Ok nhận')) {" +
                        "             ZAutoBridge.onNewWebMsg(groupName, msgText);" +
                        "          }" +
                        "        }" +
                        "      }" +
                        "    } catch(e) {}" +
                        "  }" +
                        "}, 2000);";
                    
                    view.evaluateJavascript(jsPayload, null);
                }
            });

            hiddenWebView.loadUrl("https://chat.zalo.me");
            
            // Nút đóng chuyên nghiệp
            Button btnClose = new Button(activity);
            btnClose.setText("X ĐÓNG & CHẠY NGẦM");
            btnClose.setBackgroundColor(Color.parseColor("#CC0000"));
            btnClose.setTextColor(Color.WHITE);
            btnClose.setPadding(20, 10, 20, 10);
            
            FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, 
                FrameLayout.LayoutParams.WRAP_CONTENT
            );
            lp.gravity = Gravity.TOP | Gravity.RIGHT;
            lp.setMargins(0, 40, 40, 0);
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
