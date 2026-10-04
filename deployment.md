# Deployment Guide: Local Backend + Online Frontend & Database

This guide explains how to deploy the system using your chosen architecture:
* 🌐 **Database Online**: Managed serverless PostgreSQL on **Neon.tech** (Free, cloud-hosted).
* 🚀 **Frontend Online**: Deployed globally on **Vercel** (Free, automatic HTTPS).
* 💻 **Backend & Engine on Local Machine**: Running on your local Windows PC (with Chrome, NVDA, and Speech Viewer).
* 🔒 **The Bridge**: **Cloudflare Tunnel** (Free, secure HTTPS URL connecting your online frontend to your local backend without port forwarding).

---

## 🏗️ Architecture Overview

```
                      ┌──────────────────────────────────────────┐
                      │          ONLINE FRONTEND                 │
                      │          Hosted on Vercel                │
                      │  https://your-auditor.vercel.app        │
                      └────────────────────┬─────────────────────┘
                                           │
                                           │ HTTPS API Calls
                                           ▼
                      ┌──────────────────────────────────────────┐
                      │       CLOUDFLARE TUNNEL (Free)           │
                      │  https://xxxx.trycloudflare.com          │
                      │         (or custom domain)               │
                      └────────────────────┬─────────────────────┘
                                           │ Secure Tunnel
                                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│  YOUR LOCAL WINDOWS MACHINE                                            │
│  ├─ FastAPI Backend (http://127.0.0.1:8000)                           │
│  ├─ Google Chrome (Selenium WebDriver)                                 │
│  ├─ NVDA Screen Reader + Speech Viewer (Active Window)                 │
│  └─ Background Worker Queue (Sequential audit execution)               │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   │ Direct SSL Connection
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│  ONLINE POSTGRESQL DATABASE (Neon.tech)                                │
│  - Stores audit history, compliance metrics, and full JSONB reports    │
│  - Accessible from anywhere with SSL connection string                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Prerequisites Checklist

Before you begin, ensure you have:
1. **Google Gemini API Key**: From [Google AI Studio](https://aistudio.google.com/).
2. **GitHub Account**: To push code for automatic deployment on Vercel.
3. **Vercel Account**: Free account at [vercel.com](https://vercel.com).
4. **Neon Account**: Free serverless PostgreSQL at [neon.tech](https://neon.tech).
5. **On your Local Windows PC**:
   * Python 3.10+ installed
   * Node.js (v18+) & npm installed
   * Google Chrome installed
   * NVDA installed with Speech Viewer open

---

## Step 1: Set Up Online PostgreSQL Database (Neon.tech)

1. Sign up at [Neon.tech](https://neon.tech) and click **Create Project**.
2. Name your project (e.g. `nvda-accessibility-auditor`).
3. Under **Connection Details**, select **PostgreSQL** and copy your connection string. It will look like this:
   ```text
   postgresql://alex:AbC123xyz@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. **No manual SQL scripts are required**: When your local backend runs, it automatically connects to Neon and provisions the `audits` table, indexes, and schemas.

---

## Step 2: Configure Your Local Backend

### 2.1 Install Python Dependencies
Open PowerShell in your project root:
```powershell
# Navigate to project folder
cd "C:\Users\Harsh Vardhan Seth\Desktop\NVDA_TEXT_EXTRACTOR - Copy"

# Install all backend and testing requirements
pip install -r requirements.txt
```

### 2.2 Update Local `.env` File
Edit the `.env` file in the project root:
```env
# Google Gemini AI Key
GEMINI_API_KEY=AIzaSy...your_actual_gemini_key_here...
GEMINI_MODEL=gemini-2.5-flash

# Online Neon PostgreSQL Database
DATABASE_URL=postgresql://alex:AbC123xyz@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require

# Frontend CORS (allow local testing and your future Vercel URL)
FRONTEND_ORIGIN=https://*.vercel.app,http://localhost:5173
```

### 2.3 Test the Local Backend
Verify that the backend connects to your online database:
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Open [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) in your browser. You should see:
```json
{
  "status": "ok",
  "service": "accessibility-testing-api",
  "database": "connected"
}
```
*(Press `Ctrl + C` in PowerShell to stop the server for now).*

---

## Step 3: Expose Your Local Backend Online (Cloudflare Tunnel)

Because your frontend will run online on an **HTTPS** URL (Vercel), web browsers will block it from talking directly to `http://localhost:8000` (Mixed Content policy). A **Cloudflare Tunnel** securely exposes your local backend to the internet with a public HTTPS URL for free.

### 3.1 Install `cloudflared`
Download Cloudflare Tunnel on your Windows machine:
* **Option A (via Winget)**:
  ```powershell
  winget install --id Cloudflare.cloudflared
  ```
* **Option B (Direct Download)**:
  Download `cloudflared-windows-amd64.exe` from [Cloudflare Releases](https://github.com/cloudflare/cloudflared/releases/latest), rename it to `cloudflared.exe`, and move it to a folder in your PATH (e.g., `C:\Windows\System32` or your project folder).

### 3.2 Start a Quick Tunnel (No Domain or Account Required)
Whenever you want to expose your backend, run:
```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```
Cloudflare will output a public HTTPS URL like:
```text
https://random-words-1234.trycloudflare.com
```
👉 **Copy this URL**. This is your public Backend API URL!

*(Note: Keep this terminal open while testing. If you own a custom domain on Cloudflare, you can also set up a named permanent tunnel like `api.yourdomain.com`).*

---

## Step 4: Deploy the Frontend Online (Vercel)

### 4.1 Push Your Code to GitHub
Ensure your repository is pushed to GitHub:
```powershell
git add .
git commit -m "Configure deployment"
git push origin main
```

### 4.2 Deploy on Vercel
1. Log in to [Vercel](https://vercel.com) using your GitHub account.
2. Click **Add New...** $\rightarrow$ **Project**.
3. Select your repository and click **Import**.
4. Configure the project:
   * **Framework Preset**: Vite
   * **Root Directory**: Click *Edit* and select **`frontend`**
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
5. **Environment Variables**:
   Add the following environment variable:
   * **Key**: `VITE_API_BASE_URL`
   * **Value**: Your Cloudflare Tunnel URL (e.g. `https://random-words-1234.trycloudflare.com` or your custom API domain, *without trailing slash*).
6. Click **Deploy**.

Vercel will build and deploy your React app in ~60 seconds and give you a live URL like:
```text
https://nvda-accessibility-auditor.vercel.app
```

---

## Step 5: How to Run the System Daily

Whenever you want to use the application or run audits from anywhere in the world:

### Quick 3-Step Routine on Your Windows PC:

1. **Step 1: Open NVDA & Speech Viewer**
   * Start NVDA.
   * Press `NVDA + N` $\rightarrow$ **Tools** $\rightarrow$ **Speech Viewer** (keep the window open).

2. **Step 2: Start Local Backend**
   Open a terminal and run:
   ```powershell
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
   ```

3. **Step 3: Start Cloudflare Tunnel**
   Open a second terminal and run:
   ```powershell
   cloudflared tunnel --url http://127.0.0.1:8000
   ```

4. **Step 4: Use Your App Online!**
   * Open your Vercel URL (`https://your-auditor.vercel.app`) from any phone, laptop, or browser.
   * Enter any website URL (e.g., `https://example.com`) and click **Start Audit**.
   * Your online frontend sends the audit request through the tunnel to your local PC.
   * Your local PC launches Chrome, traverses with NVDA, captures speech, sends observations to Gemini, and saves the final report directly to your online Neon PostgreSQL database!
   * The results and live progress stream back to your online Vercel dashboard.

---

## ⚡ Bonus: One-Click Startup Script for Windows

To avoid opening multiple command prompts manually, create a file named `start_local_backend.bat` in your project root:

```bat
@echo off
title Accessibility Auditor - Local Engine
echo ========================================================
echo Starting NVDA Accessibility Backend and Cloudflare Tunnel
echo ========================================================

:: Check if NVDA is running
tasklist /FI "IMAGENAME eq nvda.exe" 2>NUL | find /I /N "nvda.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo [WARNING] NVDA is not running! Please start NVDA and open Speech Viewer.
)

:: Start Backend in a new window
echo Starting FastAPI Backend on port 8000...
start "FastAPI Backend" cmd /k "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1"

:: Wait 3 seconds for backend to initialize
timeout /t 3 /nobreak >nul

:: Start Cloudflare Tunnel
echo Starting Cloudflare Tunnel...
cloudflared tunnel --url http://127.0.0.1:8000
```

Double-clicking `start_local_backend.bat` will start the backend and give you the public tunnel URL immediately!

---

## 🔍 Troubleshooting & FAQs

### Q: Why does my browser say "Failed to fetch" on Vercel?
* Ensure `cloudflared` is running on your local machine.
* Check that `VITE_API_BASE_URL` in your Vercel Project Settings matches your current Cloudflare tunnel URL.
* If you restart a temporary tunnel (`trycloudflare.com`), the URL changes. Update `VITE_API_BASE_URL` in Vercel or configure a permanent Cloudflare Tunnel with a custom domain.

### Q: Can multiple people run audits at the same time?
* Yes! The backend has an in-memory sequential queue (`AuditService`).
* Additional audits will show `"status": "queued"` on the frontend and will automatically run one by one as your local screen reader finishes the previous audit, avoiding focus conflicts.

### Q: Can my laptop go to sleep while an audit is running?
* No. Since Chrome and NVDA require an active desktop session and CPU time, keep your Windows PC awake while audits are in progress (set Windows Power Settings to "Never sleep when plugged in").

### Q: Can I view past audits if my local PC is turned off?
* Because the database is hosted online on **Neon.tech**, any audits already saved can still be retrieved if you query the database, but live status polling and new audits require your local PC to be running.
