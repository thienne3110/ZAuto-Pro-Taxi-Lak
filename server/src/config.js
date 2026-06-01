const toBool = (value, fallback) => {
  if (value === undefined) return fallback;
  return ["1", "true", "yes", "on"].includes(String(value).trim().toLowerCase());
};

export const config = {
  port: Number(process.env.PORT) || 3000,

  // Auto-reply behaviour
  autoModeEnabled: toBool(process.env.AUTO_MODE_ENABLED, true),

  // Keywords that must ALL appear (case-insensitive) in a group message for the
  // bot to auto-accept the ride. Separate with "*" (kept for backward
  // compatibility) or ",". Example: "đón*trả*giá".
  autoKeywords: process.env.AUTO_KEYWORDS || "đón*trả*giá",

  // Text replied with when a message matches (manual accept and auto accept).
  replyMessage: process.env.AUTO_REPLY_MESSAGE || "ok nhận",

  // Random delay window (ms) before sending a reply, to look less robotic.
  replyDelayMinMs: Number(process.env.REPLY_DELAY_MIN_MS) || 1500,
  replyDelayMaxMs: Number(process.env.REPLY_DELAY_MAX_MS) || 3000,

  // Where zalo-api-final writes the QR png. We also expose it as base64 over HTTP.
  qrPath: process.env.QR_PATH || "qr.png",
};
