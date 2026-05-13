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
    public static FrameLayout webLayout; // Container để điều chỉnh toạ độ
    private static final String TAG = "ZAutoWebManager";

    // =========================================================
    // HÀM CHỐT CUỐC: BẮT ĐÚNG BONG BÓNG TIN NHẮN (PRODUCTION GRADE)
    // =========================================================
    public static void sendReplyToSpecificMessage(final Activity activity, final String conversationId, final String msgId, final String text, final String groupName) {
        if (activity == null || hiddenWebView == null) return;
        
        activity.runOnUiThread(() -> {
            try {
                if (hiddenWebView == null) return; 
                
                String js = "(function() { " +
                    "try {" +
                        // 1. Focus đúng nhóm/đoạn chat
                        "let chatNode = document.getElementById('" + conversationId + "') || document.querySelector('.conv-item[title=\"" + groupName + "\"]');" +
                        "if(chatNode && !chatNode.classList.contains('active')) chatNode.click();" +
                        
                        "setTimeout(() => {" +
                            // 2. Tìm bong bóng tin nhắn
                            "let msgNode = document.querySelector('div[data-id=\"" + msgId + "\"]');" +
                            "if(!msgNode) return;" +
                            
                            // 3. Hover và click nút Reply (icon reply Zalo Web)
                            "let replyBtn = msgNode.querySelector('div[icon=\"reply\"], div[data-translate-inner=\"STR_REPLY_MESSAGE\"], .flx-al-c[title=\"Trả lời\"]');" + 
                            "if(replyBtn) replyBtn.click();" + 
                            
                            "setTimeout(() => {" +
                                // 4. Nhập text và Enter
                                "let input = document.getElementById('richInput');" +
                                "if(input) { input.innerHTML = '"+ text +"'; input.dispatchEvent(new Event('input', {bubbles:true})); }" +
                                
                                "setTimeout(() => {" +
                                    "let sendBtn = document.querySelector('.btn-send, [icon=\"icn-send\"]');" +
                                    "if(sendBtn) sendBtn.click();" +
                                "}, 200);" + // Đợi input nhận diện text rồi mới click gửi
                                
                            "}, 400);" +
                        "}, 500);" +
                    "} catch(e) {}" +
                "})();";
                
                hiddenWebView.evaluateJavascript(js, null);
            } catch (Exception e) {
                Log.e(TAG, "Lỗi khi gửi reply JS", e);
            }
        });
    }

    // =========================================================
    // CẦU NỐI JAVASCRIPT -> PYTHON (ĐÃ XÓA CHỮ .taxi)
    // =========================================================
    public static class WebAppInterface {
        Context mContext;
        WebAppInterface(Context c) { mContext = c; }

        @JavascriptInterface
        public void onLoginSuccess(String name, String avatar) {
            try {
                Intent intent = new Intent("org.zauto.LOGIN_SUCCESS");
                intent.setPackage(mContext.getPackageName());
                intent.putExtra("zalo_name", name);
                intent.putExtra("zalo_avatar", avatar);
                mContext.sendBroadcast(intent);
            } catch (Exception e) {
                Log.e(TAG, "Broadcast LoginSuccess Error", e);
            }
        }

        @JavascriptInterface
        public void onNewWebMsg(String group, String msg, String msgId, String conversationId) {
            try {
                Intent intent = new Intent("org.zauto.WEB_NEW_MSG");
                intent.setPackage(mContext.getPackageName());
                intent.putExtra("group", group);
                intent.putExtra("msg", msg);
                intent.putExtra("msg_id", msgId);
                intent.putExtra("conversation_id", conversationId);
                mContext.sendBroadcast(intent);
            } catch (Exception e) {
                Log.e(TAG, "Broadcast NewWebMsg Error", e);
            }
        }

        @JavascriptInterface
        public void onGroupListReceived(String jsonGroups) {
            try {
                Intent intent = new Intent("org.zauto.GROUPS_DATA");
                intent.setPackage(mContext.getPackageName());
                intent.putExtra("groups_list", jsonGroups);
                mContext.sendBroadcast(intent);
            } catch (Exception e) {
                Log.e(TAG, "Broadcast GroupList Error", e);
            }
        }
    }

    // =========================================================
    // KHỞI TẠO WEBVIEW NHÚNG NATIVE
    // =========================================================
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
                // BẮT BUỘC ĐỂ CHỐNG NGỦ ĐÔNG MEDIA VÀ JS
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
                        
                        // Kích hoạt ghi đĩa Cookie ngay để chống out Zalo khi tắt app nền
                        CookieManager.getInstance().flush();
                        
                        view.postDelayed(() -> {
                            try {
                                if (hiddenWebView == null) return;
                                
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
                                    "                   if(!groups.includes(txt)) groups.push(txt);" +
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
                                    "       let app = document.querySelector('#app');" +
                                    "       if(app) {" +
                                    "           if(!window.zauto_logged) {" +
                                    "               let name = 'Đã kết nối'; let avatar = '';" +
                                    "               try {" +
                                    "                   let imgs = document.querySelectorAll('img');" +
                                    "                   imgs.forEach(i => { if(i.src && i.src.includes('avatar')) avatar = i.src; });" +
                                    "                   let titleEl = document.querySelector('[data-translate-inner]');" +
                                    "                   if(titleEl) name = titleEl.innerText;" +
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
                                    "                   let msgId = lastMsgEl.getAttribute('data-id') || '';" +
                                    "                   let groupName = 'Nhóm Zalo';" +
                                    "                   let header = document.querySelector('.header-title');" +
                                    "                   if(header) groupName = header.innerText;" +
                                    "                   let activeConv = document.querySelector('.conv-item.active');" + 
                                    "                   let conversationId = activeConv ? activeConv.getAttribute('id') : '';" +
                                    "                   if(window.last_zauto_id !== msgId) {" +
                                    "                       window.last_zauto_id = msgId;" +
                                    "                       if(!msgText.includes('Ok nhận')) {" +
                                    "                           ZAutoBridge.onNewWebMsg(groupName, msgText, msgId, conversationId);" +
                                    "                       }" +
                                    "                   }" +
                                    "               }" +
                                    "           } catch(e) {}" +
                                    "       }" +
                                    "   } catch(e) {}" +
                                    "}, 1500);"; 

                                view.evaluateJavascript(jsPayload, null);
                            } catch (Exception e) {
                                Log.e(TAG, "Lỗi khi inject payload JS", e);
                            }
                        }, 5000);
                    }
                });

                hiddenWebView.loadUrl("https://id.zalo.me/account?continue=https://chat.zalo.me");

                webLayout.addView(hiddenWebView, new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                ));

                webLayout.setVisibility(android.view.View.GONE);
                activity.addContentView(webLayout, new FrameLayout.LayoutParams(0, 0));
                
            } catch (Exception e) {
                Log.e(TAG, "Lỗi khi khởi tạo WebView", e);
            }
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
                        params.leftMargin = x;
                        params.topMargin = y;
                        params.width = width;
                        params.height = height;
                        webLayout.setLayoutParams(params);
                    }
                }
            } catch (Exception e) {
                Log.e(TAG, "Lỗi khi cập nhật tọa độ WebView", e);
            }
        });
    }

    public static void sendReply(final Activity activity, final String groupName, final String replyText) {
        String js = "window.sendHiddenMessage('" + replyText + "');";
        executeJS(activity, js);
    }

    public static void reloadWeb(final Activity activity) {
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            try {
                if (hiddenWebView != null) hiddenWebView.reload();
            } catch (Exception e) {
                Log.e(TAG, "Lỗi khi reload WebView", e);
            }
        });
    }

    public static void executeJS(final Activity activity, final String jsCode) {
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            try {
                if (hiddenWebView != null) {
                    hiddenWebView.evaluateJavascript(jsCode, null);
                }
            } catch (Exception e) {
                Log.e(TAG, "Lỗi khi execute trực tiếp JS", e);
            }
        });
    }

    // =========================================================
    // HÀM ÉP WEBVIEW LUÔN THỨC VÀ CHẠY JAVASCRIPT NGẦM LIÊN TỤC
    // =========================================================
    public static void onResume(final Activity activity) {
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            try {
                if (hiddenWebView != null) {
                    // 1. Kích hoạt lại toàn bộ luồng xử lý của WebView
                    hiddenWebView.onResume();
                    // 2. Ép các hàm setTimeout và setInterval trong JS chạy lại
                    hiddenWebView.resumeTimers();
                    // 3. Đảm bảo WebView không bị hệ thống cho đi ngủ
                    hiddenWebView.setKeepScreenOn(true);
                    // 4. Gửi một lệnh ping nhỏ để xốc lại luồng JS
                    hiddenWebView.evaluateJavascript("console.log('System Ping: Wake Up Zalo');", null);
                }
            } catch (Exception e) {
                Log.e(TAG, "Lỗi khi đánh thức WebView", e);
            }
        });
    }
}
