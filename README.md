# 🟣 Discord 24/7 Cloud Streamer & Badge Leveling Engine

A lightweight, high-performance cloud runner that keeps your Discord account broadcasting a **live purple Streaming status & badge 24/7/365** AND automatically joins a voice channel to broadcast a **Go-Live screen share** to level up your **Discord Streaming Progression Badge (Star ➔ Phenomenon 5,000h)** — completely free and **without needing your PC turned on**.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status: Production Ready](https://img.shields.io/badge/status-active-success.svg)

---

## ✨ Features

- ☁️ **100% PC-Free (Cloud Powered)**: Runs entirely on free cloud hosts (Render, Koyeb, Railway, VPS, or Docker). Turn your PC off, disconnect Wi-Fi, or go to sleep—your stream stays live.
- 📺 **Profile Streaming Badge**: Broadcasts real-time purple streaming presence with customizable games (Minecraft, Valorant, etc.) and Twitch/YouTube links across all mutual servers and friend lists.
- 🎙️ **Automated Voice Go-Live**: Headlessly joins your voice channel and broadcasts a WebRTC video stream (`self_stream: True`).
- 👥 **Dual-Account Auto-Viewer**: Automatically connects a second/alt account into the same voice channel to watch your stream so Discord's server rolls up every single elapsed hour toward your badge.
- 🔒 **DAVE E2EE Compatible**: Fully compatible with Discord's latest voice encryption protocol (DAVE MLS E2EE) and UDP discovery.
- ⚡ **Built-In Keep-Alive Server**: Integrated HTTP server on port `8080` that responds to free uptime monitors (UptimeRobot, Cron-Job) so your container never sleeps.

---

## 🚀 3-Minute Free Setup on Render.com

### Step 1: Fork or Upload to GitHub
1. Star and Fork this repository, or upload these files to your GitHub repository:
   - `cloud_presence.py`
   - `requirements.txt`
   - `render.yaml`

### Step 2: Deploy to Render
1. Go to **[Render Dashboard](https://dashboard.render.com/)** and sign up for free.
2. Click **New +** ➔ **Web Service**.
3. Select your GitHub repository (`discord-cloud-presence`).
4. Set the basic configuration:
   - **Language**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python cloud_presence.py`
   - **Instance Type**: `Free`

### Step 3: Add Environment Variables
Under the **Environment Variables** tab, add your settings:

| Variable Name | Required | Example Value | Description |
|---|:---:|---|---|
| `DISCORD_TOKEN` | **YES** | `MTIzNjk0NTczMDA...` | Your main Discord account token |
| `VOICE_CHANNEL_ID` | Optional | `1359567308925833414` | The voice channel ID where you want to stream 24/7 |
| `ALT_TOKEN` | Optional | `MTQ4NTk2MDcxMjE...` | An alt account token to sit in the VC and watch your stream |
| `STREAM_GAME` | Optional | `Minecraft` | The game name shown on your profile |
| `STREAM_TITLE` | Optional | `24/7 Live Stream` | Stream description displayed on your profile |
| `STREAM_URL` | Optional | `https://www.twitch.tv/discord` | Stream link |

Click **Save Changes / Deploy Web Service**!

---

## 📖 How to Get Your IDs & Tokens

<details>
<summary><b>🔑 How to get your Discord Token (Main or Alt)</b></summary>

1. Open Discord in your web browser (Chrome / Edge / Firefox) at [discord.com/app](https://discord.com/app).
2. Press `F12` (or `Ctrl + Shift + I`) to open Developer Tools.
3. Click the **Console** tab at the top.
4. Paste the following snippet and press `Enter`:
   ```javascript
   window.webpackChunkdiscord_app.push([
     [Math.random()],
     {},
     (req) => {
       for (const m of Object.keys(req.c).map((x) => req.c[x].exports).filter((x) => x)) {
         if (m.default && m.default.getToken !== undefined) {
           return console.log("YOUR TOKEN:", m.default.getToken());
         }
         if (m.getToken !== undefined) {
           return console.log("YOUR TOKEN:", m.getToken());
         }
       }
     },
   ]);
   ```
5. Copy your token (never share this with anyone except your private Render environment variables).
</details>

<details>
<summary><b>🎙️ How to get your Voice Channel ID</b></summary>

1. In Discord, go to **User Settings** ➔ **Advanced**.
2. Turn **Developer Mode** ON.
3. Right-click any Voice Channel in your server and click **Copy Channel ID**.
</details>

---

## ⏰ Keep Free Tier Running 24/7 (Prevent Render Sleeping)

Render's free tier puts web services to sleep after 15 minutes of inactivity. To keep your stream running 24/7/365 uninterrupted:

1. Copy your public Render service URL (e.g., `https://discord-cloud-presence.onrender.com`).
2. Go to **[Cron-Job.org](https://cron-job.org/)** or **[UptimeRobot.com](https://uptimerobot.com/)** (100% free).
3. Create a free HTTP ping monitor:
   - **URL**: `https://your-app-name.onrender.com`
   - **Interval**: Every `10 minutes`
4. The built-in health server will respond with `200 OK` and keep your cloud instance awake indefinitely!

---

## 📁 Repository Structure

```text
├── cloud_presence.py     # Main cloud runner (Gateway, Voice WebRTC & HTTP health server)
├── requirements.txt      # Python dependencies (websockets, requests)
├── render.yaml           # 1-Click blueprint configuration for Render.com
├── Dockerfile            # Container definition for Docker/VPS deployments
├── Procfile              # Heroku/Railway process definition
└── README.md             # Documentation and setup guide
```

---

## ⚠️ Disclaimer

This project is intended for educational purposes and personal presence automation. Use responsibly and in accordance with Discord's Terms of Service.
