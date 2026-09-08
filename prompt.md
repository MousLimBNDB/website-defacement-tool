# Context : 
- i want to transform the integration of this tool to an n8n workflow, which mean :
    - having the same system architecturte but instaid of it been here i want it in nodes as a workflow n8n
    - each node is in a file and you will provide me with a schematic.md to help me know how to connect each node

# tasks : 
- get rid of any file that you see is unusable for this workflow 
- follow the workflow that i will provid in last section
- try to follow the code that you wrote in these files to creat your node, and add this miner improvements in each one of them:

    @screenshot_engine.py :
        * Snapshot Algorithm Optimization: Refined core capture algorithms to maximize website monitoring efficiency and capture speed.
        * Anti-Bot Evasion Enhancement: Strengthened bot-detection countermeasures to prevent automated inspection blocking.
        * Headless Browser Stealthing: Resolved headless browser fingerprinting issues to ensure undetectable scanning sessions.
        * Infinite Scroll Handling: Engineered solutions to reliably capture dynamic, infinite-scrolling pages across social networks and web stores.
        * User Profile Emulation: Implemented realistic user profiles and session management to eliminate automated behavior signatures.
        * Pupop handling : Improve how you can handle the popups (ads , coockes , bot detection , login , inforsing loging ,captcha ) 
        * capture popups : capture the popups indivudaly so that it can be monitored for potecial defacment
        * take long timeouts to simulate the usage of a real humain (consider the time to read text, navigate with mose and click into what you want to click on, slow scrolling not too much that it becames very slow and not too fast to be detected by the antibots) 
        * When you browse the web as a human, your brain ignores the 500ms it takes for:
            1. JavaScript Hydration / Single Page Apps: React/Vue/Next.js pages initially load a blank <div> or a skeleton screen, then asynchronously fetch JSON APIs and render the actual DOM.
            2. Web Fonts Loading: Fonts (like Google Fonts) load asynchronously. Before they load, text might render in a fallback font and cause a Layout Shift (CLS) when the real font snaps into place.
            3. Lazy-Loaded Images & Videos: Modern sites only load images when they enter the viewport. A full-page screenshot taken immediately will have gray/blank placeholders for everything below the fold.
            4. CSS Animations / Carousels / Banners: Moving hero sliders, rotating badges, and fading transitions will produce different pixel frames every millisecond, creating false positive defacement alerts.
        all of that to mitigate if two screenshots of the exact same unchanged website are taken 200ms apart with an unstable renderer,and make my image diffing algorithm will report a 40% change!
        * see how you can conter these :
            - Bot Detection & Captchas: Sites like Amazon, Pinterest, and AliExpress actively detect default Playwright/Puppeteer user agents and headless flags, serving a CAPTCHA or blocking the connection.
            - Continuous Polling / WebSockets: On heavy e-commerce sites, background tracking scripts send pings continuously, causing wait_until="networkidle" with a strict 30s timeout to throw a TimeoutError.
            - Engineering Fix for Later: When wait_until="networkidle" times out, you can catch the TimeoutError and fallback gracefully to 'load', or pass a realistic User-Agent string in browser.new_page(user_agent="...").
        * try screenshot_engine with the sites that i will provide you with in the site section and ask me every time if the screenshot is good and tweak what you need to ensure that every site i provided you with is good to go  
        * consult the github repos that i will provide you with and see what you need to copie from it counter the popup problems 
    
    @image_comparator.py
        * don't use the .resize() function, instead use a Canvas Expansion (Letterboxing / Padding) : 
            - Instead of squashing, create a new canvas sized to the maximum width and maximum height of both images, and paste both images onto their respective canvas at (0, 0)
            - Why this works:
                * Neither image gets squashed or distorted.
                * The overlapping sections align perfectly pixel-for-pixel.
                * The newly added section at the bottom (or removed section) is compared against a blank background, so it automatically gets highlighted in red as a difference!

# constraints 
- get rid of any file that is out of the work flow that i provided 
- do not add any functionality outside of what i provided you with 
- make the code simple and easy read and mentain 
- comment when needed (the primery perpes of the func and is outputs and inputs)
- ask me for any thing you need to know about what you see is good to add and you see any thing unuseful 







# github repos: 
- https://github.com/cavi-au/Consent-O-Matic.git
- https://github.com/duckduckgo/autoconsent.git
- https://github.com/moodl/playwright-mcp-extended.git

# sites to test on :
- https://i10x.ai/?fpr=thao53&gad_source=1&gad_campaignid=24047206317&gbraid=0AAAABDfEZ7Z8eBzxBDYwMr07xNp139pbN&gclid=Cj0KCQjwkOvTBhDgARIsAKUNyRtKS6TGRz7bg59tUXOQ1y_PiBiPp8vZinl6qgIoyCdDGPT7Lb1T9_UaAufOEALw_wcB
- https://www.fikesiteboom.com/
- https://www.alibaba.com
- https://www.aliexpress.com
- https://www.youtube.com
- https://vimm.net/ 
- https://playwright.dev/python/
- https://www.cerist.dz/index.php/fr/index.html
- https://www.amazon.fr/
- https://www.netacad.com/
- https://pinterest.com/
- https://news.ycombinator.com
- https://github.com/
- https://www.reddit.com/
- https://soar-ky.org/
- https://leetcode.com/

# Workflow 

```

[ Target URLs ]
       │
       ▼
[ APScheduler ] ──(Interval Trigger)──► [ Playwright Screenshot Engine ]
                                                   │
                                                   ▼
[ Baseline Image ] ──(Pillow Comparison)──► [ Current Image Snapshot ]
                                                   │
                                                   ▼
                                      [ Similarity Score Check ]
                                                   │
                        ┌──────────────────────────┴──────────────────────────┐
                        │ (Similarity < Threshold)                            │ (Similarity >= threshold)
                        ▼                                                     ▼
        [ Multimodal AI Engine ]                                      [ Log Normal Event ]
                    (Ollama)
                        │
                        ▼
      [ Incident Alerting Engine ]
                    (Webhook)

```
