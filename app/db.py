"""Banco SQLite do condomínio: schema, conexão e carga dos dados iniciais."""

import json
import sqlite3
from contextlib import contextmanager

from app.config import DB_CONDOMINIO, DB_SESSOES, DIR_DADOS, DIR_VAR

SCHEMA = """
CREATE TABLE IF NOT EXISTS reservas (
    codigo      TEXT PRIMARY KEY,
    apartamento TEXT NOT NULL,
    area        TEXT NOT NULL,
    data        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'ativa'
                CHECK (status IN ('ativa', 'cancelada'))
);

-- Garantia 5: no máximo uma reserva ATIVA por área e data. O próprio banco
-- recusa a segunda gravação, mesmo que duas cheguem no mesmo instante.
CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_ativa
    ON reservas (area, data) WHERE status = 'ativa';

CREATE TABLE IF NOT EXISTS visitantes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    apartamento TEXT NOT NULL,
    nome        TEXT NOT NULL,
    data        TEXT NOT NULL,
    UNIQUE (apartamento, nome, data)
);
"""

TABELAS_SESSAO = ("events", "sessions", "user_states", "app_states")


def carregar_json(nome: str) -> list[dict]:
  return json.loads((DIR_DADOS / nome).read_text(encoding="utf-8"))


@contextmanager
def conectar():
  """Abre uma conexão; confirma a transação ao sair ou desfaz em caso de erro."""
  DIR_VAR.mkdir(exist_ok=True)
  conn = sqlite3.connect(DB_CONDOMINIO, timeout=15)
  conn.row_factory = sqlite3.Row
  try:
    conn.execute("PRAGMA journal_mode=WAL")
    with conn:
      yield conn
  finally:
    conn.close()


def _carregar_dados_iniciais(conn: sqlite3.Connection) -> None:
  conn.execute("DELETE FROM reservas")
  conn.execute("DELETE FROM visitantes")
  conn.executemany(
      "INSERT INTO reservas (codigo, apartamento, area, data)"
      " VALUES (:codigo, :apartamento, :area, :data)",
      carregar_json("reservas.json"),
  )
  conn.executemany(
      "INSERT INTO visitantes (apartamento, nome, data)"
      " VALUES (:apartamento, :nome, :data)",
      carregar_json("visitantes.json"),
  )


def inicializar() -> None:
  """Cria o banco com os dados iniciais se ele ainda não existir."""
  with conectar() as conn:
    existe = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'reservas'"
    ).fetchone()
    conn.executescript(SCHEMA)
    if not existe:
      _carregar_dados_iniciais(conn)


def restaurar() -> None:
  """Volta reservas e visitantes ao estado de dados/ e apaga as sessões."""
  with conectar() as conn:
    conn.executescript(SCHEMA)
    _carregar_dados_iniciais(conn)

  if DB_SESSOES.exists():
    conn = sqlite3.connect(DB_SESSOES, timeout=15)
    try:
      with conn:
        existentes = {
            linha[0]
            for linha in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        for tabela in TABELAS_SESSAO:
          if tabela in existentes:
            conn.execute(f"DELETE FROM {tabela}")
    finally:
      conn.close()
