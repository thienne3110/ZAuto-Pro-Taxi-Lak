import { EventEmitter } from "node:events";
import QRCode from "qrcode";
import { Zalo, ThreadType, LoginQRCallbackEventType } from "zalo-api-final";

import { config } from "./config.js";
import { matchesKeywords } from "./keywords.js";

const randomDelay = (min, max) =>
  new Promise((resolve) =>
    setTimeout(resolve, Math.floor(Math.random() * (max - min + 1) + min)),
  );

/**
 * Extract plain text from a zalo message payload. `content` is a string for
 * text messages and an object for attachments/links.
 */
const extractText = (data) => {
  if (typeof data.content === "string") return data.content;
  if (data.content && typeof data.content.title === "string") return data.content.title;
  return "";
};

/**
 * Wraps zalo-api-final and exposes a small, app-friendly surface:
 *   - emits "status"  -> { status: "waiting" | "pending" | "scanned" | "success" }
 *   - emits "qr"      -> { qrBase64 }
 *   - emits "message" -> { id, groupId, groupName, content }
 *   - emits "auto_reply" / "reply_sent" -> { messageId }
 */
export class ZaloClient extends EventEmitter {
  constructor() {
    super();
    this.zalo = new Zalo();
    this.api = null;
    this.status = "waiting"; // waiting | pending | scanned | success
    this.qrBase64 = null;
    // Cache of recent group messages (msgId -> message.data) so manual accepts
    // coming from the app (which only know the messageId) can quote correctly.
    this.recentMessages = new Map();
    this.maxRecentMessages = 500;
  }

  #cacheMessage(data) {
    this.recentMessages.set(data.msgId, data);
    if (this.recentMessages.size > this.maxRecentMessages) {
      const oldestKey = this.recentMessages.keys().next().value;
      this.recentMessages.delete(oldestKey);
    }
  }

  /** Look up a cached message payload by id (for quoting on manual accept). */
  getMessage(msgId) {
    return this.recentMessages.get(msgId);
  }

  #setStatus(status) {
    this.status = status;
    this.emit("status", { status });
  }

  async #handleQrEvent(event) {
    switch (event.type) {
      case LoginQRCallbackEventType.QRCodeGenerated: {
        // Prefer the QR image from the API; fall back to rendering the code.
        let qrBase64 = null;
        if (event.data?.image) {
          qrBase64 = `data:image/png;base64,${event.data.image}`;
        } else if (event.data?.code) {
          qrBase64 = await QRCode.toDataURL(event.data.code);
        }
        this.qrBase64 = qrBase64;
        this.#setStatus("pending");
        this.emit("qr", { qrBase64 });
        break;
      }
      case LoginQRCallbackEventType.QRCodeScanned:
        this.#setStatus("scanned");
        break;
      case LoginQRCallbackEventType.QRCodeExpired:
        this.qrBase64 = null;
        this.#setStatus("waiting");
        break;
      case LoginQRCallbackEventType.QRCodeDeclined:
        this.qrBase64 = null;
        this.#setStatus("waiting");
        break;
      default:
        break;
    }
  }

  #attachListener() {
    this.api.listener.on("message", async (message) => {
      // Ignore messages sent by the logged-in account and non-group messages.
      if (message.isSelf) return;
      if (message.type !== ThreadType.Group) return;

      const data = message.data;
      this.#cacheMessage(data);
      const content = extractText(data);
      const payload = {
        id: data.msgId,
        groupId: message.threadId,
        groupName: data.dName || "Nhóm Zalo",
        content,
      };

      this.emit("message", payload);

      if (config.autoModeEnabled && matchesKeywords(content, config.autoKeywords)) {
        await randomDelay(config.replyDelayMinMs, config.replyDelayMaxMs);
        try {
          await this.reply(message.threadId, config.replyMessage, data);
          this.emit("auto_reply", { messageId: data.msgId });
        } catch (error) {
          console.error("❌ Lỗi Auto-reply:", error);
        }
      }
    });

    this.api.listener.on("error", (error) => {
      console.error("❌ Lỗi listener:", error);
    });

    this.api.listener.start({ retryOnClose: true });
  }

  /**
   * Send a text reply to a group, optionally quoting the original message.
   * @param {string} threadId
   * @param {string} message
   * @param {object} [quoteData] original message.data to quote
   */
  async reply(threadId, message, quoteData) {
    if (!this.api) throw new Error("Zalo chưa đăng nhập");
    const content = quoteData ? { msg: message, quote: quoteData } : { msg: message };
    return this.api.sendMessage(content, threadId, ThreadType.Group);
  }

  /** Start the QR login flow. Resolves once login succeeds. */
  async start() {
    this.api = await this.zalo.loginQR(
      { qrPath: config.qrPath },
      (event) => this.#handleQrEvent(event),
    );

    console.log("✅ Đăng nhập Zalo thành công!");
    this.qrBase64 = "SUCCESS";
    this.#setStatus("success");
    this.#attachListener();
    return this.api;
  }
}
