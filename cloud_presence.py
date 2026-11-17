"""
24/7 Discord Streaming Presence Cloud Host.
Self-contained, headless WebSocket Gateway client with integrated HTTP keep-alive server.
Deployable on Render, Railway, Koyeb, Fly.io, VPS, or local/Android Termux.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("CloudPresence")

# Configuration via Environment Variables or fallback config
TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()
GAME_NAME = os.environ.get("STREAM_GAME", "Minecraft").strip()
STREAM_TITLE = os.environ.get("STREAM_TITLE", "24/7 Live Stream").strip()
STREAM_URL = os.environ.get("STREAM_URL", "https://www.twitch.tv/discord").strip()
PORT = int(os.environ.get("PORT", "8080"))

GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"


class KeepAliveHandler(BaseHTTPRequestHandler):
    """Responds to cloud container health checks (keeps free tiers awake)."""

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = (
            "<!DOCTYPE html><html><head><title>Discord 24/7 Presence</title></head>"
            "<body style='font-family:sans-serif;background:#0b0d12;color:#fff;text-align:center;padding:50px;'>"
            "<h2 style='color:#a855f7;'>🟣 Discord 24/7 Streaming Presence: ACTIVE</h2>"
            f"<p>Game: <b>{GAME_NAME}</b> | Title: <b>{STREAM_TITLE}</b></p>"
            "<p style='color:#4ade80;'>✔ Gateway WebSocket is connected and broadcasting live.</p>"
            "</body></html>"
        )
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format: str, *args) -> None:
        pass  # Suppress HTTP access noise in stdout


def start_http_health_check() -> None:
    try:
        server = HTTPServer(("0.0.0.0", PORT), KeepAliveHandler)
        logger.info(f"Health-check HTTP server listening on port {PORT}")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Could not bind HTTP server on port {PORT}: {e}")


class CloudPresenceEngine:
    """Maintains an unbroken 24/7 connection to Discord Gateway."""

    def __init__(self, token: str) -> None:
        self.token = token
        self._running = True
        self._seq: Optional[int] = None
        self._session_id: Optional[str] = None
        self._start_time = int(time.time() * 1000)

    def _build_activity(self) -> dict:
        url = STREAM_URL
        if not (url.startswith("https://www.twitch.tv/") or url.startswith("https://twitch.tv/") or "youtube.com/watch" in url):
            url = "https://www.twitch.tv/discord"

        return {
            "name": GAME_NAME,
            "type": 1,  # ActivityType.STREAMING
            "url": url,
            "details": STREAM_TITLE,
            "state": "Live on Twitch",
            "timestamps": {"start": self._start_time},
            "assets": {
                "large_image": "twitch:streamer",
                "large_text": STREAM_TITLE,
                "small_image": "live",
                "small_text": "Live",
            },
        }

    async def run(self) -> None:
        reconnect_delay = 3.0
        while self._running:
            logger.info("Connecting to Discord Gateway...")
            try:
                async with websockets.connect(
                    GATEWAY_URL,
                    ping_interval=None,
                    max_size=50 * 1024 * 1024,
                    user_agent_header=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) discord/1.0.9253 Chrome/148.0.7778.280 "
                        "Electron/42.7.1 Safari/537.36"
                    ),
                ) as ws:
                    reconnect_delay = 3.0
                    # Step 1: Wait for HELLO
                    hello_msg = await ws.recv()
                    hello_data = json.loads(hello_msg)
                    if hello_data.get("op") != 10:
                        logger.warning(f"Unexpected initial Opcode: {hello_data.get('op')}")
                        continue

                    interval = hello_data["d"]["heartbeat_interval"] / 1000.0
                    logger.info(f"Gateway connected. Heartbeat interval: {interval:.1f}s")

                    # Step 2: IDENTIFY
                    identify_payload = {
                        "op": 2,
                        "d": {
                            "token": self.token,
                            "capabilities": 30717,
                            "properties": {
                                "os": "Linux",
                                "browser": "Discord Client",
                                "device": "CloudServer",
                                "system_locale": "en-US",
                                "browser_user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                                "client_build_number": 594031,
                            },
                            "presence": {
                                "since": 0,
                                "activities": [self._build_activity()],
                                "status": "online",
                                "afk": False,
                            },
                            "compress": False,
                        },
                    }
                    await ws.send(json.dumps(identify_payload))

                    # Start Heartbeat loop
                    hb_task = asyncio.create_task(self._heartbeat(ws, interval))

                    try:
                        async for raw_message in ws:
                            payload = json.loads(raw_message)
                            op = payload.get("op")
                            self._seq = payload.get("s", self._seq)

                            if op == 0:  # DISPATCH
                                t = payload.get("t")
                                if t == "READY":
                                    user = payload["d"].get("user", {})
                                    username = user.get("username", "User")
                                    self._session_id = payload["d"].get("session_id")
                                    logger.info(f"✨ Authenticated as {username}! 24/7 Streaming presence is LIVE.")
                            elif op == 1:  # Discord requested Heartbeat
                                await ws.send(json.dumps({"op": 1, "d": self._seq}))
                            elif op == 7:  # Reconnect requested
                                logger.info("Discord requested session reconnect.")
                                break
                            elif op == 9:  # Invalid session
                                logger.warning("Session invalidated. Re-identifying in 3s...")
                                await asyncio.sleep(3.0)
                                break
                            elif op == 11:  # Heartbeat ACK
                                pass
                    finally:
                        hb_task.cancel()

            except Exception as exc:
                logger.warning(f"Connection dropped ({exc}). Reconnecting in {reconnect_delay:.0f}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(30.0, reconnect_delay * 1.5)

    async def _heartbeat(self, ws: websockets.WebSocketClientProtocol, interval: float) -> None:
        try:
            while self._running:
                await asyncio.sleep(interval)
                if ws and ws.open:
                    await ws.send(json.dumps({"op": 1, "d": self._seq}))
        except asyncio.CancelledError:
            pass


def main() -> None:
    token = TOKEN
    if not token:
        # Check local stream_state.json if available
        state_file = os.path.join(os.path.dirname(__file__), "..", "stream_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    token = data.get("token", "")
            except Exception:
                pass

    if not token:
        logger.error("FATAL: No DISCORD_TOKEN provided! Set DISCORD_TOKEN env variable.")
        sys.exit(1)

    # Start background health-check HTTP server for cloud hosts
    threading.Thread(target=start_http_health_check, daemon=True).start()

    # Start Gateway Presence loop
    engine = CloudPresenceEngine(token)
    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        logger.info("Process stopped by user.")


if __name__ == "__main__":
    main()
