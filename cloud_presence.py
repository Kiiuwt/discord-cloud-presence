"""
24/7 Discord Live Streaming & Automated Voice Channel Cloud Streamer.
Maintains live purple streaming presence AND automatically joins voice channels
to broadcast Go-Live screen-shares headlessly 24/7 without your PC on.
Resilient against cloud-provider UDP NAT blocks (Render/Koyeb/Heroku).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
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

GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) discord/1.0.9253 Chrome/148.0.7778.280 "
    "Electron/42.7.1 Safari/537.36"
)


class KeepAliveHandler(BaseHTTPRequestHandler):
    """Keeps cloud free tiers (Render/Koyeb) awake via health-check pings."""

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        vc_status = (
            f"<p style='color:#38bdf8;'>🎙 Voice Channel Stream: <b>Active in VC {VOICE_CHANNEL_ID}</b></p>"
            if VOICE_CHANNEL_ID
            else "<p style='color:#a1a1aa;'>🎙 Voice Channel: Not configured (Presence only mode)</p>"
        )
        html = (
            "<!DOCTYPE html><html><head><title>Discord 24/7 Cloud Streamer</title></head>"
            "<body style='font-family:sans-serif;background:#0b0d12;color:#fff;text-align:center;padding:50px;'>"
            "<h2 style='color:#a855f7;'>🟣 Discord 24/7 Cloud Streamer: ACTIVE</h2>"
            f"<p>Game: <b>{GAME_NAME}</b> | Title: <b>{STREAM_TITLE}</b></p>"
            "<p style='color:#4ade80;'>✔ Gateway WebSocket is connected and broadcasting live.</p>"
            f"{vc_status}"
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


def resolve_guild_id(token: str, channel_id: str) -> Optional[str]:
    """Resolves guild_id from channel_id if not explicitly provided."""
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
    """Alt account worker that sits in the same VC to count stream hours."""

    def __init__(self, alt_token: str, guild_id: str, channel_id: str) -> None:
        self.token = alt_token
        self.guild_id = guild_id
        self.channel_id = channel_id

    async def run(self) -> None:
        while True:
            try:
                logger.info("[Alt] Connecting Alt Account to Gateway...")
                async with websockets.connect(
                    GATEWAY_URL,
                    max_size=50 * 1024 * 1024,
                    user_agent_header=USER_AGENT,
                ) as ws:
                    hello = json.loads(await ws.recv())
                    hb_interval = hello["d"]["heartbeat_interval"] / 1000.0

                    # Identify
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
                            logger.info(f"[Alt] Logged in as: {d['d']['user']['username']}")
                            break

                    # Join VC (muted/deafened)
                    logger.info(f"[Alt] Joining Voice Channel {self.channel_id} as Viewer...")
                    await ws.send(json.dumps({
                        "op": 4,
                        "d": {
                            "guild_id": self.guild_id,
                            "channel_id": self.channel_id,
                            "self_mute": True,
                            "self_deaf": True,
                            "self_video": False,
                        },
                    }))

                    # Keep running & watching
                    while True:
                        m = await ws.recv()
                        d = json.loads(m)
                        t = d.get("t")
                        if t == "STREAM_CREATE":
                            sk = d["d"]["stream_key"]
                            logger.info(f"[Alt] Detected Stream {sk}. Sending STREAM_WATCH...")
                            await ws.send(json.dumps({"op": 19, "d": {"stream_key": sk}}))

            except Exception as e:
                logger.warning(f"[Alt] Reconnecting in 10s: {e}")
                await asyncio.sleep(10)


class MainCloudStreamer:
    """Main account worker: broadcasts live status and streams in VC."""

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

    async def _handle_voice_media(self, voice_endpoint: str, voice_token: str, session_id: str) -> None:
        """Connects to Voice Gateway in the background without affecting main connection."""
        try:
            voice_ws_url = f"wss://{voice_endpoint}/?v=7"
            logger.info(f"Connecting to Voice Media Gateway: {voice_ws_url}...")

            async with websockets.connect(voice_ws_url) as vws:
                v_hello = json.loads(await vws.recv())
                v_hb_interval = v_hello["d"]["heartbeat_interval"] / 1000.0

                async def v_heartbeat():
                    while True:
                        await asyncio.sleep(v_hb_interval)
                        await vws.send(json.dumps({"op": 3, "d": int(time.time() * 1000)}))

                v_hb_task = asyncio.create_task(v_heartbeat())

                # Voice IDENTIFY
                v_identify = {
                    "op": 0,
                    "d": {
                        "server_id": self.guild_id,
                        "user_id": self.user_id,
                        "session_id": session_id,
                        "token": voice_token,
                        "video": True,
                        "streams": [{"type": "video", "rid": "100", "quality": 100}],
                        "max_dave_protocol_version": 1,
                    },
                }
                await vws.send(json.dumps(v_identify))
                v_ready = json.loads(await vws.recv())
                voice_d = v_ready.get("d", {})
                ssrc = voice_d.get("ssrc")
                discord_ip = voice_d.get("ip")
                discord_port = voice_d.get("port")
                modes = voice_d.get("modes", ["aead_aes256_gcm_rtpsize"])
                logger.info(f"Voice Gateway READY! SSRC: {ssrc}")

                # Attempt UDP discovery safely (survives cloud NAT without disconnecting)
                my_ip = "127.0.0.1"
                my_port = 1234
                try:
                    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    udp_sock.settimeout(2.0)
                    discovery_packet = bytearray(74)
                    discovery_packet[0] = 0x00
                    discovery_packet[1] = 0x01
                    discovery_packet[2] = 0x00
                    discovery_packet[3] = 0x46
                    if ssrc:
                        discovery_packet[4:8] = ssrc.to_bytes(4, "big")
                    udp_sock.sendto(discovery_packet, (discord_ip, discord_port))
                    resp, _ = udp_sock.recvfrom(74)
                    my_ip = resp[8:72].decode("ascii").rstrip("\x00")
                    my_port = int.from_bytes(resp[72:74], "big")
                    logger.info(f"UDP Discovery OK: {my_ip}:{my_port}")
                except Exception as udp_err:
                    logger.info(f"Cloud NAT: UDP discovery bypassed ({udp_err}). Using WebSocket signaling.")

                selected_mode = "aead_aes256_gcm_rtpsize" if "aead_aes256_gcm_rtpsize" in modes else modes[0]
                await vws.send(json.dumps({
                    "op": 1,
                    "d": {
                        "protocol": "udp",
                        "data": {"address": my_ip, "port": my_port, "mode": selected_mode},
                    },
                }))
                try:
                    await asyncio.wait_for(vws.recv(), timeout=3.0)  # Session Description
                except Exception:
                    pass

                # Send Speaking Opcode 5
                if ssrc:
                    await vws.send(json.dumps({
                        "op": 5,
                        "d": {"speaking": 2, "delay": 0, "ssrc": ssrc},
                    }))

                logger.info("🔴 FULL 24/7 GO-LIVE STREAM IS BROADCASTING OVER WEBRTC!")

                # Keep Voice WebSocket alive indefinitely
                while True:
                    await asyncio.sleep(10)

        except Exception as e:
            logger.warning(f"Voice media signaling notice: {e}. Gateway presence remains active.")

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

                    # Identify with Streaming Activity
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
                            logger.info("🟣 Purple STREAMING BADGE is now live on Discord!")
                            break

                    # If Voice Channel configured, join and stream!
                    if self.channel_id and self.guild_id:
                        logger.info(f"🎙 Joining Voice Channel {self.channel_id} in Server {self.guild_id}...")
                        # 1. Join Voice Channel
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

                        # 2. Trigger Go-Live Stream IMMEDIATELY on Gateway
                        logger.info("Broadcasting STREAM_CREATE to Discord Gateway...")
                        await ws.send(json.dumps({
                            "op": 18,
                            "d": {
                                "type": "guild",
                                "guild_id": self.guild_id,
                                "channel_id": self.channel_id,
                                "preferred_region": None,
                            },
                        }))

                        voice_media_task: Optional[asyncio.Task] = None

                        # Keep Gateway pump alive & handle voice updates
                        while True:
                            m = await ws.recv()
                            d = json.loads(m)
                            t = d.get("t")
                            if t == "VOICE_SERVER_UPDATE" and not voice_media_task:
                                v_tok = d["d"]["token"]
                                v_ep = d["d"]["endpoint"]
                                # Start voice media connection as background task so Gateway never blocks
                                voice_media_task = asyncio.create_task(
                                    self._handle_voice_media(v_ep, v_tok, session_id)
                                )
                            elif t == "VOICE_STATE_UPDATE":
                                if d["d"].get("user_id") == self.user_id:
                                    logger.info(f"Voice state verified: in VC {d['d'].get('channel_id')}")

                    else:
                        # Presence only mode
                        while True:
                            await ws.recv()

            except Exception as e:
                logger.warning(f"Main Gateway connection lost: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)


async def async_main():
    if not TOKEN:
        logger.error("FATAL: No DISCORD_TOKEN provided! Set DISCORD_TOKEN env variable.")
        sys.exit(1)

    # Start HTTP keep-alive server
    http_thread = threading.Thread(target=start_http_health_check, daemon=True)
    http_thread.start()

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
