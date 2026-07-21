# 🛡️ Website Defacement Detection & Mitigation Tool

An automated, AI-powered website monitoring and defacement detection system. The tool periodically captures full-page visual screenshots of target websites, performs structural image similarity comparison (SSIM), and utilizes Google Gemini Multimodal AI to detect unauthorized visual changes, hacking manifestos, broken CSS layouts, or website downtime.

---

## ✨ Features

- **Automated Periodic Monitoring**: Uses `APScheduler` to check target websites at user-defined intervals (e.g., every minute or every 5 minutes).
- **Headless Browser Screenshot Engine**: Uses `Playwright` to capture high-fidelity, full-page screenshots.
- **Visual Image Comparison**: Calculates Structural Similarity Index (SSIM) using `Pillow` and `scikit-image` to generate visual diff images highlighting altered areas in red.
- **Multimodal AI Analysis (Google Gemini)**: When visual changes drop below similarity thresholds, Gemini AI analyzes baseline vs. current screenshots to distinguish between:
  - Malicious defacements (hacker manifestos, defaced branding, malicious text/banners)
  - Normal updates (dynamic ads, news updates, date shifts)
  - Broken CSS / technical layout bugs
- **Web Dashboard**: Interactive UI built with FastAPI, HTML, and Vanilla JS for managing monitored targets, viewing real-time audit logs, adjusting settings, and resetting baseline screenshots.
- **Multi-Channel Alerting**: Instant notifications via Webhooks (Discord, Slack, Teams) and SMTP Email alerts for unreachable sites or confirmed defacements.
- **System Verification Suite**: Built-in test suite (`verify_system.py`) that launches a local mock website, simulates defacement attacks, and verifies end-to-end pipeline functionality.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, SQLite
- **Scheduling**: APScheduler (AsyncIO)
- **Browser Automation**: Playwright
- **Image Processing**: Pillow (PIL), Scikit-Image
- **AI Integration**: Google GenAI SDK (`google-genai`), Gemini 2.5 Flash
- **Frontend**: HTML5, Vanilla CSS (Glassmorphism design system), Vanilla JavaScript

---

## 🚀 Quick Start Guide

### 1. Prerequisites
Ensure you have Python installed on your system.

### 2. Installation & Virtual Environment Setup

Clone the repository and set up a virtual environment:

```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install required dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### 3. Environment Variables (Optional)
Set your Google Gemini API key to enable AI-powered defacement analysis:

```powershell
# PowerShell
$env:GEMINI_API_KEY="your-gemini-api-key-here"
```

---

## 💻 Running the Application

### Start the Web Server & Dashboard
Run `app.py` using your virtual environment Python:

```powershell
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

### Running the End-to-End Test Suite
To verify the complete monitoring, comparison, and alerting pipeline using a mock local website:

```powershell
python verify_system.py
```

---

## 📁 Project Structure

```
.
├── app.py                  # FastAPI web server and API endpoints
├── scheduler.py            # AsyncIO background monitoring task manager
├── screenshot_engine.py    # Playwright automated full-page screenshot generator
├── image_comparator.py     # Image SSIM analysis & visual diff highlighter
├── gemini_analyzer.py      # Google Gemini Multimodal AI defacement evaluation
├── database.py             # SQLite database layer for targets, logs & settings
├── verify_system.py        # End-to-end integration test runner & mock server
├── requirements.txt        # Project dependencies
├── templates/
│   └── index.html          # Main web dashboard interface
└── static/
    ├── app.js              # Frontend dashboard interactive script
    └── screenshots/        # Directory holding baseline, current, and diff images
```

---

## ⚙️ Configuration & Alerts

Through the Web Dashboard Settings panel (or database configuration), you can set up:
- **Webhook URL**: Webhook endpoint for real-time notifications.
- **SMTP Email Settings**: Host, port, user, and recipient for email alerts.
- **Similarity Threshold**: Sensitivity threshold (default `0.98`) to trigger AI evaluation.
