# 🟣 Discord 24/7 Streaming Presence Cloud Host

A lightweight, high-performance cloud runner that keeps your Discord account broadcasting a **live purple Streaming status & badge 24/7/365** — completely free and **without needing your PC turned on**.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

---

## ✨ Features

- **24/7 Cloud Uptime**: Runs 100% on cloud servers (Render, Koyeb, Railway, VPS, or Termux).
- **Zero PC Usage**: You can turn off your computer or go offline; the cloud host keeps your presence active.
- **Customizable Presence**: Choose your stream game (Minecraft, Valorant, Chill & Chat), stream title, and Twitch/YouTube URL.
- **Integrated Health Check**: Built-in lightweight HTTP server on port `8080` to keep free-tier cloud containers awake with uptime monitors (UptimeRobot, Cron-Job).
- **Auto-Reconnecting WebSocket**: Handles Discord Gateway disconnects and heartbeats automatically.

---

## 🚀 1-Click Setup on Render (Free)

### Step 1: Fork or Use this Repository
1. Click **Star** and **Fork** this repository to your GitHub account (or upload these files to your own repository).

### Step 2: Deploy on Render
1. Go to **[Render Dashboard](https://dashboard.render.com/)**.
2. Click **New +** ➔ **Web Service**.
3. Select your `discord-cloud-presence` repository.
4. Set the following:
   - **Language**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python cloud_presence.py`
   - **Instance Type**: `Free`

### Step 3: Add Environment Variables
Under the **Environment Variables** section, add:

| Key | Value | Description |
|---|---|---|
| `DISCORD_TOKEN` | *your_token_here* | **(Required)** Your Discord account token |
| `STREAM_GAME` | `Minecraft` | *(Optional)* Game or category displayed |
| `STREAM_TITLE` | `24/7 Live Stream` | *(Optional)* Stream title displayed on your profile |
| `STREAM_URL` | `https://www.twitch.tv/discord` | *(Optional)* Twitch or YouTube stream URL |

Click **Save Changes** / **Deploy Web Service**!

---

## ⏰ Keep Free Tier Awake 24/7 (Prevent Sleeping)

Free Render web services spin down after 15 minutes of inactivity. To keep your stream presence running 24/7 without interruption:

1. Copy your Render service URL (e.g., `https://discord-cloud-presence.onrender.com`).
2. Go to **[Cron-Job.org](https://cron-job.org)** or **[UptimeRobot](https://uptimerobot.com)** (100% free).
3. Create a free HTTP ping monitor pointing to your Render URL every **10 minutes**.
4. The built-in health server will respond with `200 OK` and keep your container active forever!

---

## ❓ Frequently Asked Questions

### Is this connected to my PC?
> **No.** Once deployed on Render, the Python code runs entirely on cloud servers in Render's datacenter. Your PC can be shut down, disconnected from the internet, or completely turned off, and your Discord profile will stay live.

### What are the files in this repository?
- **`cloud_presence.py`**: The Python script that connects to Discord Gateway via WebSockets and sends your live streaming status. It also runs a small background HTTP health-check server.
- **`render.yaml`**: The blueprint configuration file telling Render how to build and run the app.
- **`requirements.txt`**: The list of Python libraries needed (`websockets`, `requests`).

---

## ⚠️ Disclaimer
This tool is for educational and personal presence automation purposes. Use responsibly according to Discord's Terms of Service.
