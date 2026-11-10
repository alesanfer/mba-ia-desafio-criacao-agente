"""Leitura e gravação de reservas e visitantes.

Toda função que toca dados de um morador recebe o apartamento como parâmetro
explícito. Quem chama (tools e rotas de verificação) é que decide de onde ele
vem; nas tools, sempre do state da sessão.
"""

import secrets
import sqlite3
import unicodedata
from datetime import date

from app.db import carregar_json, conectar

APARTAMENTOS = {a["numero"] for a in carregar_json("apartamentos.json")}
AREAS = {a["id"]: a for a in carregar_json("areas.json")}


def _sem_acento(texto: str) -> str:
  nfkd = unicodedata.normalize("NFKD", texto.strip().lower())
  return "".join(c for c in nfkd if not unicodedata.combining(c))


def resolver_area(texto: str) -> dict | None:
  """Aceita o id ou o nome da área e devolve o registro, ou None."""
  alvo = _sem_acento(texto).replace(" ", "-")
  for area in AREAS.values():
    if alvo in (area["id"], _sem_acento(area["nome"]).replace(" ", "-")):
      return area
  return None


def data_valida(texto: str) -> bool:
  try:
    return len(texto) == 10 and date.fromisoformat(texto).isoformat() == texto
  except (TypeError, ValueError):
    return False


# --- Reservas ---------------------------------------------------------------


def listar_reservas(apartamento: str) -> list[dict]:
  with conectar() as conn:
    linhas = conn.execute(
        "SELECT codigo, area, data FROM reservas"
        " WHERE apartamento = ? AND status = 'ativa' ORDER BY data, area",
        (apartamento,),
    ).fetchall()
  return [dict(linha) for linha in linhas]


def data_ocupada(area_id: str, data: str) -> bool:
  """Só informa se a data está ocupada, nunca por quem."""
  with conectar() as conn:
    return (
        conn.execute(
            "SELECT 1 FROM reservas"
            " WHERE area = ? AND data = ? AND status = 'ativa'",
            (area_id, data),
        ).fetchone()
        is not None
    )


def criar_reserva(apartamento: str, area_id: str, data: str) -> str | None:
  """Grava a reserva e devolve o código, ou None se a data já está ocupada.

  A exclusividade não depende de conferência prévia: o INSERT esbarra no índice
  único parcial (area, data) das reservas ativas. O código é chave primária da
  tabela, que guarda também as canceladas, então nunca se repete.
  """
  while True:
    codigo = f"RSV-{secrets.randbelow(900000) + 100000}"
    try:
      with conectar() as conn:
        conn.execute(
            "INSERT INTO reservas (codigo, apartamento, area, data)"
            " VALUES (?, ?, ?, ?)",
            (codigo, apartamento, area_id, data),
        )
      return codigo
    except sqlite3.IntegrityError as erro:
      if "reservas.codigo" in str(erro):
        continue  # colisão de código: sorteia outro
      return None  # área e data já têm reserva ativa


def cancelar_reserva(
    apartamento: str, *, codigo: str = "", area_id: str = "", data: str = ""
) -> dict | None:
  """Cancela uma reserva ativa do apartamento, por código ou por área e data.

  O filtro por apartamento está no próprio UPDATE: reserva de outro apartamento
  simplesmente não é encontrada.
  """
  with conectar() as conn:
    linha = conn.execute(
        "UPDATE reservas SET status = 'cancelada'"
        " WHERE apartamento = ? AND status = 'ativa'"
        " AND (codigo = ? OR (area = ? AND data = ?))"
        " RETURNING codigo, area, data",
        (apartamento, codigo.strip().upper(), area_id, data),
    ).fetchone()
  return dict(linha) if linha else None


# --- Visitantes -------------------------------------------------------------


def listar_visitantes(apartamento: str) -> list[dict]:
  with conectar() as conn:
    linhas = conn.execute(
        "SELECT nome, data FROM visitantes"
        " WHERE apartamento = ? ORDER BY data, nome",
        (apartamento,),
    ).fetchall()
  return [dict(linha) for linha in linhas]


def autorizar_visitante(apartamento: str, nome: str, data: str) -> None:
  with conectar() as conn:
    conn.execute(
        "INSERT OR IGNORE INTO visitantes (apartamento, nome, data)"
        " VALUES (?, ?, ?)",
        (apartamento, nome, data),
    )
