# pothole-app
 # Pothole Detection App

## Descriere
Aplicație web pentru detectarea şi marcare a gropilor pe o hartă.  
Utilizează Flask pentru backend, YOLO (server Colab) pentru inference, Leaflet.js pentru hartă şi Geopy pentru reverse-geocoding.

## Funcționalități
- Încărcare imagine cu coordonate EXIF GPS  
- Detecție YOLO (model pe Colab)  
- Pagină “Nicio groapă detectată” cu buton de revenire şi forţare pin dummy  
- Hartă interactivă (Leaflet) ce afișează toate detecțiile  
- Admin page cu gallery, adresă (reverse-geocoding) şi buton de ștergere  
- API JSON pentru puncte (`/api/points`) și ştergere (`/api/delete/<id>`)

## Cerințe  
- Python ≥ 3.8  
- Pip  

## Instalare

1. Clonează repository:
    ```bash
    git clone https://github.com/username/pothole-app.git
    cd pothole-app
    ```
2. Crează şi activează un mediu virtual:
    ```bash
    python3 -m venv venv
    source venv/bin/activate    # Windows: venv\Scripts\activate
    ```
3. Instalează dependențele:
    ```bash
    pip install -r requirements.txt
    ```

## Configurare
- În `app.py` modifică `COLAB_URL` cu endpoint-ul tău de detecție YOLO (ngrok/alt tunnel).
- Asigură-te că directoarele există şi sunt scriibile:
  ```text
  static/uploads/
  data/ (conţine detections.json)
  templates/
