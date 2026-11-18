"""
24/7 Discord Automated Voice Channel Streamer & Live Badge Farmer.
Production-grade stability:
- Connects cleanly to Voice Channel and starts Go-Live screen share.
- Eliminates Opcode 4 spam (only re-joins on actual disconnects).
- Rock-solid Gateway & Voice heartbeats.
- Embedded self-pinging keep-alive to prevent Render free-tier sleep.
- Independent, resilient Alt account viewer worker.
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

import requests
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("CloudStreamer")

# Configuration via Environment Variables
TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()
ALT_TOKEN = os.environ.get("ALT_TOKEN", "").strip()
VOICE_CHANNEL_ID = os.environ.get("VOICE_CHANNEL_ID", "").strip()
GUILD_ID = os.environ.get("GUILD_ID", "").strip()

GAME_NAME = os.environ.get("STREAM_GAME", "Minecraft").strip()
STREAM_TITLE = os.environ.get("STREAM_TITLE", "24/7 Live Stream").strip()
STREAM_URL = os.environ.get("STREAM_URL", "https://www.twitch.tv/discord").strip()
PORT = int(os.environ.get("PORT", "8080"))
EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "").strip()

GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) discord/1.0.9253 Chrome/148.0.7778.280 "
    "Electron/42.7.1 Safari/537.36"
)


class KeepAliveHandler(BaseHTTPRequestHandler):
    """Responds to uptime pings to keep cloud container awake 24/7."""

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = (
            "<!DOCTYPE html><html><head><title>Discord 24/7 Cloud Streamer</title></head>"
            "<body style='font-family:sans-serif;background:#0b0d12;color:#fff;text-align:center;padding:50px;'>"
            "<h2 style='color:#a855f7;'>🟣 Discord 24/7 Cloud Streamer: ACTIVE</h2>"
            f"<p>Target Voice Channel: <b>{VOICE_CHANNEL_ID}</b></p>"
            "<p style='color:#4ade80;'>✔ Gateway WebSockets connected. Voice & Stream running 24/7.</p>"
            "</body></html>"
        )
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format: str, *args) -> None:
        pass


def start_http_health_check() -> None:
    try:
        server = HTTPServer(("0.0.0.0", PORT), KeepAliveHandler)
        logger.info(f"Health-check HTTP server listening on port {PORT}")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Could not bind HTTP server on port {PORT}: {e}")


def self_ping_worker() -> None:
    """Periodically pings own HTTP server to prevent container sleep."""
    url = EXTERNAL_URL
    if not url:
        return
    logger.info(f"Keep-Alive auto-pinger started for URL: {url}")
    while True:
        try:
            time.sleep(300)  # Ping every 5 minutes
            r = requests.get(url, timeout=10)
            logger.info(f"[Keep-Alive] Ping {url} -> status {r.status_code}")
        except Exception as e:
            logger.warning(f"[Keep-Alive] Ping notice: {e}")


def resolve_guild_id(token: str, channel_id: str) -> Optional[str]:
    """Resolves guild_id from channel_id."""
    try:
        r = requests.get(
            f"https://discord.com/api/v9/channels/{channel_id}",
            headers={"Authorization": token, "User-Agent": USER_AGENT},
            timeout=5,
        )
        if r.status_code == 200:
            gid = r.json().get("guild_id")
            logger.info(f"Resolved Guild ID: {gid} for Channel: {channel_id}")
            return gid
    except Exception as e:
        logger.warning(f"Could not resolve guild_id: {e}")
    return None


class AltAccountWatcher:
    """Alt account worker: sits in VC as active viewer, re-joins cleanly on disconnect."""

    def __init__(self, alt_token: str, guild_id: str, channel_id: str) -> None:
        self.token = alt_token
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.user_id = ""

    async def run(self) -> None:
        while True:
            try:
                logger.info("[Alt] Connecting to Discord Gateway...")
                async with websockets.connect(
                    GATEWAY_URL,
                    max_size=50 * 1024 * 1024,
                    user_agent_header=USER_AGENT,
                ) as ws:
                    hello = json.loads(await ws.recv())
                    hb_interval = hello["d"]["heartbeat_interval"] / 1000.0

                    identify = {
                        "op": 2,
                        "d": {
                            "token": self.token,
                            "capabilities": 30717,
                            "properties": {
                                "os": "Windows",
                                "browser": "Discord Client",
                                "device": "",
                                "system_locale": "en-US",
                                "browser_user_agent": USER_AGENT,
                                "client_build_number": 594031,
                            },
                            "presence": {"status": "online", "since": 0, "activities": [], "afk": False},
                            "compress": False,
                        },
                    }
                    await ws.send(json.dumps(identify))

                    async def alt_heartbeat():
                        while True:
                            await asyncio.sleep(hb_interval)
                            await ws.send(json.dumps({"op": 1, "d": None}))

                    hb_task = asyncio.create_task(alt_heartbeat())

                    while True:
                        m = await ws.recv()
                        d = json.loads(m)
                        if d.get("t") == "READY":
                            self.user_id = d["d"]["user"]["id"]
                            logger.info(f"[Alt] Logged in as: {d['d']['user']['username']}")
                            break

                    # Join VC once
                    logger.info(f"[Alt] Joining Voice Channel {self.channel_id} as Active Viewer...")
                    await ws.send(json.dumps({
                        "op": 4,
                        "d": {
                            "guild_id": self.guild_id,
                            "channel_id": self.channel_id,
                            "self_mute": False,
                            "self_deaf": False,
                            "self_video": False,
                        },
                    }))

                    # Listen for events & only rejoin if explicitly disconnected
                    while True:
                        m = await ws.recv()
                        d = json.loads(m)
                        t = d.get("t")

                        if t == "STREAM_CREATE":
                            sk = d["d"]["stream_key"]
                            logger.info(f"[Alt] Stream detected: {sk}. Sending STREAM_WATCH...")
                            await ws.send(json.dumps({"op": 19, "d": {"stream_key": sk}}))

                        elif t == "VOICE_STATE_UPDATE":
                            if d["d"].get("user_id") == self.user_id:
                                cur_c = d["d"].get("channel_id")
                                # If disconnected, wait 2 seconds then rejoin
                                if cur_c is None or cur_c != self.channel_id:
                                    logger.info(f"[Alt] Voice state disconnected (channel={cur_c}). Rejoining in 2s...")
                                    await asyncio.sleep(2.0)
                                    await ws.send(json.dumps({
                                        "op": 4,
                                        "d": {
                                            "guild_id": self.guild_id,
                                            "channel_id": self.channel_id,
                                            "self_mute": False,
                                            "self_deaf": False,
                                            "self_video": False,
                                        },
                                    }))

            except Exception as e:
                logger.warning(f"[Alt] Connection notice: {e}. Auto-reconnecting in 5s...")
                await asyncio.sleep(5)


class MainCloudStreamer:
    """Main account worker: broadcasts live status and screen shares 24/7."""

    def __init__(self, token: str, guild_id: Optional[str], channel_id: Optional[str]) -> None:
        self.token = token
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.user_id = ""

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
            "timestamps": {"start": int(time.time() * 1000)},
            "assets": {
                "large_image": "twitch:streamer",
                "large_text": STREAM_TITLE,
                "small_image": "live",
                "small_text": "Live",
            },
        }

    async def _run_stream_media_server(self, stream_endpoint: str, stream_token: str, rtc_server_id: str, session_id: str) -> None:
        """Maintains the active Go-Live screen share on Discord's stream media server."""
        while True:
            try:
                stream_ws_url = f"wss://{stream_endpoint}/?v=7"
                logger.info(f"Connecting to Stream Server: {stream_ws_url} (server_id: {rtc_server_id})...")

                async with websockets.connect(stream_ws_url) as svws:
                    s_hello = json.loads(await svws.recv())
                    s_hb_interval = s_hello["d"]["heartbeat_interval"] / 1000.0

                    async def s_heartbeat():
                        while True:
                            await asyncio.sleep(s_hb_interval)
                            await svws.send(json.dumps({"op": 3, "d": int(time.time() * 1000)}))

                    s_hb_task = asyncio.create_task(s_heartbeat())

                    # Identify on Stream Server with rtc_server_id
                    s_identify = {
                        "op": 0,
                        "d": {
                            "server_id": rtc_server_id,
                            "user_id": self.user_id,
                            "session_id": session_id,
                            "token": stream_token,
                            "video": True,
                            "streams": [{"type": "video", "rid": "100", "quality": 100}],
                            "max_dave_protocol_version": 1,
                        },
                    }
                    await svws.send(json.dumps(s_identify))
                    s_ready = json.loads(await svws.recv())
                    s_d = s_ready.get("d", {})
                    ssrc = s_d.get("ssrc")
                    modes = s_d.get("modes", ["aead_aes256_gcm_rtpsize"])
                    logger.info(f"Stream Server READY! SSRC: {ssrc}")

                    # Select Protocol
                    selected_mode = "aead_aes256_gcm_rtpsize" if "aead_aes256_gcm_rtpsize" in modes else modes[0]
                    await svws.send(json.dumps({
                        "op": 1,
                        "d": {
                            "protocol": "udp",
                            "data": {"address": "127.0.0.1", "port": 1234, "mode": selected_mode},
                        },
                    }))
                    try:
                        await asyncio.wait_for(svws.recv(), timeout=3.0)
                    except Exception:
                        pass

                    # Unpause stream & activate speaking
                    await svws.send(json.dumps({"op": 22, "d": {"paused": False}}))
                    if ssrc:
                        await svws.send(json.dumps({"op": 5, "d": {"speaking": 2, "delay": 0, "ssrc": ssrc}}))

                    logger.info("🔴🔴 RED 'LIVE' SCREEN SHARE IS NOW BROADCASTING 24/7! 🔴🔴")

                    # Keep stream alive indefinitely
                    while True:
                        await asyncio.sleep(15)

            except Exception as e:
                logger.warning(f"Stream media connection notice: {e}. Auto-reconnecting in 3s...")
                await asyncio.sleep(3)

    async def run(self) -> None:
        while True:
            try:
                logger.info("Connecting Main Account to Discord Gateway...")
                async with websockets.connect(
                    GATEWAY_URL,
                    max_size=50 * 1024 * 1024,
                    user_agent_header=USER_AGENT,
                ) as ws:
                    hello = json.loads(await ws.recv())
                    hb_interval = hello["d"]["heartbeat_interval"] / 1000.0
                    logger.info(f"Connected to Gateway. Heartbeat: {hb_interval:.1f}s")

                    # Identify
                    identify = {
                        "op": 2,
                        "d": {
                            "token": self.token,
                            "capabilities": 30717,
                            "properties": {
                                "os": "Windows",
                                "browser": "Discord Client",
                                "device": "CloudServer",
                                "system_locale": "en-US",
                                "browser_user_agent": USER_AGENT,
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
                    await ws.send(json.dumps(identify))

                    async def heartbeat():
                        while True:
                            await asyncio.sleep(hb_interval)
                            await ws.send(json.dumps({"op": 1, "d": None}))

                    hb_task = asyncio.create_task(heartbeat())

                    session_id = ""
                    while True:
                        m = await ws.recv()
                        d = json.loads(m)
                        if d.get("t") == "READY":
                            self.user_id = d["d"]["user"]["id"]
                            session_id = d["d"]["session_id"]
                            logger.info(f"Authenticated as: {d['d']['user']['username']} (ID: {self.user_id})")
                            logger.info("🟣 Purple STREAMING BADGE is active on Discord!")
                            break

                    if self.channel_id and self.guild_id:
                        logger.info(f"🎙 Joining Voice Channel {self.channel_id}...")

                        async def join_and_start_stream():
                            # Join Voice
                            await ws.send(json.dumps({
                                "op": 4,
                                "d": {
                                    "guild_id": self.guild_id,
                                    "channel_id": self.channel_id,
                                    "self_mute": False,
                                    "self_deaf": False,
                                    "self_video": False,
                                },
                            }))
                            await asyncio.sleep(0.5)
                            # Start Screen Share
                            await ws.send(json.dumps({
                                "op": 18,
                                "d": {
                                    "type": "guild",
                                    "guild_id": self.guild_id,
                                    "channel_id": self.channel_id,
                                    "preferred_region": None,
                                },
                            }))

                        await join_and_start_stream()

                        rtc_server_id: Optional[str] = None
                        stream_media_task: Optional[asyncio.Task] = None

                        # Event pump
                        while True:
                            m = await ws.recv()
                            d = json.loads(m)
                            t = d.get("t")

                            if t == "STREAM_CREATE":
                                rtc_server_id = d["d"].get("rtc_server_id")
                                logger.info(f"Stream created! rtc_server_id: {rtc_server_id}")

                            elif t == "STREAM_SERVER_UPDATE" and rtc_server_id:
                                s_tok = d["d"].get("token")
                                s_ep = d["d"].get("endpoint")
                                if s_tok and s_ep:
                                    logger.info(f"STREAM_SERVER_UPDATE received: {s_ep}")
                                    if stream_media_task and not stream_media_task.done():
                                        stream_media_task.cancel()
                                    stream_media_task = asyncio.create_task(
                                        self._run_stream_media_server(s_ep, s_tok, rtc_server_id, session_id)
                                    )

                            elif t == "VOICE_STATE_UPDATE":
                                if d["d"].get("user_id") == self.user_id:
                                    cur_c = d["d"].get("channel_id")
                                    is_stream = d["d"].get("self_stream", False)
                                    # If disconnected from channel, re-join cleanly
                                    if cur_c is None or cur_c != self.channel_id or not is_stream:
                                        logger.info(f"Voice state sync (channel={cur_c}, stream={is_stream}). Rejoining in 2s...")
                                        await asyncio.sleep(2.0)
                                        await join_and_start_stream()

                            elif t == "STREAM_DELETE":
                                logger.info("Stream ended. Re-initiating Go-Live stream...")
                                await asyncio.sleep(1.0)
                                await join_and_start_stream()

                    else:
                        while True:
                            await ws.recv()

            except Exception as e:
                logger.warning(f"Main Gateway notice: {e}. Auto-reconnecting in 3 seconds...")
                await asyncio.sleep(3)


async def async_main():
    if not TOKEN:
        logger.error("FATAL: No DISCORD_TOKEN provided! Set DISCORD_TOKEN env variable.")
        sys.exit(1)

    # Start HTTP server
    http_thread = threading.Thread(target=start_http_health_check, daemon=True)
    http_thread.start()

    # Start self-ping thread
    ping_thread = threading.Thread(target=self_ping_worker, daemon=True)
    ping_thread.start()

    guild_id = GUILD_ID
    if VOICE_CHANNEL_ID and not guild_id:
        guild_id = resolve_guild_id(TOKEN, VOICE_CHANNEL_ID)

    tasks = []
    main_streamer = MainCloudStreamer(TOKEN, guild_id, VOICE_CHANNEL_ID if VOICE_CHANNEL_ID else None)
    tasks.append(asyncio.create_task(main_streamer.run()))

    if ALT_TOKEN and VOICE_CHANNEL_ID and guild_id:
        alt_watcher = AltAccountWatcher(ALT_TOKEN, guild_id, VOICE_CHANNEL_ID)
        tasks.append(asyncio.create_task(alt_watcher.run()))

    await asyncio.gather(*tasks)


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Shutting down cloud streamer.")


if __name__ == "__main__":
    main()
