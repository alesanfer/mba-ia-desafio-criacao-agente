"""API do assistente do Residencial Aurora."""

import asyncio
import logging
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from google.genai import types
from pydantic import BaseModel

from app import confirmacoes, db, repositorio, runtime

logger = logging.getLogger(__name__)


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
  db.inicializar()
  yield


app = FastAPI(title="Assistente do Residencial Aurora", lifespan=ciclo_de_vida)

# Uma execução por vez em cada sessão: evita duas respostas concorrentes para
# a mesma confirmação e eventos intercalados.
_travas: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


class NovaSessao(BaseModel):
  apartamento: str


class Mensagem(BaseModel):
  texto: str


class RespostaConfirmacao(BaseModel):
  id: str
  confirmado: bool


async def _sessao_ou_404(session_id: str):
  sessao = await runtime.buscar_sessao(session_id)
  if sessao is None:
    raise HTTPException(status_code=404, detail="Sessão não encontrada.")
  return sessao


async def _executar(session_id: str, mensagem: types.Content) -> dict:
  try:
    resposta = await runtime.executar(session_id, mensagem)
  except Exception as erro:  # falha do modelo ou do runtime
    logger.exception("Falha ao executar o agente")
    raise HTTPException(
        status_code=502, detail=f"Falha ao executar o assistente: {erro}"
    ) from erro
  sessao = await _sessao_ou_404(session_id)
  return {
      "resposta": resposta,
      "confirmacoes_pendentes": confirmacoes.pendentes(sessao.events),
  }


# --- Conversa ---------------------------------------------------------------


@app.post("/sessoes", status_code=201)
async def criar_sessao(corpo: NovaSessao):
  apartamento = corpo.apartamento.strip()
  if apartamento not in repositorio.APARTAMENTOS:
    raise HTTPException(status_code=404, detail="Apartamento não encontrado.")
  sessao = await runtime.criar_sessao(apartamento)
  return {"session_id": sessao.id}


@app.post("/sessoes/{session_id}/mensagens")
async def enviar_mensagem(session_id: str, corpo: Mensagem):
  async with _travas[session_id]:
    await _sessao_ou_404(session_id)
    return await _executar(session_id, types.UserContent(corpo.texto))


@app.post("/sessoes/{session_id}/confirmacoes")
async def responder_confirmacao(session_id: str, corpo: RespostaConfirmacao):
  async with _travas[session_id]:
    sessao = await _sessao_ou_404(session_id)
    # Garantia 1: só passa id que está pendente NESTA sessão. Id desconhecido,
    # de outra sessão ou já respondido recebe 409 antes de chegar ao agente.
    ids_pendentes = {p["id"] for p in confirmacoes.pendentes(sessao.events)}
    if corpo.id not in ids_pendentes:
      raise HTTPException(
          status_code=409,
          detail="Não existe confirmação pendente com esse id nesta sessão.",
      )
    return await _executar(
        session_id, confirmacoes.montar_resposta(corpo.id, corpo.confirmado)
    )


@app.get("/sessoes/{session_id}/eventos")
async def listar_eventos(session_id: str):
  sessao = await _sessao_ou_404(session_id)
  return [
      evento.model_dump(mode="json", exclude_none=True)
      for evento in sessao.events
  ]


# --- Verificação (leem o banco direto, sem passar pelo modelo) --------------


@app.get("/apartamentos/{numero}/reservas")
def reservas_do_apartamento(numero: str):
  return repositorio.listar_reservas(numero)


@app.get("/apartamentos/{numero}/visitantes")
def visitantes_do_apartamento(numero: str):
  return repositorio.listar_visitantes(numero)
