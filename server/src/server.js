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

// Bridge Zalo events to connected apps over Socket.IO.
zaloClient.on("message", (payload) => io.emit("new_zalo_message", payload));
zaloClient.on("qr", (payload) => io.emit("qr", payload));
zaloClient.on("status", (payload) => io.emit("zalo_status", payload));
zaloClient.on("auto_reply", ({ messageId }) =>
  io.emit("nhan_cuoc_thanh_cong", { messageId, auto: true }),
);

io.on("connection", (socket) => {
  console.log("📱 App kết nối Socket:", socket.id);
  socket.emit("zalo_status", { status: zaloClient.status });

  // Manual accept triggered from the app.
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
});

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

server.listen(config.port, () => {
  console.log(`🚀 Core Logic chạy tại port ${config.port}`);
  // Kick off Zalo login in the background so the QR endpoint is reachable
  // immediately while waiting for the user to scan.
  zaloClient.start().catch((error) => {
    console.error("❌ Lỗi đăng nhập Zalo:", error);
  });
});

export { app, server, io, zaloClient };
