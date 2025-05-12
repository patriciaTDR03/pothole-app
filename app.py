# app.py (versiune actualizată - interacțiune Colab pentru detecție)
from flask import Flask, render_template, request, redirect, url_for, jsonify
from PIL import Image
import os, uuid, json, piexif
import requests

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = 'data/detections.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# URL-ul serverului Colab pentru detecție
COLAB_URL = 'https://<COLAB_SERVER_URL>/detect'

# Funcție pentru extragerea coordonatelor GPS din EXIF

def get_gps_from_image(img_path):
    try:
        exif_dict = piexif.load(img_path)
        gps = exif_dict.get("GPS")
        if gps and 2 in gps and 4 in gps:
            lat = gps[2]
            lon = gps[4]
            lat_deg = lat[0][0] / lat[0][1] + lat[1][0] / lat[1][1] / 60 + lat[2][0] / lat[2][1] / 3600
            lon_deg = lon[0][0] / lon[0][1] + lon[1][0] / lon[1][1] / 60 + lon[2][0] / lon[2][1] / 3600
            if gps.get(1) == b'S': lat_deg *= -1
            if gps.get(3) == b'W': lon_deg *= -1
            return lat_deg, lon_deg
    except Exception as e:
        print(f"Eroare EXIF: {e}")
    return None, None


# Funcție pentru verificarea coordonatelor Cluj

def is_in_cluj(lat, lon):
    return lat and lon and (46.5 <= lat <= 47.1) and (23.4 <= lon <= 23.8)


# Endpoint principal pentru upload și detecție

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get('image')
        if not file:
            return "Nu ai încărcat nicio imagine.", 400

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        lat, lon = get_gps_from_image(filepath)
        if not is_in_cluj(lat, lon):
            os.remove(filepath)
            return render_template("not_in.html"), 400

        # Trimitere către Colab pentru detecție
        try:
            with open(filepath, 'rb') as img_file:
                response = requests.post(COLAB_URL, files={'image': img_file})
                result = response.json()

            if result.get("status") == "success":
                detection = {
                    "id": uuid.uuid4().hex,
                    "filename": filename,
                    "location": {"lat": lat, "lon": lon},
                    "status": "pending"
                }
                save_detection(detection)
                return "✅ Groapă detectată și salvată cu succes.", 200
            else:
                return result.get("message", "Eroare la detecție."), 500
        except Exception as e:
            print(f"Eroare la cererea către Colab: {e}")
            return "Eroare la cererea către serverul Colab.", 500

    return render_template("interfata.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/api/points")
def api_points():
    with open(DATA_FILE) as f:
        return jsonify(json.load(f))

@app.route("/api/delete/<id>", methods=["POST"])
def delete_point(id):
    delete_detection(id)
    return jsonify(success=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
