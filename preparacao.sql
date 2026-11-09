-- Use somente banco exclusivo de laboratorio. Nao apaga esquema existente.
BEGIN;
CREATE SCHEMA lab_fluxo;
CREATE TABLE lab_fluxo.conta (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    saldo INTEGER NOT NULL CHECK (saldo >= 0)
);
INSERT INTO lab_fluxo.conta VALUES
    (1, 'Ana', 500), (2, 'Bruno', 300), (3, 'Carla', 500);
CREATE TABLE lab_fluxo.plantao (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    ativo BOOLEAN NOT NULL
);
INSERT INTO lab_fluxo.plantao VALUES (1, 'Ana', true), (2, 'Bruno', true);
COMMIT;
