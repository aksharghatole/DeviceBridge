# DeviceBridge v1.0

A browser-based cross-device sharing prototype. Pair devices using an invite link, QR code or a random 10-character room code. No account, database or application file storage. Node.js serves the interface and exchanges only room membership and WebRTC signaling. WebRTC carries text and file content over an encrypted data channel. Rooms support six devices.

## Run on your computer

1. Install Node.js 18 or later (https://nodejs.org/).
2. Extract this archive, open a terminal in the `devicebridge` folder, and run `npm start`. There are no packages to install.
3. Open http://localhost:3000 on the computer and create a room.
4. To connect a phone on the same Wi-Fi, find your computer's local IPv4 address (`ipconfig` on Windows, `ip addr` on Linux). Open `http://YOUR_LOCAL_IP:3000` on both devices, then create a room using that address so the QR invite is reachable from the phone. Allow inbound TCP 3000 on your private network if your firewall prompts you. Do not expose the local server directly to the public internet.
5. Join on the second device using the QR code, invite link or room code. Wait until it is shown as connected. Select a file or enter text and send it. The recipient must accept each file and then click Download.

Some mobile browsers restrict WebRTC or clipboard access on insecure HTTP. If local HTTP does not work, deploy over HTTPS. Both browser tabs must remain open. Do not use the localhost invite on a second physical device.

## Deploy online (Render)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Faksharghatole%2FDeviceBridge)

1. Open the deployment link and sign in to Render. Connect your own GitHub account if prompted.
2. Review the Blueprint (`render.yaml`), choose the **Free** web service, and approve deployment. No database is needed.
3. Open the HTTPS URL shown in your Render dashboard on both devices. Create a room on one and join on the other.
4. Test text, then a small file, and verify that the recipient receives the exact file. The health endpoint is `/health`.

The free service may sleep after 15 minutes without inbound traffic. It can take time to wake, and rooms are lost on restart or deployment. This is hobby hosting, not an availability guarantee. Auto-deploy is configured for the main branch. Never add long-lived TURN secrets to this public repository.

## Public HTTPS deployment

This is a single Node HTTP service, not a static site. Upload the contents to a repository and deploy it to a Node-compatible host using `npm start`. The server listens on `PORT` (default 3000). Configure TLS at the hosting provider or reverse proxy. SSE responses must not be buffered and the host must permit long-lived HTTP connections. Run one server instance because rooms are in memory. GitHub Pages by itself cannot run the signaling server. A Dockerfile is included.

Default ICE configuration uses Google's public STUN endpoint. Some networks require a TURN relay; set `ICE_SERVERS` to a JSON array of RTCIceServer objects (e.g. `[ {"urls":"stun:stun.l.google.com:19302"}, {"urls":"turn:YOUR_HOST:3478","username":"...","credential":"..."} ]`). Use short-lived TURN credentials in production; configured credentials are visible to clients. TURN can cost money and relays encrypted traffic. No hosted URL or TURN service is included.

## Features and boundaries

- Up to six devices, QR/invite/code pairing, recipient selection, device status.
- Multiple files queued sequentially; consent, decline, progress, cancellation and receipt acknowledgment. Maximum 256 MiB per file, and one active incoming file per browser. Receiving uses browser memory; large files may fail on low-memory devices. Clear completed activity to free retained blobs.
- Text/link sharing and explicit copy-to-clipboard (no background clipboard reading).
- Ephemeral activity; clearing or leaving discards unsaved files. No automatic transfer resume, offline messaging, device authentication beyond possession of the invitation, or background transfers. Rooms disappear on restart or once empty; disconnected members expire after two minutes.
- Use only with trusted peers and a trusted signaling host. WebRTC encrypts transport, but the current prototype does not independently verify peer identity or protect against a malicious signaling service. Do not publish invitations. For production, add independently verified pairing, session hardening, anti-abuse controls, monitoring, and browser/device testing. Avoid logging query strings (event-stream session tokens appear in URLs). The service exposes no file upload endpoint.

## Verification

Run `npm test` for HTTP room lifecycle, QR generation and signaling authorization. JavaScript syntax checked with `node --check`. The included optional Playwright smoke test covers browser pairing, text, file download bytes, decline and disconnect. It could not run in the build environment because local Chromium navigation was blocked by administrator policy; actual device transfers are not yet verified. To run it yourself, install Python Playwright, run `python -m playwright install chromium`, then `python browser-smoke.py`.

## Third-party notice

Vendored QRCode JavaScript by Kazuhiko Arase (MIT, copyright 2009), adapted by qrcode-terminal. See vendor/LICENSE and source headers. All other app files are original for this project.
