"""Comando de restauração: uv run python -m app.restaurar"""

from app import db

if __name__ == "__main__":
  db.restaurar()
  print("Dados restaurados: reservas e visitantes iniciais, sessões apagadas.")
