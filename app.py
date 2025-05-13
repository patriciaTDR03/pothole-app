# app.py (versiune finală cu debugging Colab și fallback dummy)
from flask import Flask, render_template, request, jsonify
from PIL import Image
import os, uuid, json, piexif, requests

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = 'data/detections.json'
COLAB_URL = 'https://865b-35-247-42-51.ngrok-free.app/detect'

# Asigurăm directorii și fișierul de date
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# Funcții auxiliare

def get_gps_from_image(img_path):
    try:
        exif_dict = piexif.load(img_path)
        gps = exif_dict.get('GPS')
        if gps and 2 in gps and 4 in gps:
            lat = gps[2]; lon = gps[4]
            lat_deg = lat[0][0]/lat[0][1] + lat[1][0]/lat[1][1]/60 + lat[2][0]/lat[2][1]/3600
            lon_deg = lon[0][0]/lon[0][1] + lon[1][0]/lon[1][1]/60 + lon[2][0]/lon[2][1]/3600
            if gps.get(1) == b'S': lat_deg *= -1
            if gps.get(3) == b'W': lon_deg *= -1
            return lat_deg, lon_deg
    except Exception as e:
        app.logger.error(f'Eroare EXIF: {e}')
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
        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=2)

# Ruta principală
@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('image')
        if not file:
            return 'Nu ai încărcat nicio imagine.', 400

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        lat, lon = get_gps_from_image(filepath)
        if not is_in_cluj(lat, lon):
            os.remove(filepath)
            return render_template('not_in.html'), 400

        # Debug: afișăm date despre imagine
        app.logger.info(f'Primit imagine: {filename} cu lat={lat}, lon={lon}')

        # Apel către Colab
        try:
            with open(filepath, 'rb') as img_file:
                resp = requests.post(COLAB_URL, files={'image': img_file}, timeout=15)
            app.logger.info(f'Colab status: {resp.status_code}')
            app.logger.info(f'Colab raw: {resp.text}')
            if resp.status_code != 200:
                app.logger.error(f'Colab error {resp.status_code}: {resp.text}')
                return '❌ Serverul de detecție a răspuns cu eroare.', 502

            result = resp.json()
            app.logger.info(f'Colab JSON: {result}')

            if result.get('status') == 'success' and result.get('message') == 'Groapă detectată.':
                # Detecție reală
                entry = {
                    'id': uuid.uuid4().hex,
                    'filename': filename,
                    'location': {'lat': lat, 'lon': lon},
                    'status': 'pending'
                }
                save_detection(entry)
                return '✅ Groapă detectată și salvată cu succes.', 200
            else:
                # Fallback dummy detection
                entry = {
                    'id': uuid.uuid4().hex,
                    'filename': filename,
                    'location': {'lat': lat, 'lon': lon},
                    'status': 'dummy'
                }
                save_detection(entry)
                return '⚠️ Nu s-a detectat groapă, dar am adăugat un pin dummy pentru test.', 200

        except requests.Timeout:
            app.logger.error('Timeout la cererea către Colab')
            return '⏰ Timeout la serverul de detecție.', 504
        except Exception as e:
            app.logger.error(f'Eroare la cererea către Colab: {e}')
            return '❌ Eroare internă în comunicarea cu serverul de detecție.', 502

    return render_template('interfata.html')

# Admin și API
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
