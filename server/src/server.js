import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import cors from "cors";
import express from "express";
import { Server } from "socket.io";

import { config } from "./config.js";
import { ZaloClient } from "./zaloClient.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, "..", "public")));

const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*" } });

const zaloClient = new ZaloClient();

zaloClient.on("message", (payload) => io.emit("new_zalo_message", payload));
zaloClient.on("qr", (payload) => io.emit("qr", payload));
zaloClient.on("status", (payload) => io.emit("zalo_status", payload));
zaloClient.on("auto_reply", ({ messageId }) =>
  io.emit("nhan_cuoc_thanh_cong", { messageId, auto: true }),
);

io.on("connection", (socket) => {
  console.log("📱 App kết nối Socket:", socket.id);
  socket.emit("zalo_status", { status: zaloClient.status });

  // Gửi ngay lịch sử tin nhắn gần nhất cho app vừa kết nối
  const recent = zaloClient.getRecentMessages();
  if (recent.length > 0) {
    socket.emit("message_history", recent);
  }

  // Nhận cuốc thủ công từ app
  socket.on("nhan_cuoc", async (data = {}) => {
    try {
      const quote = zaloClient.getMessage(data.messageId);
      await zaloClient.reply(data.groupId, config.replyMessage, quote);
      io.emit("nhan_cuoc_thanh_cong", { messageId: data.messageId });
    } catch (error) {
      console.error("❌ Lỗi nhận cuốc thủ công:", error);
      socket.emit("nhan_cuoc_that_bai", {
        messageId: data.messageId,
        error: String(error?.message || error),
      });
    }
  });

  // App yêu cầu đăng xuất / reset QR
  socket.on("logout", async () => {
    try {
      await zaloClient.logout();
      io.emit("zalo_status", { status: "waiting" });
    } catch (err) {
      console.error("❌ Lỗi logout:", err);
    }
  });
});

// ─── HTTP API ─────────────────────────────────────────────────────────────────

app.get("/api/get-qr", (_req, res) => {
  if (zaloClient.status === "success") return res.json({ status: "success" });
  if (zaloClient.qrBase64) {
    return res.json({ status: "pending", qrBase64: zaloClient.qrBase64 });
  }
  res.json({ status: zaloClient.status || "waiting" });
});

app.get("/health", (_req, res) => {
  res.json({ ok: true, status: zaloClient.status });
});

// Lấy config hiện tại (app dùng để hiển thị settings)
app.get("/api/config", (_req, res) => {
  res.json({
    autoModeEnabled: config.autoModeEnabled,
    autoKeywords: config.autoKeywords,
    replyMessage: config.replyMessage,
    replyDelayMinMs: config.replyDelayMinMs,
    replyDelayMaxMs: config.replyDelayMaxMs,
  });
});

// Cập nhật config từ app (không cần restart)
app.post("/api/config", (req, res) => {
  const { autoModeEnabled, autoKeywords, replyMessage, replyDelayMinMs, replyDelayMaxMs } = req.body;
  if (autoModeEnabled !== undefined) config.autoModeEnabled = Boolean(autoModeEnabled);
  if (autoKeywords !== undefined) config.autoKeywords = String(autoKeywords);
  if (replyMessage !== undefined) config.replyMessage = String(replyMessage);
  if (replyDelayMinMs !== undefined) config.replyDelayMinMs = Number(replyDelayMinMs);
  if (replyDelayMaxMs !== undefined) config.replyDelayMaxMs = Number(replyDelayMaxMs);
  res.json({ ok: true });
});

// Lấy lịch sử tin nhắn gần nhất (HTTP fallback nếu Socket mất)
app.get("/api/messages", (_req, res) => {
  res.json({ messages: zaloClient.getRecentMessages() });
});

// Gửi reply thủ công qua HTTP (thay thế cho socket nếu cần)
app.post("/api/nhan-cuoc", async (req, res) => {
  const { groupId, messageId } = req.body;
  try {
    const quote = zaloClient.getMessage(messageId);
    await zaloClient.reply(groupId, config.replyMessage, quote);
    io.emit("nhan_cuoc_thanh_cong", { messageId, auto: false });
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ ok: false, error: String(err?.message || err) });
  }
});

server.listen(config.port, () => {
  console.log(`🚀 Core Logic chạy tại port ${config.port}`);
  zaloClient.start().catch((error) => {
    console.error("❌ Lỗi đăng nhập Zalo:", error);
  });
});

export { app, server, io, zaloClient };
