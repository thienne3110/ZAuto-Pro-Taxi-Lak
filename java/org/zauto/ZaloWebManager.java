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
import android.graphics.Color;
import android.view.Gravity;
import android.widget.Button;
import android.widget.FrameLayout;
import android.util.Log;

public class ZaloWebManager {

    public static WebView hiddenWebView;

    // =========================================================
    // BRIDGE JAVA <-> JAVASCRIPT
    // =========================================================
    public static class WebAppInterface {

        Context mContext;

        WebAppInterface(Context c) {
            mContext = c;
        }

        // LOGIN SUCCESS
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

        // NEW MESSAGE
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

        // GROUP LIST
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
    // OPEN ZALO WEB
    // =========================================================
    public static void openZaloWebQR(Activity activity) {
        activity.runOnUiThread(() -> {

            Dialog dialog = new Dialog(
                    activity,
                    android.R.style.Theme_NoTitleBar_Fullscreen
            );

            FrameLayout layout = new FrameLayout(activity);
            hiddenWebView = new WebView(activity);

            // =====================================================
            // WEB SETTINGS
            // =====================================================
            WebSettings settings = hiddenWebView.getSettings();
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(true);
            settings.setDatabaseEnabled(true);
            settings.setAllowFileAccess(true);
            settings.setAllowContentAccess(true);
            settings.setLoadsImagesAutomatically(true);
            settings.setMediaPlaybackRequiresUserGesture(false);
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
            settings.setUseWideViewPort(true);
            settings.setLoadWithOverviewMode(true);
            settings.setSupportZoom(false);
            settings.setBuiltInZoomControls(false);
            settings.setDisplayZoomControls(false);
            settings.setCacheMode(WebSettings.LOAD_DEFAULT);

            // =====================================================
            // DESKTOP USER AGENT
            // =====================================================
            settings.setUserAgentString(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                    "AppleWebKit/537.36 (KHTML, like Gecko) " +
                    "Chrome/122.0.0.0 Safari/537.36"
            );

            // =====================================================
            // COOKIE
            // =====================================================
            CookieManager cookieManager = CookieManager.getInstance();
            cookieManager.setAcceptCookie(true);
            cookieManager.setAcceptThirdPartyCookies(hiddenWebView, true);

            // =====================================================
            // JS BRIDGE
            // =====================================================
            hiddenWebView.addJavascriptInterface(
                    new WebAppInterface(activity),
                    "ZAutoBridge"
            );

            // =====================================================
            // WEB CLIENT
            // =====================================================
            hiddenWebView.setWebChromeClient(new WebChromeClient());

            hiddenWebView.setWebViewClient(new WebViewClient() {
                @Override
                public void onPageFinished(WebView view, String url) {
                    super.onPageFinished(view, url);

                    // Delay để React render xong
                    view.postDelayed(() -> {
                        try {
                            String jsPayload =

                                    // =====================================
                                    // PLATFORM FIX
                                    // =====================================
                                    "Object.defineProperty(navigator,'platform',{get:()=> 'Win32'});" +

                                    // =====================================
                                    // SEND MESSAGE FUNCTION
                                    // =====================================
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

                                    // =====================================
                                    // GET GROUP LIST (FIX CHỐNG LAG)
                                    // =====================================
                                    "window.getZaloGroups = function() {" +
                                    "   try {" +
                                    "       let groups = [];" +
                                    "       /* Tối ưu: Chỉ quét các class chứa tên nhóm thay vì quét toàn bộ thẻ * */" +
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

                                    // =====================================
                                    // MAIN LOOP
                                    // =====================================
                                    "setInterval(() => {" +
                                    "   try {" +
                                    "       let app = document.querySelector('#app');" +
                                    "       if(app) {" +
                                    
                                    "           // =========================" +
                                    "           // LOGIN CHECK" +
                                    "           // =========================" +
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

                                    "           // =========================" +
                                    "           // GROUP UPDATE" +
                                    "           // =========================" +
                                    "           window.getZaloGroups();" +

                                    "           // =========================" +
                                    "           // MESSAGE DETECT" +
                                    "           // =========================" +
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

            // =====================================================
            // LOAD URL
            // =====================================================
            hiddenWebView.loadUrl(
                    "https://id.zalo.me/account?continue=https://chat.zalo.me"
            );

            // =====================================================
            // CLOSE BUTTON
            // =====================================================
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

            btnClose.setOnClickListener(v -> {
                CookieManager.getInstance().flush();
                dialog.dismiss();
            });

            // =====================================================
            // ADD VIEW
            // =====================================================
            layout.addView(hiddenWebView);
            layout.addView(btnClose);
            dialog.setContentView(layout);
            dialog.show();
        });
    }

    // =========================================================
    // EXECUTE JS
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
}
