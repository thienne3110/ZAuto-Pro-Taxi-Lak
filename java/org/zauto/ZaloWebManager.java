package org.zauto;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.view.ViewGroup;
import android.util.Log;

public class ZaloWebManager {

    public static WebView hiddenWebView;
    public static FrameLayout webLayout;
    private static final String TAG = "ZAutoWebManager";

    public static void sendReplyToSpecificMessage(final Activity activity, final String conversationId, final String msgId, final String text, final String groupName) {
        if (activity == null || hiddenWebView == null) return;
        activity.runOnUiThread(() -> {
            try {
                String js = "(function() { " +
                    "try {" +
                        "let chatNode = document.getElementById('" + conversationId + "') || document.querySelector('.conv-item[title=\"" + groupName + "\"]');" +
                        "if(chatNode && !chatNode.classList.contains('active')) chatNode.click();" +
                        "setTimeout(() => {" +
                            "let msgNode = document.querySelector('div[data-id=\"" + msgId + "\"]');" +
                            "if(!msgNode) return;" +
                            "let replyBtn = msgNode.querySelector('div[icon=\"reply\"], div[data-translate-inner=\"STR_REPLY_MESSAGE\"], .flx-al-c[title=\"Trả lời\"]');" + 
                            "if(replyBtn) replyBtn.click();" + 
                            "setTimeout(() => {" +
                                "let input = document.getElementById('richInput');" +
                                "if(input) { input.innerHTML = '"+ text +"'; input.dispatchEvent(new Event('input', {bubbles:true})); }" +
                                "setTimeout(() => {" +
                                    "let sendBtn = document.querySelector('.btn-send, [icon=\"icn-send\"]');" +
                                    "if(sendBtn) sendBtn.click();" +
                                "}, 200);" +
                            "}, 400);" +
                        "}, 500);" +
                    "} catch(e) { console.log(e); }" +
                "})();";
                hiddenWebView.evaluateJavascript(js, null);
            } catch (Exception e) { Log.e(TAG, "Reply Error", e); }
        });
    }

    public static class WebAppInterface {
        Context mContext;
        WebAppInterface(Context c) { mContext = c; }

        @JavascriptInterface
        public void onLoginSuccess(String name, String avatar) {
            try {
                Intent intent = new Intent("org.zauto.LOGIN_SUCCESS");
                // Đã gỡ bỏ setPackage để vượt rào Android 14 Broadcast
                intent.putExtra("zalo_name", name);
                intent.putExtra("zalo_avatar", avatar);
                mContext.sendBroadcast(intent);
            } catch (Exception e) { Log.e(TAG, "LoginSuccess Error", e); }
        }

        @JavascriptInterface
        public void onNewWebMsg(String group, String msg, String msgId, String conversationId) {
            try {
                Intent intent = new Intent("org.zauto.WEB_NEW_MSG");
                intent.putExtra("group", group);
                intent.putExtra("msg", msg);
                intent.putExtra("msg_id", msgId);
                intent.putExtra("conversation_id", conversationId);
                mContext.sendBroadcast(intent);
            } catch (Exception e) { Log.e(TAG, "NewWebMsg Error", e); }
        }

        @JavascriptInterface
        public void onGroupListReceived(String jsonGroups) {
            try {
                Intent intent = new Intent("org.zauto.GROUPS_DATA");
                intent.putExtra("groups_list", jsonGroups);
                mContext.sendBroadcast(intent);
            } catch (Exception e) { Log.e(TAG, "GroupList Error", e); }
        }
    }

    public static void initWebView(final Activity activity) {
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            try {
                if (hiddenWebView != null) return;

                webLayout = new FrameLayout(activity);
                hiddenWebView = new WebView(activity);

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

                settings.setUserAgentString("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36");

                CookieManager cookieManager = CookieManager.getInstance();
                cookieManager.setAcceptCookie(true);
                cookieManager.setAcceptThirdPartyCookies(hiddenWebView, true);

                hiddenWebView.addJavascriptInterface(new WebAppInterface(activity), "ZAutoBridge");
                hiddenWebView.setWebChromeClient(new WebChromeClient());
                hiddenWebView.setWebViewClient(new WebViewClient() {
                    @Override
                    public void onPageFinished(WebView view, String url) {
                        super.onPageFinished(view, url);
                        CookieManager.getInstance().flush();
                        
                        view.postDelayed(() -> {
                            try {
                                if (hiddenWebView == null) return;
                                
                                // Payload JS chống Crash tuyệt đối
                                String jsPayload = 
                                    "Object.defineProperty(navigator,'platform',{get:()=> 'Win32'});" +
                                    "window.getZaloGroups = function() {" +
                                    "   try {" +
                                    "       let groups = [];" +
                                    "       let elements = document.querySelectorAll('.conv-item-title__name, .group-name, span.truncate');" +
                                    "       elements.forEach(el => {" +
                                    "           let txt = el.innerText;" +
                                    "           if(txt && txt.length > 1 && !groups.includes(txt)) groups.push(txt);" +
                                    "       });" +
                                    "       if(groups.length > 0) ZAutoBridge.onGroupListReceived(JSON.stringify(groups.slice(0,100)));" +
                                    "   } catch(e) {}" +
                                    "};" +
                                    "setInterval(() => {" +
                                    "   try {" +
                                    "       let chatInput = document.getElementById('richInput') || document.querySelector('.chat-input');" +
                                    "       if(chatInput) {" +
                                    "           if(!window.zauto_logged) {" +
                                    "               window.zauto_logged = true;" +
                                    "               ZAutoBridge.onLoginSuccess('Đã kết nối', '');" +
                                    "           }" +
                                    "           window.getZaloGroups();" +
                                    "           let msgs = document.querySelectorAll('.msg-item');" +
                                    "           if(msgs.length > 0) {" +
                                    "               let lastMsgEl = msgs[msgs.length - 1];" +
                                    "               let msgText = lastMsgEl.innerText;" +
                                    "               let msgId = lastMsgEl.getAttribute('data-id') || '';" +
                                    "               let groupName = 'Nhóm Zalo';" +
                                    "               let header = document.querySelector('.header-title');" +
                                    "               if(header) groupName = header.innerText;" +
                                    "               let activeConv = document.querySelector('.conv-item.active');" + 
                                    "               let conversationId = activeConv ? activeConv.getAttribute('id') : '';" +
                                    "               if(window.last_zauto_id !== msgId) {" +
                                    "                   window.last_zauto_id = msgId;" +
                                    "                   if(!msgText.includes('Ok nhận')) {" +
                                    "                       ZAutoBridge.onNewWebMsg(groupName, msgText, msgId, conversationId);" +
                                    "                   }" +
                                    "               }" +
                                    "           }" +
                                    "       }" +
                                    "   } catch(e) {}" +
                                    "}, 1500);"; 
                                view.evaluateJavascript(jsPayload, null);
                            } catch (Exception e) {}
                        }, 4000);
                    }
                });

                hiddenWebView.loadUrl("https://id.zalo.me/account?continue=https://chat.zalo.me");
                webLayout.addView(hiddenWebView, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
                webLayout.setVisibility(android.view.View.GONE);
                activity.addContentView(webLayout, new FrameLayout.LayoutParams(0, 0));
                
            } catch (Exception e) { Log.e(TAG, "Init Error", e); }
        });
    }

    public static void updateWebViewBounds(final Activity activity, final int x, final int y, final int width, final int height, final boolean visible) {
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            try {
                if (webLayout != null) {
                    if (!visible) {
                        webLayout.setVisibility(android.view.View.GONE);
                    } else {
                        webLayout.setVisibility(android.view.View.VISIBLE);
                        FrameLayout.LayoutParams params = (FrameLayout.LayoutParams) webLayout.getLayoutParams();
                        params.leftMargin = x; params.topMargin = y; params.width = width; params.height = height;
                        webLayout.setLayoutParams(params);
                    }
                }
            } catch (Exception e) {}
        });
    }

    public static void reloadWeb(final Activity activity) {
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            try { if (hiddenWebView != null) hiddenWebView.reload(); } catch (Exception e) {}
        });
    }

    public static void onResume(final Activity activity) {
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            try {
                if (hiddenWebView != null) {
                    hiddenWebView.onResume();
                    hiddenWebView.resumeTimers();
                    hiddenWebView.setKeepScreenOn(true);
                }
            } catch (Exception e) {}
        });
    }
}
