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
    'database': os.getenv('DB_NAME', 'bike_shop_subotica'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password123'),
    'port': int(os.getenv('DB_PORT', 5432))
}

# URL Centralne biciklane iz environment varijable
CENTRAL_URL = os.getenv('CENTRAL_URL', "http://central_app:5000")
GRAD_NAZIV = "Subotica"

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



@app.route('/zaduzenje', methods=['POST'])
def zaduzi_bicikl():
    """
    Zaduženje bicikla
    Expected JSON: {
        "jmbg": "1234567890123",
        "oznaka_bicikla": "NS001",
        "tip_bicikla": "Gradski",
        "datum_zaduzivanja": "2025-09-16"
    }
    """
    try:
        data = request.get_json()
        
        # Validacija podataka
        required_fields = ['jmbg', 'oznaka_bicikla', 'tip_bicikla', 'datum_zaduzivanja']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "success": False,
                    "message": f"Nedostaje obavezan podatak: {field}"
                }), 400
        
        # Validacija datuma
        try:
            datetime.strptime(data['datum_zaduzivanja'], '%Y-%m-%d')
        except ValueError:
            return jsonify({
                "success": False,
                "message": "Neisprava format datuma. Koristiti YYYY-MM-DD"
            }), 400
        
        # Provera da li korisnik može da zaduži bicikl
        check_response = call_centralna_api('/korisnici/proveri-zaduzenje', {'jmbg': data['jmbg']})
        
        if not check_response:
            return jsonify({
                "success": False,
                "message": "Greška pri komunikaciji sa centralnom biciklanom"
            }), 500
        
        if not check_response.get('success'):
            return jsonify(check_response), 404
        
        if not check_response.get('can_rent'):
            return jsonify({
                "success": False,
                "message": "Korisnik je dostigao maksimalan broj zaduženja (2 bicikla)"
            }), 400
        
        # Provera da li je bicikl već zadužen u ovom gradu
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "message": "Greška pri konekciji sa bazom podataka"
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id FROM zaduzenja 
            WHERE oznaka_bicikla = %s AND status = 'aktivan'
        """, (data['oznaka_bicikla'],))
        
        existing_rental = cursor.fetchone()
        
        if existing_rental:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": f"Bicikl {data['oznaka_bicikla']} je već zadužen"
            }), 400
        
        # Registrovanje zaduženja u centralnoj biciklani
        rent_response = call_centralna_api('/korisnici/zaduzi-bicikl', {'jmbg': data['jmbg']})
        
        if not rent_response or not rent_response.get('success'):
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Greška pri registraciji zaduženja u centralnoj biciklani"
            }), 500
        
        # Lokalno čuvanje zaduženja
        cursor.execute("""
            INSERT INTO zaduzenja (korisnik_id, jmbg, ime, prezime, oznaka_bicikla, tip_bicikla, datum_zaduzivanja, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'aktivan')
            RETURNING id
        """, (
            rent_response['user_id'],
            data['jmbg'],
            check_response['ime'],
            check_response['prezime'],
            data['oznaka_bicikla'],
            data['tip_bicikla'],
            data['datum_zaduzivanja']
        ))
        
        rental_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Bicikl {data['oznaka_bicikla']} uspešno zadužen u {GRAD_NAZIV}",
            "rental_id": rental_id,
            "active_rentals": rent_response['active_rentals']
        }), 201
        
    except Exception as e:
        print(f"Greška pri zaduženju bicikla: {e}")
        return jsonify({
            "success": False,
            "message": "Interna greška servera"
        }), 500

@app.route('/razduzivanje', methods=['POST'])
def razduzi_bicikl():
    """
    Razduženje bicikla
    Expected JSON: {
        "oznaka_bicikla": "NS001"
    }
    """
    try:
        data = request.get_json()
        
        if 'oznaka_bicikla' not in data or not data['oznaka_bicikla']:
            return jsonify({
                "success": False,
                "message": "Oznaka bicikla je obavezan parametar"
            }), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "message": "Greška pri konekciji sa bazom podataka"
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Pronalaženje aktivnog zaduženja
        cursor.execute("""
            SELECT id, jmbg, ime, prezime, oznaka_bicikla 
            FROM zaduzenja 
            WHERE oznaka_bicikla = %s AND status = 'aktivan'
        """, (data['oznaka_bicikla'],))
        
        rental = cursor.fetchone()
        
        if not rental:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": f"Aktivno zaduženje za bicikl {data['oznaka_bicikla']} nije pronađeno"
            }), 404
        
        # Razduženje u centralnoj biciklani
        unrent_response = call_centralna_api('/korisnici/razduzi-bicikl', {'jmbg': rental['jmbg']})
        
        if not unrent_response or not unrent_response.get('success'):
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Greška pri razduženju u centralnoj biciklani"
            }), 500
        
        # Lokalno ažuriranje zaduženja
        cursor.execute("""
            UPDATE zaduzenja 
            SET status = 'razduzen', datum_razduzivanja = %s
            WHERE id = %s
        """, (date.today(), rental['id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Bicikl {data['oznaka_bicikla']} uspešno razdužen u {GRAD_NAZIV}",
            "korisnik": f"{rental['ime']} {rental['prezime']}",
            "remaining_rentals": unrent_response['active_rentals']
        }), 200
        
    except Exception as e:
        print(f"Greška pri razduženju bicikla: {e}")
        return jsonify({
            "success": False,
            "message": "Interna greška servera"
        }), 500

@app.route('/zaduzenja', methods=['GET'])
def get_zaduzenja():
    """Vraća sva zaduženja za ovaj grad"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "message": "Greška pri konekciji sa bazom podataka"
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Filtiranje po statusu (opciono)
        status_filter = request.args.get('status', None)
        
        if status_filter:
            cursor.execute("""
                SELECT id, jmbg, ime, prezime, oznaka_bicikla, tip_bicikla, 
                       datum_zaduzivanja, datum_razduzivanja, status, created_at
                FROM zaduzenja 
                WHERE status = %s
                ORDER BY created_at DESC
            """, (status_filter,))
        else:
            cursor.execute("""
                SELECT id, jmbg, ime, prezime, oznaka_bicikla, tip_bicikla, 
                       datum_zaduzivanja, datum_razduzivanja, status, created_at
                FROM zaduzenja 
                ORDER BY created_at DESC
            """)
        
        zaduzenja = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Konvertovanje date objekata u string
        result = []
        for zaduzenje in zaduzenja:
            z = dict(zaduzenje)
            if z['datum_zaduzivanja']:
                z['datum_zaduzivanja'] = z['datum_zaduzivanja'].strftime('%Y-%m-%d')
            if z['datum_razduzivanja']:
                z['datum_razduzivanja'] = z['datum_razduzivanja'].strftime('%Y-%m-%d')
            result.append(z)
        
        return jsonify({
            "success": True,
            "grad": GRAD_NAZIV,
            "zaduzenja": result
        }), 200
        
    except Exception as e:
        print(f"Greška pri dohvatanju zaduženja: {e}")
        return jsonify({
            "success": False,
            "message": "Interna greška servera"
        }), 500



if __name__ == '__main__':
    print("Pokretanje Bike Shop Novi Sad...")
    print("Endpoints:")
    print("GET  /health")
    print("POST /registracija")
    
    app.run(host='0.0.0.0', port=5003, debug=True)