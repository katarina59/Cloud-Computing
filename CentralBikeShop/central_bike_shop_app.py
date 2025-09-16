from flask import Flask, request, jsonify # type: ignore
import psycopg2 # type: ignore
from psycopg2.extras import RealDictCursor # type: ignore
import os
from datetime import datetime

app = Flask(__name__)

# Database konfiguracija iz environment varijabli
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'central_bike_shop'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password123'),
    'port': int(os.getenv('DB_PORT', 5432))
}

def get_db_connection():
    """Kreiranje konekcije sa bazom podataka"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Greška pri konekciji sa bazom: {e}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "OK", "service": "Central Bike Shop"}), 200

@app.route('/korisnici/registracija', methods=['POST'])
def registruj_korisnika():
    """
    Registracija novog korisnika
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
        
        # Validacija JMBG (mora biti 13 karaktera)
        if len(data['jmbg']) != 13 or not data['jmbg'].isdigit():
            return jsonify({
                "success": False,
                "message": "JMBG mora imati tačno 13 cifara"
            }), 400
            
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "message": "Greška pri konekciji sa bazom podataka"
            }), 500
            
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Provera da li korisnik već postoji
        cursor.execute("SELECT id FROM korisnici WHERE jmbg = %s", (data['jmbg'],))
        existing_user = cursor.fetchone()
        
        if existing_user:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Korisnik sa datim JMBG već postoji"
            }), 409
        
        # Registracija novog korisnika
        cursor.execute("""
            INSERT INTO korisnici (jmbg, ime, prezime, adresa, broj_aktivnih_bicikala)
            VALUES (%s, %s, %s, %s, 0)
            RETURNING id
        """, (data['jmbg'], data['ime'], data['prezime'], data['adresa']))
        
        user_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Korisnik uspešno registrovan",
            "user_id": user_id
        }), 201
        
    except Exception as e:
        print(f"Greška pri registraciji: {e}")
        return jsonify({
            "success": False,
            "message": "Interna greška servera"
        }), 500

@app.route('/korisnici/proveri-zaduzenje', methods=['POST'])
def proveri_zaduzenje():
    """
    Provera da li korisnik može da zaduži bicikl (maksimalno 2)
    Expected JSON: {
        "jmbg": "1234567890123"
    }
    """
    try:
        data = request.get_json()
        
        if 'jmbg' not in data:
            return jsonify({
                "success": False,
                "message": "JMBG je obavezan parametar"
            }), 400
            
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "message": "Greška pri konekciji sa bazom podataka"
            }), 500
            
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Pronalaženje korisnika i brojanje aktivnih bicikala
        cursor.execute("""
            SELECT id, ime, prezime, broj_aktivnih_bicikala 
            FROM korisnici 
            WHERE jmbg = %s
        """, (data['jmbg'],))
        
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Korisnik nije registrovan"
            }), 404
        
        # Provera da li može da zaduži (maksimalno 2 bicikla)
        can_rent = user['broj_aktivnih_bicikala'] < 2
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "can_rent": can_rent,
            "current_rentals": user['broj_aktivnih_bicikala'],
            "user_id": user['id'],
            "ime": user['ime'],
            "prezime": user['prezime']
        }), 200
        
    except Exception as e:
        print(f"Greška pri proveri zaduženja: {e}")
        return jsonify({
            "success": False,
            "message": "Interna greška servera"
        }), 500

@app.route('/korisnici/zaduzi-bicikl', methods=['POST'])
def zaduzi_bicikl():
    """
    Registrovanje novog zaduženja bicikla
    Expected JSON: {
        "jmbg": "1234567890123"
    }
    """
    try:
        data = request.get_json()
        
        if 'jmbg' not in data:
            return jsonify({
                "success": False,
                "message": "JMBG je obavezan parametar"
            }), 400
            
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "message": "Greška pri konekciji sa bazom podataka"
            }), 500
            
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Ažuriranje broja aktivnih bicikala
        cursor.execute("""
            UPDATE korisnici 
            SET broj_aktivnih_bicikala = broj_aktivnih_bicikala + 1
            WHERE jmbg = %s AND broj_aktivnih_bicikala < 2
            RETURNING id, broj_aktivnih_bicikala
        """, (data['jmbg'],))
        
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Korisnik nije pronađen ili je dostigao maksimalan broj zaduženja"
            }), 400
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Zaduženje uspešno registrovano",
            "user_id": result['id'],
            "active_rentals": result['broj_aktivnih_bicikala']
        }), 200
        
    except Exception as e:
        print(f"Greška pri zaduženju bicikla: {e}")
        return jsonify({
            "success": False,
            "message": "Interna greška servera"
        }), 500

@app.route('/korisnici/razduzi-bicikl', methods=['POST'])
def razduzi_bicikl():
    """
    Razduženje bicikla - smanjuje broj aktivnih zaduženja
    Expected JSON: {
        "jmbg": "1234567890123"
    }
    """
    try:
        data = request.get_json()
        
        if 'jmbg' not in data:
            return jsonify({
                "success": False,
                "message": "JMBG je obavezan parametar"
            }), 400
            
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "message": "Greška pri konekciji sa bazom podataka"
            }), 500
            
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Smanjenje broja aktivnih bicikala
        cursor.execute("""
            UPDATE korisnici 
            SET broj_aktivnih_bicikala = broj_aktivnih_bicikala - 1
            WHERE jmbg = %s AND broj_aktivnih_bicikala > 0
            RETURNING id, broj_aktivnih_bicikala
        """, (data['jmbg'],))
        
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Korisnik nije pronađen ili nema aktivnih zaduženja"
            }), 400
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Razduženje uspešno registrovano",
            "user_id": result['id'],
            "active_rentals": result['broj_aktivnih_bicikala']
        }), 200
        
    except Exception as e:
        print(f"Greška pri razduženju bicikla: {e}")
        return jsonify({
            "success": False,
            "message": "Interna greška servera"
        }), 500

@app.route('/korisnici', methods=['GET'])
def get_all_users():
    """Vraća sve registrovane korisnike"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "message": "Greška pri konekciji sa bazom podataka"
            }), 500
            
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, jmbg, ime, prezime, adresa, broj_aktivnih_bicikala, created_at
            FROM korisnici 
            ORDER BY created_at DESC
        """)
        
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "users": [dict(user) for user in users]
        }), 200
        
    except Exception as e:
        print(f"Greška pri dohvatanju korisnika: {e}")
        return jsonify({
            "success": False,
            "message": "Interna greška servera"
        }), 500

if __name__ == '__main__':
    print("Pokretanje Centralne Biciklane...")
    print("Endpoints:")
    print("POST /korisnici/registracija")
    print("POST /korisnici/proveri-zaduzenje") 
    print("POST /korisnici/zaduzi-bicikl")
    print("POST /korisnici/razduzi-bicikl")
    print("GET  /korisnici")
    print("GET  /health")
    
    app.run(host='0.0.0.0', port=5000, debug=True)