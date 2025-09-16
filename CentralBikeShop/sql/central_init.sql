-- Tabela registrovanih korisnika
CREATE TABLE korisnici (
    id SERIAL PRIMARY KEY,
    jmbg VARCHAR(13) UNIQUE NOT NULL,
    ime VARCHAR(100) NOT NULL,
    prezime VARCHAR(100) NOT NULL,
    adresa TEXT NOT NULL,
    broj_aktivnih_bicikala INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indeksi za bolje performanse
CREATE INDEX idx_korisnici_jmbg ON korisnici(jmbg);
CREATE INDEX idx_korisnici_created_at ON korisnici(created_at);

-- Test podaci
INSERT INTO korisnici (jmbg, ime, prezime, adresa, broj_aktivnih_bicikala) VALUES 
('1234567890123', 'Marko', 'Petrović', 'Bulevar Oslobođenja 1, Novi Sad', 0),
('9876543210987', 'Ana', 'Jovanović', 'Zmaj Jovina 15, Novi Sad', 1),
('1122334455667', 'Stefan', 'Nikolić', 'Kralja Petra 22, Subotica', 2),
('5555666677778', 'Milica', 'Stojanović', 'Svetozara Markovića 5, Kragujevac', 0),
('9999888877776', 'Nikola', 'Milosavljević', 'Kneza Miloša 12, Kragujevac', 1);