-- Feche A e B antes. Execute somente no banco de laboratorio.
BEGIN;
UPDATE lab_fluxo.conta SET saldo=500 WHERE id IN (1, 3);
UPDATE lab_fluxo.conta SET saldo=300 WHERE id=2;
UPDATE lab_fluxo.plantao SET ativo=true;
COMMIT;
-- Confira com conectar(), consultar(conexao) e fechar(conexao) no Python.
