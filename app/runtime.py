"""Runtime do ADK: App, Runner e sessões persistidas em SQLite."""

from google.adk.apps import App, ResumabilityConfig
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import Session
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai import types

from app.agentes.principal import agente_principal
from app.config import DB_SESSOES, DIR_VAR, NOME_APP, USER_ID
from app.tools.sessao import CHAVE_APARTAMENTO

DIR_VAR.mkdir(exist_ok=True)

# Garantia 3: sessões e eventos ficam em arquivo, não em memória.
servico_sessoes = SqliteSessionService(str(DB_SESSOES))

aplicacao = App(
    name=NOME_APP,
    root_agent=agente_principal,
    # Permite pausar na confirmação e retomar depois, inclusive após reinício.
    resumability_config=ResumabilityConfig(is_resumable=True),
)

runner = Runner(app=aplicacao, session_service=servico_sessoes)


async def criar_sessao(apartamento: str) -> Session:
  """Garantia 2: único ponto em que o apartamento da sessão é definido."""
  return await servico_sessoes.create_session(
      app_name=NOME_APP,
      user_id=USER_ID,
      state={CHAVE_APARTAMENTO: apartamento},
  )


async def buscar_sessao(session_id: str) -> Session | None:
  return await servico_sessoes.get_session(
      app_name=NOME_APP, user_id=USER_ID, session_id=session_id
  )


def _texto(evento: Event) -> str:
  if evento.author == "user" or evento.partial or not evento.content:
    return ""
  return "".join(
      parte.text
      for parte in evento.content.parts or []
      if parte.text and not parte.thought
  )


async def executar(session_id: str, mensagem: types.Content) -> str:
  """Roda o agente com uma mensagem e devolve o texto respondido ao morador."""
  textos = []
  async for evento in runner.run_async(
      user_id=USER_ID, session_id=session_id, new_message=mensagem
  ):
    if texto := _texto(evento).strip():
      textos.append(texto)
  return "\n".join(textos)
