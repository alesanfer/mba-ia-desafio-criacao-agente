"""Caminhos e configuração lidos do ambiente."""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

DIR_DADOS = RAIZ / "dados"
DIR_VAR = RAIZ / "var"
DB_CONDOMINIO = DIR_VAR / "condominio.db"
DB_SESSOES = DIR_VAR / "sessoes.db"

NOME_APP = "residencial_aurora"
# Cada sessão pertence a um apartamento (guardado no state); o user_id do ADK
# é fixo porque a API localiza a sessão só pelo session_id.
USER_ID = "morador"

MODELO = os.getenv("MODELO_GEMINI") or "gemini-3.5-flash"
