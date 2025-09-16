import os
from flask import Flask, request, jsonify # type: ignore
import psycopg2 # type: ignore
from psycopg2.extras import RealDictCursor # type: ignore
import requests
from datetime import datetime, date
import json

app = Flask(__name__)

# Database konfiguracija iz environment varijabli
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'bike_shop_novi_sad'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password123'),
    'port': int(os.getenv('DB_PORT', 5432))
}

# URL Centralne biciklane iz environment varijable
CENTRAL_URL = os.getenv('CENTRAL_URL', "http://central_app:5000")
GRAD_NAZIV = "Kragujevac"

def get_db_connection():
    """Kreiranje konekcije sa bazom podataka"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Greška pri konekciji sa bazom: {e}")
        return None

def call_centralna_api(endpoint, data=None, method='POST'):
    """Helper funkcija za pozivanje API-ja centralne biciklane"""
    try:
        url = f"{CENTRAL_URL}{endpoint}"
        
        if method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        elif method == 'GET':
            response = requests.get(url, timeout=10)
        else:
            return None
            
        return response.json() if response.status_code in [200, 201, 400, 404, 409] else None
        
    except requests.exceptions.RequestException as e:
        print(f"Greška pri pozivu centralne API: {e}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "OK", "service": f"Bike shop {GRAD_NAZIV}"}), 200

@app.route('/registracija', methods=['POST'])
def registruj_korisnika():
    """
    Registracija novog korisnika preko centralne biciklane
    Expected JSON: {
        "jmbg": "1234567890123",
        "ime": "Marko",
        "prezime": "Petrovic", 
        "adresa": "Bulevar Oslobođenja 1, Novi Sad"
    }
    """
    try:
        data = request.get_json()
        
        # Validacija podataka
        required_fields = ['jmbg', 'ime', 'prezime', 'adresa']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "success": False,
                    "message": f"Nedostaje obavezan podatak: {field}"
                }), 400
        
        # Poziv centralne biciklane za registraciju
        response = call_centralna_api('/korisnici/registracija', data)
        
        if not response:
            return jsonify({
                "success": False,
                "message": "Greška pri komunikaciji sa centralnom biciklanom"
            }), 500
        
        if response.get('success'):
            return jsonify({
                "success": True,
                "message": f"Korisnik uspešno registrovan u {GRAD_NAZIV}",
                "user_id": response.get('user_id')
            }), 201
        else:
            return jsonify(response), 409
            
    except Exception as e:
        print(f"Greška pri registraciji: {e}")
        return jsonify({
            "success": False,
            "message": "Interna greška servera"
        }), 500


if __name__ == '__main__':
    print("Pokretanje Bike Shop Novi Sad...")
    print("Endpoints:")
    print("GET  /health")
    print("POST /registracija")
    
    app.run(host='0.0.0.0', port=5002, debug=True)
