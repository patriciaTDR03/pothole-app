# app.py (versiune actualizată - interacțiune Colab pentru detecție)
from flask import Flask, render_template, request, redirect, url_for, jsonify
from PIL import Image
import os, uuid, json, piexif, requests

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = 'data/detections.json'
# Asigurăm directorii necesari
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

# Inițializăm fișierul de date dacă nu există
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# URL-ul serverului Colab pentru detecție
COLAB_URL = 'https://7840-35-247-42-51.ngrok-free.app'

# Extrage coordonatele GPS din EXIF

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

# Verifică dacă coordonatele sunt în zona Cluj

def is_in_cluj(lat, lon):
    return lat and lon and (46.5 <= lat <= 47.1) and (23.4 <= lon <= 23.8)

# Salvează o detecție în fișierul JSON

def save_detection(entry):
    with open(DATA_FILE, 'r+') as f:
        data = json.load(f)
        data.append(entry)
        f.seek(0)
        json.dump(data, f, indent=2)

# Șterge o detecție după id

def delete_detection(id):
    with open(DATA_FILE, 'r+') as f:
        data = json.load(f)
        data = [d for d in data if d['id'] != id]
        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=2)

# Ruta principală pentru upload și trimitere spre Colab

@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('image')
        if not file:
            return "Nu ai încărcat nicio imagine.", 400

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        lat, lon = get_gps_from_image(filepath)
        if not is_in_cluj(lat, lon):
            os.remove(filepath)
            return render_template('not_in.html'), 400

        # Trimitere către serverul Colab
        try:
            with open(filepath, 'rb') as img_file:
                resp = requests.post(COLAB_URL, files={'image': img_file})
                result = resp.json()

            if result.get('status') == 'success' and 'Groapă detectată' in result.get('message', ''):
                entry = {
                    'id': uuid.uuid4().hex,
                    'filename': filename,
                    'location': {'lat': lat, 'lon': lon},
                    'status': 'pending'
                }
                save_detection(entry)
                return '✅ Groapă detectată și salvată cu succes.', 200
            else:
                return result.get('message', 'Eroare la detecție.'), 200
        except Exception as e:
            print(f"Eroare la cererea către Colab: {e}")
            return "Eroare la cererea către serverul Colab.", 500

    return render_template('interfata.html')

# Pagina de administrare

@app.route('/admin')
def admin():
    return render_template('admin.html')

# API pentru preluarea punctelor detectate

@app.route('/api/points')
def api_points():
    with open(DATA_FILE) as f:
        return jsonify(json.load(f))

# API pentru ștergerea unui punct

@app.route('/api/delete/<id>', methods=['POST'])
def delete_point(id):
    delete_detection(id)
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
