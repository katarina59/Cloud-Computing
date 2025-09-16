
-- Tabela lokalnih zaduženja
CREATE TABLE zaduzenja (
    id SERIAL PRIMARY KEY,
    korisnik_id INTEGER NOT NULL, -- ID iz centralne baze
    jmbg VARCHAR(13) NOT NULL,
    ime VARCHAR(100) NOT NULL,
    prezime VARCHAR(100) NOT NULL,
    oznaka_bicikla VARCHAR(50) NOT NULL,
    tip_bicikla VARCHAR(50) NOT NULL,
    datum_zaduzivanja DATE NOT NULL,
    datum_razduzivanja DATE NULL,
    status VARCHAR(20) DEFAULT 'aktivan',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indeksi za bolje performanse
CREATE INDEX idx_zaduzenja_jmbg ON zaduzenja(jmbg);
CREATE INDEX idx_zaduzenja_oznaka_bicikla ON zaduzenja(oznaka_bicikla);
CREATE INDEX idx_zaduzenja_status ON zaduzenja(status);
CREATE INDEX idx_zaduzenja_created_at ON zaduzenja(created_at);

-- Constraint za jedinstvene aktivne bicikle
CREATE UNIQUE INDEX idx_unique_active_bike 
ON zaduzenja(oznaka_bicikla) 
WHERE status = 'aktivan';

-- Test podaci (različiti za svaki grad)
-- Ovi podaci će biti dodani preko aplikacije ili ručno po potrebi