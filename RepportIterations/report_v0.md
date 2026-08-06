# Website Defacement Detection and Mitigation Tool: Technical Report (Version 0)

## 1. Introduction & Core Functionalities

The **Website Defacement Detection & Mitigation Tool** is an automated cybersecurity monitoring system designed to detect unauthorized visual, structural, and content alterations on web applications. The system periodically captures target web pages, performs pixel-level image comparisons, and utilizes Multimodal Artificial Intelligence (Vision LLMs) to evaluate visual changes and detect defacement attacks while minimizing false positives.

### Key Functionalities

- **Automated Periodic Web Capture**: Schedules headless Chromium browser checks using Playwright to capture high-fidelity snapshots of target websites.  
  `[ Screenshot Placeholder: Automated Scheduled Capture In Progress ]`

- **Dynamic Element Masking & Fragment Isolation**: Masks dynamic elements (such as live clocks or ad banners) using CSS selectors prior to capture, or isolates specific DOM sections.  
  `[ Screenshot Placeholder: CSS Selector Configuration for Hiding Dynamic Elements ]`

- **Visual Structural Comparison & Diff Highlighting**: Computes structural similarity scores using Pillow and generates visual diff images highlighting altered areas in red.  
  ![Visual Diff Overlay](../static/screenshots/10/diff_20260724_020658.png)

- **Multimodal AI Analysis Dispatcher**: Delegates screenshots (baseline, current, and diff overlay) to Vision models (local Ollama `llama3.2-vision` or Google Gemini `gemini-2.5-flash`) to categorize changes into *Defacement*, *Regular Content Update*, *Layout Bug*, or *No Change*.  
  `[ Screenshot Placeholder: AI Analysis Diagnostic Output ]`

- **Single-Page Web Dashboard**: Provides a web interface built with FastAPI and Vanilla JS for adding targets, setting threshold parameters, inspecting audit logs, and resetting baseline snapshots.  
  `[ Screenshot Placeholder: Dashboard Target Management Interface ]`

- **Multi-Channel Incident Alerting**: Dispatches automated Webhook (Discord, Slack, Teams) payloads and SMTP email notifications upon target unreachability or confirmed defacement.  
  `[ Screenshot Placeholder: Webhook & SMTP Email Alert Notification ]`

---

## 2. System Architecture & How It Works

The system operates via an automated execution pipeline:

![Technology Stack Diagram](../TechnologyStack.png)

### Execution Pipeline Steps

1. **Target Registration**: The user registers a target URL along with optional CSS selectors (`ignored_selectors` and `target_selectors`).
2. **Baseline Snapshot Acquisition**: On initial registration, Playwright navigates to the target site and saves a clean `baseline.png`.
3. **Scheduled Audit Execution**: At configured intervals, APScheduler triggers Playwright to render the page, apply element masking, and capture `current.png`.
4. **Visual Comparison & Diff Generation**: `image_comparator.py` calculates absolute pixel differences between `baseline.png` and `current.png`, returning a similarity score (0.0 to 1.0) and generating a red-highlighted `diff.png`.
5. **Multimodal AI Analysis**: If the similarity score falls below the designated sensitivity threshold (e.g., `0.98`), `ai_analyzer.py` sends the baseline, current, and diff images to the configured LLM engine (Ollama or Gemini) for context evaluation.
6. **Incident Logging & Alerting**: Audit logs are recorded in the SQLite database (`data/monitoring.db`). If defacement or target unreachability is confirmed, Webhook and SMTP email alerts are dispatched immediately.

---

## 3. Technology Stack

- **Backend Framework**: Python 3.10+, FastAPI, Uvicorn (ASGI Server)
- **Database Layer**: SQLite3 (`data/monitoring.db`)
- **Task Scheduler**: APScheduler (AsyncIO Scheduler)
- **Browser Automation**: Playwright (Headless Chromium)
- **Image Processing**: Pillow (PIL), Scikit-Image
- **Artificial Intelligence Integration**:
  - **Local Vision Provider**: Ollama API (`llama3.2-vision` / `llava`)
  - **Cloud Vision Provider**: Google GenAI SDK (`gemini-2.5-flash`)
- **Frontend Dashboard**: HTML5, Vanilla CSS, Vanilla JavaScript
- **Notification Services**: Standard Python `smtplib` and HTTP `urllib.request` Webhooks

---

## 4. Visual Evidence & Screenshots

### Baseline Target Screenshot
![Baseline Screenshot](../static/screenshots/10/baseline.png)

### Current Target Snapshot
![Current Snapshot](../static/screenshots/10/current_20260724_020658.png)

### Visual Diff Highlight (Red Overlay)
![Visual Diff Overlay](../static/screenshots/10/diff_20260724_020658.png)

### Interface Placeholders
- `[ Screenshot Placeholder: Web Dashboard Central Interface ]`
- `[ Screenshot Placeholder: Audit Logs and System Settings ]`

---

## 5. Problems Encountered & Current Challenges

1. **Local vs. Target VM Environment Parity (Primary Problem)**  
   Development was initially conducted in local host environments rather than the Virtual Machine (VM) provided by the professor. This resulted in the tool being fully operational in local host environments but non-operational within the provided VM. After multiple iterations, resolving full operational compatibility on the VM remains the primary ongoing challenge.

2. **Intermittent Baseline Capture Failures**  
   In very rare occasions, the Playwright screenshot engine fails to capture the baseline screenshot for a target website, even though the target website is active and fully operational.

3. **Network Connection Failures to Test Websites**  
   Intermittent network connectivity issues cause target connection failures when attempting to reach test websites during automated monitoring checks.

---

## 6. Conclusion & Next Steps

### Conclusion
The Website Defacement Detection Tool establishes an automated, multi-tiered security pipeline combining browser automation, visual diffing, and Multimodal Vision AI to identify malicious web defacement while minimizing false positives caused by benign dynamic updates.

### Next Steps & Future Plans
- **VM Parity & Environment Resolution**: Troubleshoot browser dependencies, network configurations, and permission settings within the provided VM to establish full operational stability.
- **Robust Capture Error Handling**: Implement retry mechanisms and secondary render waits in `screenshot_engine.py` to eliminate rare baseline capture failures on slow-loading websites.
- **Network Error Classification**: Refine network error handling to clearly distinguish transient network drops from actual website outages before issuing critical alerts.
