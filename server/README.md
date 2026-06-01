# ZAuto Taxi Core (Zalo backend)

Standalone Node.js service that logs into Zalo with a QR code (via
[`zalo-api-final`](https://www.npmjs.com/package/zalo-api-final)), listens to
group messages, and auto-accepts taxi rides ("đón / trả / giá"). It bridges
events to the mobile app over Socket.IO and exposes the login QR over HTTP.

This is the "Core Logic" backend referenced by the app; it lives alongside the
Android client in this repo but runs as its own Node process.

## Requirements

- Node.js >= 18
- A Zalo account to scan the QR code

## Setup

```bash
cd server
npm install
cp .env.example .env   # optional, tweak keywords / port
npm start
```

Then open <http://localhost:3000> and scan the QR code with Zalo. Once logged
in, the service starts listening for group messages.

## Configuration (env vars)

| Variable             | Default        | Description                                              |
| -------------------- | -------------- | -------------------------------------------------------- |
| `PORT`               | `3000`         | HTTP / Socket.IO port                                    |
| `AUTO_MODE_ENABLED`  | `true`         | Enable keyword auto-reply                                |
| `AUTO_KEYWORDS`      | `đón*trả*giá`  | Keywords that must **all** appear (`*` or `,` separated) |
| `AUTO_REPLY_MESSAGE` | `ok nhận`      | Text sent on accept                                      |
| `REPLY_DELAY_MIN_MS` | `1500`         | Min random delay before replying                         |
| `REPLY_DELAY_MAX_MS` | `3000`         | Max random delay before replying                         |
| `QR_PATH`            | `qr.png`       | Where the QR png is written                              |

## HTTP API

- `GET /api/get-qr` → `{ status: "waiting" | "pending" | "success", qrBase64? }`
- `GET /health` → `{ ok: true, status }`

## Socket.IO

Server → app:

- `zalo_status` `{ status }`
- `qr` `{ qrBase64 }`
- `new_zalo_message` `{ id, groupId, groupName, content }`
- `nhan_cuoc_thanh_cong` `{ messageId, auto? }`
- `nhan_cuoc_that_bai` `{ messageId, error }`

App → server:

- `nhan_cuoc` `{ groupId, messageId }` — manually accept a ride (quotes the
  original message if it is still cached).

## Scripts

```bash
npm start    # run the server
npm run dev  # run with --watch
npm run lint # eslint
npm test     # node:test (keyword matching)
```

## Notes

`zalo-api-final` is an unofficial library; use it responsibly and at your own
risk per its license and Zalo's terms of service.
