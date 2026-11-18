<div align="center">

# Discord 24/7 Cloud Streamer & Badge Engine

<p>A headless, zero-PC cloud runner that broadcasts a live streaming presence and automates voice channel screen sharing to level up your Discord Streaming Progression Badge (Star ➔ Phenomenon 5,000h).</p>

<p>
  <a href="https://render.com"><img src="https://img.shields.io/badge/Deploy%20to-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white" alt="Deploy to Render" /></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" /></a>
  <a href="https://discord.com"><img src="https://img.shields.io/badge/Discord-Voice%20Gateway-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord Gateway" /></a>
  <a href="https://webrtc.org"><img src="https://img.shields.io/badge/WebRTC-DAVE%20E2EE-333333?style=for-the-badge&logo=webrtc&logoColor=white" alt="WebRTC DAVE" /></a>
</p>

</div>

---

## Overview

This tool runs 100% in the cloud to maintain your Discord live streaming status and automate voice channel streaming without leaving your personal computer running.

- **Zero PC Usage**: Runs completely on cloud infrastructure (Render, Koyeb, Railway, VPS, or Docker).
- **Profile Presence**: Broadcasts an unbroken purple Streaming badge with custom game titles and Twitch/YouTube links.
- **Voice Channel Go-Live**: Connects headlessly to your voice channel and broadcasts a WebRTC video stream (`self_stream: True`).
- **Dual-Account Auto-Viewer**: Connects an alt account into the same voice channel to watch your stream so Discord registers elapsed hours toward the Star / Phenomenon badge.
- **Protocol Compatibility**: Compatible with Discord's DAVE MLS E2EE voice protocol and UDP IP discovery.
- **Automated Keep-Alive**: Integrated HTTP server on port `8080` for uptime monitors so free containers never spin down.

---

## Setup Guide (Render.com)

### 1. Upload to GitHub
Create a repository on GitHub and upload the three deployment files:
- `cloud_presence.py`
- `requirements.txt`
- `render.yaml`

### 2. Create Web Service
1. Log in to [Render Dashboard](https://dashboard.render.com/).
2. Select **New +** ➔ **Web Service**.
3. Connect your repository.
4. Verify the build settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python cloud_presence.py`
   - **Plan**: `Free`

### 3. Environment Variables

Under **Environment**, configure the following variables:

| Variable | Required | Example | Purpose |
|:---|:---:|:---|:---|
| `DISCORD_TOKEN` | **Yes** | `MTIzNjk0NTczMDA...` | Your main Discord account user token |
| `VOICE_CHANNEL_ID` | Optional | `1359567308925833414` | Target voice channel ID for automated streaming |
| `ALT_TOKEN` | Optional | `MTQ4NTk2MDcxMjE...` | Alt account token to join as active stream viewer |
| `STREAM_GAME` | Optional | `Minecraft` | Game title displayed on profile |
| `STREAM_TITLE` | Optional | `24/7 Live Stream` | Description displayed on profile |
| `STREAM_URL` | Optional | `https://www.twitch.tv/discord` | Stream destination link |

Select **Save, rebuild, and deploy**.

---

## Obtaining Tokens and Channel IDs

<details>
<summary><b>Retrieve Discord Token (Console Snippet)</b></summary>

1. Open Discord in your web browser at [discord.com/app](https://discord.com/app).
2. Press `F12` (or `Ctrl + Shift + I`) to open Developer Tools.
3. Switch to the **Console** tab.
4. Execute the following code:
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
5. Copy the returned token string.
</details>

<details>
<summary><b>Retrieve Voice Channel ID</b></summary>

1. In Discord desktop or web, open **User Settings** ➔ **Advanced**.
2. Enable **Developer Mode**.
3. Right-click your voice channel and select **Copy Channel ID**.
</details>

---

## 24/7 Uptime (Prevent Free Tier Sleep)

Render free instances spin down after 15 minutes of inactivity. To ensure 24/7 continuous streaming:

1. Copy your Render web service URL (e.g. `https://discord-cloud-presence.onrender.com`).
2. Set up a free HTTP ping monitor on [Cron-Job.org](https://cron-job.org/) or [UptimeRobot.com](https://uptimerobot.com/).
3. Configure the monitor to request your URL every **10 minutes**.
4. The embedded HTTP server will return `200 OK` and keep your runner awake.

---

## Architecture

```text
├── cloud_presence.py     # Main cloud runner (Gateway, Voice WebRTC & HTTP health server)
├── requirements.txt      # Python dependencies (websockets, requests)
├── render.yaml           # Automated blueprint configuration
├── Dockerfile            # Container deployment definition
├── Procfile              # Heroku/Railway process definition
└── README.md             # Documentation
```

---

## Disclaimer

This utility is developed for personal presence automation and educational analysis. Use responsibly and adhere to Discord's Terms of Service.
