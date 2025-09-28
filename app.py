# app.py
from flask import Flask, request, jsonify
import json, math, os

app = Flask(__name__)

# Load locations JSON (make sure file name matches)
DATA_FILE = os.environ.get("LOCATIONS_FILE", "locations_with_latlon_updated.json")
with open(DATA_FILE, "r", encoding="utf-8") as f:
    locations = json.load(f)

# Haversine distance (km)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def find_nearest(user_lat, user_lon):
    nearest = None
    min_dist = float("inf")
    for loc in locations:
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        # skip if lat/lon missing
        if lat in (None, "", "null") or lon in (None, "", "null"):
            continue
        try:
            latf = float(lat)
            lonf = float(lon)
        except:
            continue
        d = haversine(user_lat, user_lon, latf, lonf)
        if d < min_dist:
            min_dist = d
            nearest = loc
    return nearest, min_dist

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status":"ok","locations":len(locations)}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    # Grab raw request for debugging
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception as e:
        data = {}
    print("🔎 Incoming payload:", data, flush=True)   # 👈 log full payload to Render logs

    # Extract lat/lon (support multiple formats)
    user_lat = None
    user_lon = None

    if data.get("type") == "location" and isinstance(data.get("location"), dict):
        user_lat = data["location"].get("latitude")
        user_lon = data["location"].get("longitude")
    elif isinstance(data.get("location"), dict):
        user_lat = data["location"].get("latitude")
        user_lon = data["location"].get("longitude")
    else:
        # Maybe MSG91 sends top-level lat/lon
        user_lat = data.get("latitude") or data.get("lat")
        user_lon = data.get("longitude") or data.get("lon") or data.get("lng")

    # Try convert to float
    try:
        if user_lat is not None and user_lon is not None:
            user_lat = float(user_lat)
            user_lon = float(user_lon)
        else:
            raise ValueError("no location provided")
    except Exception:
        return jsonify({"reply":"⚠️ Please share your live location again."}), 200

    # Find nearest
    nearest, dist = find_nearest(user_lat, user_lon)
    if not nearest:
        return jsonify({"reply":"❌ Could not find a nearby center."}), 200

    # Build reply
    reply_text = (
        f"✅ Nearest Center:\n\n"
        f"📍 {nearest.get('address','-')}\n"
        f"👤 {nearest.get('incharge_name','-')}\n"
        f"📞 {nearest.get('contact_number','-')}\n"
        f"📧 {nearest.get('email','-')}\n"
        f"🌐 Map: {nearest.get('map_link','-')}\n\n"
        f"Distance: {dist:.2f} km"
    )

    return jsonify({"reply": reply_text}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
