# BloodConnect - Emergency Blood Network & Healthcare Backend

A lifesaver healthcare web application and REST API backend designed to bridge critical moments between blood donors, emergency recipients, and trauma care facilities. Built with modern web standards, Tailwind CSS, Material Symbols, and responsive mobile-first architecture.

---

## 🚀 Quick Start (One-Click Launch)

You can launch both the backend server and the mobile frontend application in 1 click:

### Option A: Windows Batch Launcher (Double-Click)
Simply double-click `start-server.bat` in the project root:
```bat
start-server.bat
```
*Auto-detects the Python 3 runtime on your machine, launches the REST API server on port 5000, and automatically opens `http://localhost:5000/` in your default browser.*

### Option B: PowerShell Launcher
```powershell
.\start-server.ps1
```
*Optional custom port: `.\start-server.ps1 -Port 8080`*

### Option C: Manual Python Launch
```bash
python backend/server.py 5000
```
*(Compatible with standard Python 3.10+ or bundled LibreOffice Python `C:\Program Files\LibreOffice\program\python.exe` with zero `pip` packages required).*

---

## 🛠️ Multi-Stack Backend Architecture

The BloodConnect backend is available in three production-grade implementations sharing the same JSON datastore (`backend/data/database.json`):

| Stack | File Location | Command | Dependencies |
|---|---|---|---|
| **Python Standard (Default)** | [server.py](file:///c:/Users/acer/blood%20connect/backend/server.py) | `python backend/server.py 5000` | **Zero external dependencies** (uses standard library `http.server`, `urllib`, `json`) |
| **Node.js / Express** | [server.js](file:///c:/Users/acer/blood%20connect/backend/node/server.js) | `cd backend/node && npm start` | `express`, `cors` |
| **FastAPI (Async Python)** | [main.py](file:///c:/Users/acer/blood%20connect/backend/fastapi/main.py) | `cd backend/fastapi && uvicorn main:app --reload --port 5000` | `fastapi`, `uvicorn`, `pydantic` |

---

## 📡 REST API Reference

The server exposes the following REST endpoints under `http://localhost:5000/api`:

### 1. System & Health
- **`GET /api/health`**
  - Returns server status, runtime, and total registered donors/emergencies.
- **`GET /api/docs`**
  - Interactive HTML documentation and API tester.
- **`GET /api/compatibility`**
  - Returns complete ABO/Rh compatibility matrix, universal donor (`O-`), and universal recipient (`AB+`).

### 2. Authentication & Verification
- **`POST /api/auth/login`**
  - Supports credential login (email/phone + password) or instant 6-digit OTP code (`123456`).
- **`POST /api/auth/otp/send`**
  - Sends a simulated emergency 6-digit verification code to the recipient's phone.

### 3. Donor Management
- **`GET /api/donors`**
  - **Query Params**:
    - `blood`: Filter by blood group (e.g., `O+`, `A-`, `All`) or compatible matches.
    - `radius`: Filter donors within radius in kilometers (e.g., `5`, `10`, `20`, `50`).
    - `available`: `true` or `false` to filter active standby donors.
    - `lat` & `lng`: Calculate live Haversine distances to the caller's GPS coordinates.
- **`GET /api/donors/:id`**
  - Retrieve full medical profile, donation history, and badges for a specific donor.
- **`POST /api/donors`**
  - Register a new lifesaver into the regional emergency registry.
- **`PUT /api/donors/availability`**
  - Toggle live dispatch beacon between "Active & Ready" and "Away / Paused".

### 4. Emergency Triage & SOS Dispatch
- **`GET /api/emergency/active`**
  - List all live code-red trauma requests in progress.
- **`POST /api/emergency/request`** (Alias: `/api/emergency/broadcast`)
  - Broadcast an emergency SOS blood request. Automatically alerts compatible standby donors within proximity and posts an alert to the notification feed.
- **`POST /api/emergency/respond`** (Alias: `/api/emergency/:id/accept`)
  - Standby donor accepts emergency dispatch; returns navigation token, hospital ward contact, and GPS coordinates.
- **`POST /api/emergency/:id/decline`**
  - Re-routes dispatch to the next standby donor in proximity.

### 5. Alerts & Inventories
- **`GET /api/alerts`**
  - Retrieve notification feed (supports `?type=all`, `urgent`, or `camps`).
- **`POST /api/alerts`**
  - Broadcast a new emergency alert.
- **`POST /api/alerts/read`**
  - Mark alerts as read.
- **`GET /api/blood-banks`**
  - List certified blood depot locations, contact info, and current ABO reserve counts.
- **`GET /api/camps`**
  - Upcoming blood donation drives with registration counts.
- **`POST /api/camps/:id/rsvp`**
  - Register attendance for a community donation drive.

---

## 🌟 Frontend Features & Integration

The frontend Single Page Application in [index.html](file:///c:/Users/acer/blood%20connect/index.html) connects seamlessly to the backend with automatic offline fallback:

1. **Auto-Detecting API Client (`ApiClient`)**:
   - When opened via HTTP (`http://localhost:5000/`), it connects to the live REST API and displays a green pulsing **`Live API (healthy)`** badge.
   - When opened directly as a file (`file:///...`), it gracefully falls back to local storage and displays **`Offline (LocalStorage)`**.
2. **All 8 Screen Views**:
   - `screens/1-splash.html` (`#splash`): Animated ECG pulse, regional dispatch sync, and auto-advance.
   - `screens/2-onboarding.html` (`#onboarding`): 3-slide touch/drag capabilities carousel.
   - `screens/3-login.html` (`#login`): Role switcher (Donor/Recipient/Hospital), password & OTP login.
   - `screens/4-home.html` (`#home`): Dashboard with live emergency banner, blood group pills, donor cards.
   - `screens/5-donor-register.html` (`#register-donor`): 2-step onboarding, GPS detection, medical declaration.
   - `screens/6-find-donors.html` (`#find-donors`): Keyword search, radius selector, list vs vector radar map.
   - `screens/7-emergency-request.html` (`#emergency-requests`): Triage severity picker (Normal/Urgent/Critical), unit stepper, animated radar broadcast modal.
   - `screens/8-donor-dashboard.html` (`#donor-dashboard`): Active dispatch acceptance (`#EM-4821`), donation history, and badges.
3. **Floating Dev Bar**:
   - **Screens Dropdown**: Jump directly to any of the 8 screens or modal dialogs.
   - **Phone Frame Toggle**: Switch between responsive mobile view and desktop phone mockup shell.
   - **Reset State**: Clears data and restores default clinical demo state.

---

## 📁 File Structure

```
c:\Users\acer\blood connect\
├── index.html                    # Main Unified Single Page Application (All screens + Router + API Client)
├── README.md                     # Comprehensive Project & API Documentation
├── start-server.bat              # One-click Windows Batch Server Launcher
├── start-server.ps1              # One-click PowerShell Server Launcher
├── backend/
│   ├── server.py                 # Standalone Zero-Dependency Python REST Server (Port 5000)
│   ├── data/
│   │   └── database.json         # Persistent JSON Database (Donors, Emergencies, Alerts, Banks, Camps)
│   ├── node/
│   │   ├── package.json          # Node.js dependencies
│   │   └── server.js             # Express.js REST API alternative implementation
│   └── fastapi/
│       ├── requirements.txt      # FastAPI / Uvicorn dependencies
│       └── main.py               # Async FastAPI alternative implementation with OpenAPI / Swagger
└── screens/                      # Individual Standalone Screen Files
    ├── 1-splash.html             # Screen 1: Splash Screen
    ├── 2-onboarding.html         # Screen 2: Onboarding Experience Carousel
    ├── 3-login.html              # Screen 3: Login & Role Selection
    ├── 4-home.html               # Screen 4: Home Dashboard
    ├── 5-donor-register.html     # Screen 5: Donor Registration & Triage
    ├── 6-find-donors.html        # Screen 6: Find Donors (Search, Filters & Map)
    ├── 7-emergency-request.html  # Screen 7: Emergency Blood Request (SOS)
    └── 8-donor-dashboard.html    # Screen 8: Donor Dashboard & Dispatches
```

---

## 🧪 Testing the Backend

You can test the server endpoints using `curl` or PowerShell:

```bash
# 1. Health check
curl http://localhost:5000/api/health

# 2. Filter donors by blood type
curl http://localhost:5000/api/donors?blood=O%2B

# 3. Create an emergency SOS request
curl -X POST http://localhost:5000/api/emergency/request \
  -H "Content-Type: application/json" \
  -d "{\"patientName\":\"John Doe\",\"blood\":\"O-\",\"units\":2,\"priority\":\"critical\"}"
```
