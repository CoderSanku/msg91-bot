from flask import Flask, request, jsonify
import json, math, os

app = Flask(__name__)

# Load locations JSON safely
DATA_FILE = os.environ.get("LOCATIONS_FILE", "locations_with_latlon_updated.json")
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        locations = json.load(f)
except Exception as e:
    print(f"❌ Failed to load locations file: {e}", flush=True)
    locations = []

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
        if lat in (None, "", "null") or lon in (None, "", "null"):
            continue
        try:
            latf, lonf = float(lat), float(lon)
        except:
            continue
        d = haversine(user_lat, user_lon, latf, lonf)
        if d < min_dist:
            min_dist = d
            nearest = loc
    return nearest, min_dist

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status":"running","endpoints":["/health","/webhook"]}), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status":"ok","locations":len(locations)}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}
    print("🔎 Incoming payload:", data, flush=True)

    user_lat, user_lon = None, None

    if isinstance(data.get("location"), dict):
        user_lat = data["location"].get("latitude")
        user_lon = data["location"].get("longitude")
    elif isinstance(data.get("userLocation"), dict):
        user_lat = data["userLocation"].get("latitude")
        user_lon = data["userLocation"].get("longitude")
    else:
        user_lat = data.get("latitude") or data.get("lat")
        user_lon = data.get("longitude") or data.get("lon") or data.get("lng")

    try:
        user_lat, user_lon = float(user_lat), float(user_lon)
    except Exception:
        return jsonify({"reply": "⚠️ Please share your live location again."}), 200

    nearest, dist = find_nearest(user_lat, user_lon)
    if not nearest:
        return jsonify({"reply": "❌ Could not find a nearby center."}), 200

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
