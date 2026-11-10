"""Modelo Gemini compartilhado pelos agentes."""

from google.adk.models import Gemini
from google.genai import types

from app import config

# Repete a chamada quando o Gemini responde com sobrecarga ou limite de taxa,
# em vez de derrubar a mensagem do morador na primeira falha.
MODELO = Gemini(
    model=config.MODELO,
    retry_options=types.HttpRetryOptions(
        attempts=5,
        initial_delay=2,
        max_delay=30,
        http_status_codes=[429, 500, 502, 503, 504],
    ),
)
