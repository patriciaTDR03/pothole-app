# app.py (versiune actualizată – interacțiune Colab cu timeout, status check și logare)
from flask import Flask, render_template, request, jsonify
from PIL import Image
import os, uuid, json, piexif, requests

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = 'data/detections.json'
COLAB_URL = 'https://7840-35-247-42-51.ngrok-free.app/detect'

# Asigurăm directorii și fișierul de date
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

def get_gps_from_image(img_path):
    try:
        exif_dict = piexif.load(img_path)
        gps = exif_dict.get("GPS")
        if gps and 2 in gps and 4 in gps:
            lat = gps[2]; lon = gps[4]
            lat_deg = lat[0][0]/lat[0][1] + lat[1][0]/lat[1][1]/60 + lat[2][0]/lat[2][1]/3600
            lon_deg = lon[0][0]/lon[0][1] + lon[1][0]/lon[1][1]/60 + lon[2][0]/lon[2][1]/3600
            if gps.get(1) == b'S': lat_deg *= -1
            if gps.get(3) == b'W': lon_deg *= -1
            return lat_deg, lon_deg
    except Exception as e:
        app.logger.error(f"Eroare EXIF: {e}")
    return None, None

def is_in_cluj(lat, lon):
    return lat and lon and (46.5 <= lat <= 47.1) and (23.4 <= lon <= 23.8)

def save_detection(entry):
    with open(DATA_FILE, 'r+') as f:
        data = json.load(f)
        data.append(entry)
        f.seek(0)
        json.dump(data, f, indent=2)

def delete_detection(id):
    with open(DATA_FILE, 'r+') as f:
        data = json.load(f)
        data = [d for d in data if d['id'] != id]
        f.seek(0); f.truncate()
        json.dump(data, f, indent=2)

@app.route('/', methods=['GET', 'POST'])
     if request.method == 'POST':
         # … save the file, extract GPS, etc.

         # Trimitere către serverul Colab
         try:
-            with open(filepath, 'rb') as img_file:
-                resp = requests.post(COLAB_URL, files={'image': img_file})
-                result = resp.json()
+            with open(filepath, 'rb') as img_file:
+                resp = requests.post(COLAB_URL, files={'image': img_file})
+            # --- DEBUG: dump everything we got back:
+            print("🔁 Colab response code:", resp.status_code)
+            print("🔁 Colab raw text   :", resp.text)
+            try:
+                result = resp.json()
+            except Exception:
+                # If parsing fails, show an error
+                print("❌ Could not parse JSON from Colab")
+                return "Eroare la parse-uirea răspunsului de la server.", 500

-            if result.get('status') == 'success' and 'Groapă detectată' in result.get('message', ''):
+            # --- DEBUG: show the parsed dict
+            print("🔁 Colab JSON       :", result)
+
+            # decide success by the exact flag, not by substring:
+            if result.get('status') == 'success' and result.get('message') == 'Groapă detectată.':
                 entry = {
                     'id': uuid.uuid4().hex,
                     'filename': filename,
                     'location': {'lat': lat, 'lon': lon},
                     'status': 'pending'
                 }
                 save_detection(entry)
                 return '✅ Groapă detectată și salvată cu succes.', 200
             else:
-                return result.get('message', 'Eroare la detecție.'), 200
+                # show whatever message the Colab server gave you
+                return result.get('message', 'Eroare la detecție.'), 400
         except Exception as e:
             print(f"Eroare la cererea către Colab: {e}")
             return "Eroare la cererea către serverul Colab.", 500
    return render_template('interfata.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/points')
def api_points():
    with open(DATA_FILE) as f:
        return jsonify(json.load(f))

@app.route('/api/delete/<id>', methods=['POST'])
def delete_point(id):
    delete_detection(id)
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
