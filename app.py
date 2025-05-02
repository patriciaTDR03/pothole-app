from flask import Flask, render_template, request, redirect, url_for, jsonify
from PIL import Image
import os, uuid, json, piexif, gdown
import torch

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = 'data/detections.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# Descarcă modelul din Google Drive
model_id = "1NdAXsMjzDqRjXbrttroN5_2LGUi9Vflj"
model_url = f"https://drive.google.com/uc?id={model_id}"
model_path = "best.pt"

if not os.path.exists(model_path):
    print("📥 Se descarcă modelul YOLO...")
    gdown.download(model_url, model_path, quiet=False)

# Încarcă modelul YOLOv5
model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path, force_reload=True)

# Extragere GPS din EXIF

def get_gps_from_image(img_path):
    try:
        exif_dict = piexif.load(img_path)
        gps = exif_dict.get("GPS")
        if gps:
            lat = gps[2]
            lon = gps[4]
            lat_deg = lat[0][0] / lat[0][1] + lat[1][0] / lat[1][1] / 60 + lat[2][0][0] / lat[2][0][1] / 3600
            lon_deg = lon[0][0] / lon[0][1] + lon[1][0] / lon[1][1] / 60 + lon[2][0][0] / lon[2][0][1] / 3600
            if gps[1] == b'S': lat_deg *= -1
            if gps[3] == b'W': lon_deg *= -1
            return lat_deg, lon_deg
    except:
        pass
    return None, None

# Verificare locație în Cluj

def is_in_cluj(lat, lon):
    return lat and lon and (46.5 <= lat <= 47.1) and (23.4 <= lon <= 23.8)

# Salvare detecție

def save_detection(entry):
    with open(DATA_FILE, 'r+') as f:
        data = json.load(f)
        data.append(entry)
        f.seek(0)
        json.dump(data, f, indent=2)

# Ștergere detecție

def delete_detection(id):
    with open(DATA_FILE, 'r+') as f:
        data = json.load(f)
        data = [d for d in data if d["id"] != id]
        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=2)

# Pagina principală
@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get('image')
        if not file:
            return "Nu ai încărcat nicio imagine.", 400

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        img = Image.open(file).convert('RGB')
        img.save(filepath, format='JPEG')

        lat, lon = get_gps_from_image(filepath)
        if not is_in_cluj(lat, lon):
            os.remove(filepath)
            return "📍 Locația nu este în municipiul Cluj-Napoca. Detecția a fost ignorată.", 400

        results = model(filepath)
        labels = results.pandas().xyxy[0]['name'].tolist()

        if 'pothole' not in labels:
            return "✅ Imagine încărcată, dar nu s-au detectat gropi.", 200

        detection = {
            "id": uuid.uuid4().hex,
            "filename": filename,
            "location": {"lat": lat, "lon": lon},
            "status": "pending"
        }
        save_detection(detection)
        return "✅ Groapă detectată și salvată cu succes.", 200

    return render_template("interfata.html")

# Pagina admin
@app.route("/admin")
def admin():
    return render_template("admin.html")

# Puncte pentru hartă
@app.route("/api/points")
def api_points():
    with open(DATA_FILE) as f:
        return jsonify(json.load(f))

# Șterge punct
@app.route("/api/delete/<id>", methods=["POST"])
def delete_point(id):
    delete_detection(id)
    return jsonify(success=True)

# Pornire aplicație
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
