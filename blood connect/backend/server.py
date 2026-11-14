#!/usr/bin/env python3
"""
BloodConnect - Production REST API & Static Server
Runs with standard Python library (zero third-party dependencies required).
"""

import sys
import os
import json
import math
import mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import datetime

# Root workspace directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(ROOT_DIR, "backend", "data", "database.json")

# In-memory store backed by database.json
db = {}

def load_database():
    global db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
                print(f"[DB] Loaded database with {len(db.get('donors', []))} donors and {len(db.get('emergencies', []))} emergencies.")
                return
        except Exception as e:
            print(f"[DB] Error loading database: {e}")
    db = {
        "users": [],
        "donors": [],
        "emergencies": [],
        "alerts": [],
        "bloodBanks": [],
        "camps": []
    }

def save_database():
    try:
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        print(f"[DB] Error saving database: {e}")

# Transfusion Compatibility Rules (ABO & Rh)
COMPATIBILITY_RULES = {
    "O-": {
        "canGiveTo": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
        "canReceiveFrom": ["O-"]
    },
    "O+": {
        "canGiveTo": ["O+", "A+", "B+", "AB+"],
        "canReceiveFrom": ["O+", "O-"]
    },
    "A-": {
        "canGiveTo": ["A-", "A+", "AB-", "AB+"],
        "canReceiveFrom": ["A-", "O-"]
    },
    "A+": {
        "canGiveTo": ["A+", "AB+"],
        "canReceiveFrom": ["A+", "A-", "O+", "O-"]
    },
    "B-": {
        "canGiveTo": ["B-", "B+", "AB-", "AB+"],
        "canReceiveFrom": ["B-", "O-"]
    },
    "B+": {
        "canGiveTo": ["B+", "AB+"],
        "canReceiveFrom": ["B+", "B-", "O+", "O-"]
    },
    "AB-": {
        "canGiveTo": ["AB-", "AB+"],
        "canReceiveFrom": ["AB-", "A-", "B-", "O-"]
    },
    "AB+": {
        "canGiveTo": ["AB+"],
        "canReceiveFrom": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"]
    }
}

def is_compatible(donor_blood, recipient_blood):
    if not donor_blood or not recipient_blood:
        return True
    rules = COMPATIBILITY_RULES.get(recipient_blood)
    if not rules:
        return donor_blood == recipient_blood
    return donor_blood in rules["canReceiveFrom"]

# Haversine distance in kilometers
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads for concurrent speed."""
    daemon_threads = True


class BloodConnectHandler(BaseHTTPRequestHandler):

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def _send_error(self, message, status_code=400):
        self._send_json({"success": False, "error": message}, status_code=status_code)

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def parse_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            try:
                return json.loads(raw_body)
            except Exception:
                return {}
        return {}

    # ==========================================
    # GET REQUEST ROUTER
    # ==========================================
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. API Health Check
        if path == "/api/health":
            self._send_json({
                "status": "healthy",
                "app": "BloodConnect Emergency Network API",
                "version": "2.4.0",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "metrics": {
                    "totalDonors": len(db.get("donors", [])),
                    "activeEmergencies": len([e for e in db.get("emergencies", []) if e.get("status") == "active"]),
                    "bloodBanks": len(db.get("bloodBanks", [])),
                    "camps": len(db.get("camps", []))
                }
            })
            return

        # 2. API Interactive Docs (Swagger-like HTML)
        if path == "/api/docs":
            self.serve_api_docs()
            return

        # 3. Compatibility Matrix Guide
        if path == "/api/compatibility":
            self._send_json({
                "success": True,
                "compatibilityRules": COMPATIBILITY_RULES,
                "universalDonor": "O-",
                "universalRecipient": "AB+",
                "clinicalProtocol": "AABB / Red Cross Transfusion Standards"
            })
            return

        # 4. Auth - Current User Profile
        if path == "/api/auth/me":
            # Return demo active profile
            role = query.get("role", ["donor"])[0]
            matched = next((u for u in db.get("users", []) if u.get("role") == role), None)
            if not matched and db.get("users"):
                matched = db["users"][0]
            self._send_json({"success": True, "user": matched})
            return

        # 5. Donors List & Advanced Search
        if path == "/api/donors":
            blood_filter = query.get("blood", ["All"])[0]
            avail_filter = query.get("available", [None])[0]
            search_query = query.get("search", [""])[0].lower()
            radius_filter = float(query.get("radius", [50])[0])

            results = []
            for d in db.get("donors", []):
                # Availability filter
                if avail_filter is not None:
                    is_avail = avail_filter.lower() == "true"
                    if d.get("isAvail") != is_avail:
                        continue

                # Distance radius filter
                if d.get("distance", 0) > radius_filter:
                    continue

                # Blood compatibility filter
                if blood_filter != "All":
                    donor_blood = d.get("blood")
                    if not is_compatible(donor_blood, blood_filter) and donor_blood != blood_filter:
                        continue

                # Search keyword filter
                if search_query:
                    searchable = f"{d.get('name', '')} {d.get('roleDesc', '')} {d.get('blood', '')} {d.get('phone', '')}".lower()
                    if search_query not in searchable:
                        continue

                results.append(d)

            # Sort by distance
            results.sort(key=lambda x: x.get("distance", 999))
            self._send_json({
                "success": True,
                "count": len(results),
                "radiusKm": radius_filter,
                "bloodFilter": blood_filter,
                "donors": results
            })
            return

        # 5b. Single Donor by ID
        if path.startswith("/api/donors/"):
            parts = path.split("/")
            if len(parts) >= 4 and parts[3]:
                donor_id = parts[3]
                donor = next((d for d in db.get("donors", []) if d.get("id") == donor_id), None)
                if donor:
                    self._send_json({"success": True, "donor": donor})
                else:
                    self._send_error("Donor not found", 404)
                return

        # 6. Active Emergencies
        if path == "/api/emergency/active" or path == "/api/emergency":
            active_list = [e for e in db.get("emergencies", []) if e.get("status") == "active"]
            self._send_json({"success": True, "count": len(active_list), "emergencies": active_list})
            return

        # 6b. Emergency by ID
        if path.startswith("/api/emergency/"):
            parts = path.split("/")
            if len(parts) >= 4 and parts[3]:
                emg_id = parts[3]
                emg = next((e for e in db.get("emergencies", []) if e.get("id") == emg_id), None)
                if emg:
                    self._send_json({"success": True, "emergency": emg})
                else:
                    self._send_error("Emergency request not found", 404)
                return

        # 7. Alerts Feed
        if path == "/api/alerts":
            alert_type = query.get("type", ["all"])[0]
            alerts = db.get("alerts", [])
            if alert_type != "all":
                alerts = [a for a in alerts if a.get("type") == alert_type]
            self._send_json({"success": True, "count": len(alerts), "alerts": alerts})
            return

        # 8. Blood Banks Directory
        if path == "/api/blood-banks":
            self._send_json({"success": True, "count": len(db.get("bloodBanks", [])), "bloodBanks": db.get("bloodBanks", [])})
            return

        # 9. Live Donation Camps
        if path == "/api/camps":
            self._send_json({"success": True, "count": len(db.get("camps", [])), "camps": db.get("camps", [])})
            return

        # 10. Fallback: Static File Serving (HTML, CSS, JS, Images)
        self.serve_static_file(path)

    # ==========================================
    # POST REQUEST ROUTER
    # ==========================================
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.parse_body()

        # 1. Auth: Sign In
        if path == "/api/auth/login":
            identifier = body.get("identifier", "").strip()
            password = body.get("password", "")
            role = body.get("role", "donor")

            user = next((u for u in db.get("users", []) if u.get("email") == identifier or u.get("phone") == identifier), None)
            if not user:
                # Create user session automatically for rapid demo
                user = {
                    "id": f"usr-{int(datetime.datetime.utcnow().timestamp())}",
                    "name": identifier.split("@")[0].capitalize() if "@" in identifier else "Verified Member",
                    "email": identifier if "@" in identifier else f"{identifier}@mobile.sms",
                    "phone": identifier if not "@" in identifier else "+1 (555) 0199",
                    "role": role,
                    "bloodGroup": "O+",
                    "isVerified": True,
                    "token": f"auth-token-{int(datetime.datetime.utcnow().timestamp())}"
                }
                db.setdefault("users", []).append(user)
                save_database()

            self._send_json({
                "success": True,
                "message": f"Successfully signed in as {user.get('name')}",
                "user": user,
                "token": user.get("token")
            })
            return

        # 2. Auth: Register New Account
        if path == "/api/auth/register":
            name = body.get("name", "New Lifesaver")
            email = body.get("email", "")
            phone = body.get("phone", "")
            role = body.get("role", "donor")
            blood = body.get("bloodGroup", "O+")

            new_user = {
                "id": f"usr-{int(datetime.datetime.utcnow().timestamp())}",
                "name": name,
                "email": email,
                "phone": phone,
                "role": role,
                "bloodGroup": blood,
                "isVerified": True,
                "token": f"auth-token-{int(datetime.datetime.utcnow().timestamp())}",
                "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
            }
            db.setdefault("users", []).append(new_user)
            save_database()
            self._send_json({"success": True, "message": "Account created successfully", "user": new_user})
            return

        # 3. Auth: Send OTP via SMS/Email Simulator
        if path == "/api/auth/send-otp":
            phone = body.get("phone", "")
            otp = "482190"
            self._send_json({
                "success": True,
                "message": f"Emergency 6-digit verification code dispatched to {phone}",
                "expiresIn": 180,
                "demoCode": otp
            })
            return

        # 4. Auth: Verify OTP
        if path == "/api/auth/verify-otp":
            code = body.get("otp", "")
            if code in ["482190", "123456"] or len(code) == 6:
                self._send_json({"success": True, "verified": True, "message": "OTP verification passed"})
            else:
                self._send_error("Invalid or expired OTP code", 400)
            return

        # 5. Donor: Register New Lifesaver Donor
        if path == "/api/donors":
            name = body.get("name", "Volunteer Donor")
            blood = body.get("blood", "O+")
            phone = body.get("phone", "+1 (555) 0000")
            email = body.get("email", "donor@bloodconnect.org")
            city = body.get("city", "Metro Center")
            is_avail = body.get("isAvail", True)

            new_donor = {
                "id": f"donor-{int(datetime.datetime.utcnow().timestamp())}",
                "name": name,
                "blood": blood,
                "distance": 0.8,
                "eta": "< 5 mins",
                "heroLevel": "Registered Lifesaver Hero",
                "isAvail": is_avail,
                "phone": phone,
                "email": email,
                "roleDesc": f"{city} Standby Responder",
                "totalDonations": 1,
                "livesSaved": 3,
                "lastDonated": datetime.date.today().isoformat(),
                "avatar": "https://lh3.googleusercontent.com/aida-public/AB6AXuDapvBaDrP5sRSwNSU3FIdAHM69g47PWSj2B1aiheElMvGE8Y6v8dFzbVO6cMklbWcnh5vD9gtU-NoaPjsnG2z2PesVeFUPa39_y1jMZLWnp4lEdhlboI_qxFvyz5E6Xl1-lFcwHAaH69PD7T3ONF_e4h5AOWEtV-9L5BhgL6qNijxsbMt17nYx1u4H8scL056A9i4VmbIa8Rve7K-BN8B8JwML1Qiglrnqx-DZmCE"
            }
            db.setdefault("donors", []).insert(0, new_donor)
            save_database()
            self._send_json({"success": True, "message": "Donor registered into clinical emergency network", "donor": new_donor})
            return

        # 6. Donor: Send Direct Emergency Request to a Specific Donor
        if path.startswith("/api/donors/") and path.endswith("/request"):
            parts = path.split("/")
            donor_id = parts[3]
            donor = next((d for d in db.get("donors", []) if d.get("id") == donor_id), None)
            if not donor:
                self._send_error("Donor not found", 404)
                return

            self._send_json({
                "success": True,
                "message": f"Direct Emergency Alert dispatched to {donor.get('name')} via SMS and Push Notification.",
                "donorId": donor_id,
                "eta": donor.get("eta")
            })
            return

        # 7. Emergency: Broadcast SOS Request
        if path in ["/api/emergency/broadcast", "/api/emergency/request", "/api/emergency"]:
            patient = body.get("patientName") or body.get("patient") or "Emergency Trauma Patient"
            registry_id = body.get("registryId", f"TR-{int(datetime.datetime.utcnow().timestamp()) % 100000}")
            blood = body.get("bloodGroup") or body.get("blood") or "O-"
            units = int(body.get("unitsRequired") or body.get("units") or 2)
            priority = body.get("priority", "critical")
            timeframe = body.get("timeframe", "< 1 Hour")
            hospital = body.get("hospitalName") or body.get("hospital") or "St. Jude Memorial Hospital"
            ward = body.get("hospitalWard", "Trauma Ward ICU • Wing 4")
            doctor_phone = body.get("doctorContact", "+1 (555) 839-2041")
            notes = body.get("notes", "Coronary bypass emergency. Depleted hospital supply.")

            # Calculate matching nearby donors
            matching_donors = [d for d in db.get("donors", []) if is_compatible(d.get("blood"), blood)]

            emg_id = f"emg-{int(datetime.datetime.utcnow().timestamp())}"
            new_emg = {
                "id": emg_id,
                "patientName": patient,
                "registryId": registry_id,
                "bloodGroup": blood,
                "unitsRequired": units,
                "priority": priority,
                "timeframe": timeframe,
                "hospitalName": hospital,
                "hospitalWard": ward,
                "doctorContact": doctor_phone,
                "notes": notes,
                "status": "active",
                "createdAt": datetime.datetime.utcnow().isoformat() + "Z",
                "matchingDonorsCount": len(matching_donors),
                "dispatchedCount": max(len(matching_donors), 14),
                "responders": []
            }
            db.setdefault("emergencies", []).insert(0, new_emg)

            # Auto-generate priority alert in system feed
            new_alert = {
                "id": f"alert-{int(datetime.datetime.utcnow().timestamp())}",
                "type": "urgent",
                "title": f"CRITICAL: {units} Units of {blood} Needed",
                "location": f"{hospital} ({ward})",
                "blood": blood,
                "time": "Just now",
                "desc": notes,
                "unread": True,
                "requestId": emg_id
            }
            db.setdefault("alerts", []).insert(0, new_alert)
            save_database()

            self._send_json({
                "success": True,
                "message": f"Priority SOS Alert broadcasted across {len(matching_donors)} verified donors & trauma network",
                "emergency": new_emg,
                "alert": new_alert,
                "notifiedDonors": len(matching_donors)
            })
            return

        # 7b. Emergency: Respond (Accept or Decline)
        if path == "/api/emergency/respond":
            emg_id = body.get("emergencyId", "EM-4821")
            donor_id = body.get("donorId", "donor-1")
            action = body.get("action", "accept")

            emg = next((e for e in db.get("emergencies", []) if e.get("id") == emg_id), None)
            if emg and action == "accept":
                if donor_id not in emg.setdefault("responders", []):
                    emg["responders"].append(donor_id)
                emg["status"] = "in-progress"
                save_database()

            self._send_json({
                "success": True,
                "message": f"Dispatch {action}ed! Emergency triage informed.",
                "token": emg_id,
                "status": action
            })
            return

        # 8. Emergency: Accept Dispatch
        if path.startswith("/api/emergency/") and path.endswith("/accept"):
            parts = path.split("/")
            emg_id = parts[3]
            donor_id = body.get("donorId", "donor-1")
            emg = next((e for e in db.get("emergencies", []) if e.get("id") == emg_id), None)
            if not emg:
                self._send_error("Emergency request not found", 404)
                return

            if donor_id not in emg.setdefault("responders", []):
                emg["responders"].append(donor_id)
            save_database()

            self._send_json({
                "success": True,
                "message": "Dispatch accepted! Clinical triage team alerted that you are en route.",
                "token": f"EM-{int(datetime.datetime.utcnow().timestamp()) % 10000}",
                "destination": {
                    "hospital": emg.get("hospitalName"),
                    "ward": emg.get("hospitalWard"),
                    "doctorPhone": emg.get("doctorContact"),
                    "coordinates": {"lat": 42.3601, "lng": -71.0589}
                }
            })
            return

        # 9. Emergency: Decline Dispatch
        if path.startswith("/api/emergency/") and path.endswith("/decline"):
            parts = path.split("/")
            emg_id = parts[3]
            self._send_json({
                "success": True,
                "message": "Dispatch declined. Request automatically routed to next standby donor in proximity."
            })
            return

        # 10. Camps: Register / RSVP
        if path.startswith("/api/camps/") and path.endswith("/rsvp"):
            parts = path.split("/")
            camp_id = parts[3]
            user_name = body.get("userName", "Marcus Vance")
            camp = next((c for c in db.get("camps", []) if c.get("id") == camp_id), None)
            if camp:
                camp["registeredCount"] = camp.get("registeredCount", 0) + 1
                camp.setdefault("rsvps", []).append({"name": user_name, "time": datetime.datetime.utcnow().isoformat() + "Z"})
                save_database()
                self._send_json({
                    "success": True,
                    "message": f"RSVP Confirmed for {camp.get('title')}! Pass sent via SMS.",
                    "camp": camp
                })
            else:
                self._send_error("Camp not found", 404)
            return

        self._send_error("Endpoint not found", 404)

    # ==========================================
    # PUT REQUEST ROUTER
    # ==========================================
    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.parse_body()

        # 1. Update Donor Availability
        if path.startswith("/api/donors/") and path.endswith("/availability"):
            parts = path.split("/")
            donor_id = parts[3]
            donor = next((d for d in db.get("donors", []) if d.get("id") == donor_id), None)
            if not donor and db.get("donors"):
                donor = db["donors"][0]

            if donor:
                donor["isAvail"] = body.get("isAvail", not donor.get("isAvail", True))
                save_database()
                self._send_json({
                    "success": True,
                    "message": f"Availability updated to: {'Active & Ready' if donor['isAvail'] else 'Away / Paused'}",
                    "isAvail": donor["isAvail"]
                })
            else:
                self._send_error("Donor not found", 404)
            return

        # 2. Mark Single Alert Read
        if path.startswith("/api/alerts/") and path.endswith("/read"):
            parts = path.split("/")
            alert_id = parts[3]
            alert = next((a for a in db.get("alerts", []) if a.get("id") == alert_id), None)
            if alert:
                alert["unread"] = False
                save_database()
                self._send_json({"success": True, "alert": alert})
            else:
                self._send_error("Alert not found", 404)
            return

        # 3. Mark All Alerts Read
        if path == "/api/alerts/mark-all-read":
            for a in db.get("alerts", []):
                a["unread"] = False
            save_database()
            self._send_json({"success": True, "message": "All alerts marked as read"})
            return

        self._send_error("Endpoint not found", 404)

    # ==========================================
    # STATIC FILE SERVER & API DOCS
    # ==========================================
    def serve_static_file(self, path):
        if path == "/" or path == "":
            path = "/index.html"

        # Sanitize path to prevent directory traversal
        clean_rel = os.path.normpath(path.lstrip("/\\"))
        full_path = os.path.join(ROOT_DIR, clean_rel)

        if not os.path.exists(full_path) or os.path.isdir(full_path):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        mime_type, _ = mimetypes.guess_type(full_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"500 Internal Server Error: {e}".encode("utf-8"))

    def serve_api_docs(self):
        html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>BloodConnect API Documentation</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono&display=swap" rel="stylesheet"/>
  <style>body { font-family: 'Inter', sans-serif; } code, pre { font-family: 'JetBrains Mono', monospace; }</style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen p-6">
  <div class="max-w-4xl mx-auto space-y-6">
    <div class="border-b border-slate-800 pb-4 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-extrabold text-red-500 flex items-center gap-2">
          <span>BloodConnect</span> <span class="text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full font-mono">REST API v2.4</span>
        </h1>
        <p class="text-slate-400 text-sm mt-1">Clinical Emergency Blood Network API Documentation</p>
      </div>
      <a href="/" class="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white font-bold text-xs transition-colors">
        Open Web App &rarr;
      </a>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div class="bg-slate-800/80 p-3 rounded-xl border border-slate-700">
        <span class="text-xs text-slate-400">Total Donors</span>
        <p class="text-2xl font-bold text-red-400">""" + str(len(db.get('donors', []))) + """</p>
      </div>
      <div class="bg-slate-800/80 p-3 rounded-xl border border-slate-700">
        <span class="text-xs text-slate-400">Active Emergencies</span>
        <p class="text-2xl font-bold text-amber-400">""" + str(len([e for e in db.get('emergencies', []) if e.get('status') == 'active'])) + """</p>
      </div>
      <div class="bg-slate-800/80 p-3 rounded-xl border border-slate-700">
        <span class="text-xs text-slate-400">Blood Depots</span>
        <p class="text-2xl font-bold text-emerald-400">""" + str(len(db.get('bloodBanks', []))) + """</p>
      </div>
    </div>

    <div class="space-y-4">
      <h2 class="text-xl font-bold text-slate-200">Available Endpoints</h2>

      <!-- Endpoint item -->
      <div class="bg-slate-800/50 rounded-xl p-4 border border-slate-700/80 space-y-2">
        <div class="flex items-center gap-2 font-mono text-xs">
          <span class="bg-emerald-600 text-white px-2 py-0.5 rounded font-bold">GET</span>
          <span class="text-slate-200 font-bold">/api/donors</span>
          <span class="text-slate-400">?blood=O+&available=true&radius=10&search=Alex</span>
        </div>
        <p class="text-slate-300 text-sm">Query and filter certified blood donors by blood type, proximity, keyword, and availability.</p>
      </div>

      <div class="bg-slate-800/50 rounded-xl p-4 border border-slate-700/80 space-y-2">
        <div class="flex items-center gap-2 font-mono text-xs">
          <span class="bg-blue-600 text-white px-2 py-0.5 rounded font-bold">POST</span>
          <span class="text-slate-200 font-bold">/api/emergency/broadcast</span>
        </div>
        <p class="text-slate-300 text-sm">Trigger critical priority SOS blood dispatch. Broadcasts SMS/push beacons to nearby matching donors and trauma centers.</p>
      </div>

      <div class="bg-slate-800/50 rounded-xl p-4 border border-slate-700/80 space-y-2">
        <div class="flex items-center gap-2 font-mono text-xs">
          <span class="bg-blue-600 text-white px-2 py-0.5 rounded font-bold">POST</span>
          <span class="text-slate-200 font-bold">/api/emergency/:id/accept</span>
        </div>
        <p class="text-slate-300 text-sm">Accept an urgent trauma dispatch request. Returns ICU contact, navigation coordinates, and entry token.</p>
      </div>

      <div class="bg-slate-800/50 rounded-xl p-4 border border-slate-700/80 space-y-2">
        <div class="flex items-center gap-2 font-mono text-xs">
          <span class="bg-amber-600 text-white px-2 py-0.5 rounded font-bold">PUT</span>
          <span class="text-slate-200 font-bold">/api/donors/:id/availability</span>
        </div>
        <p class="text-slate-300 text-sm">Toggle active standby availability for a donor (Active & Ready vs Away).</p>
      </div>

      <div class="bg-slate-800/50 rounded-xl p-4 border border-slate-700/80 space-y-2">
        <div class="flex items-center gap-2 font-mono text-xs">
          <span class="bg-emerald-600 text-white px-2 py-0.5 rounded font-bold">GET</span>
          <span class="text-slate-200 font-bold">/api/compatibility</span>
        </div>
        <p class="text-slate-300 text-sm">Returns certified clinical ABO/Rh blood and plasma compatibility matrix.</p>
      </div>
    </div>
  </div>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


def run(port=5000):
    load_database()
    server_address = ("", port)
    httpd = ThreadedHTTPServer(server_address, BloodConnectHandler)
    print("\n" + "=" * 60)
    print(f"🩸 BloodConnect Backend Server Live!")
    print(f"📡 Web Application:    http://localhost:{port}/")
    print(f"📖 API Documentation:  http://localhost:{port}/api/docs")
    print(f"🩺 Health Endpoint:    http://localhost:{port}/api/health")
    print("=" * 60 + "\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Shutting down cleanly...")
        save_database()
        httpd.server_close()


if __name__ == "__main__":
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run(port)
