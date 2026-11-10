"""Tools de visitantes. O apartamento vem sempre da sessão."""

from google.adk.tools import ToolContext

from app import repositorio
from app.tools.sessao import apartamento_da_sessao, exigir_confirmacao


def listar_meus_visitantes(tool_context: ToolContext) -> dict:
  """Lista os visitantes autorizados pelo apartamento do morador autenticado."""
  apartamento = apartamento_da_sessao(tool_context)
  return {"visitantes": repositorio.listar_visitantes(apartamento)}


def autorizar_visitante(nome: str, data: str, tool_context: ToolContext) -> dict:
  """Autoriza a entrada de um visitante no apartamento do morador autenticado.

  Libera acesso ao prédio, então o sistema sempre pede a confirmação do morador
  por fora da conversa antes de gravar.

  Args:
    nome: nome completo do visitante.
    data: data da visita no formato AAAA-MM-DD.
  """
  nome = " ".join(nome.split())
  if not nome:
    return {"status": "erro", "mensagem": "Informe o nome do visitante."}
  if not repositorio.data_valida(data):
    return {
        "status": "erro",
        "mensagem": "Data inválida. Use o formato AAAA-MM-DD.",
    }
  apartamento = apartamento_da_sessao(tool_context)

  pendente = exigir_confirmacao(
      tool_context,
      hint=f"Autorizar a entrada de {nome} em {data}.",
      detalhes={"nome": nome, "data": data},
  )
  if pendente:
    return pendente

  repositorio.autorizar_visitante(apartamento, nome, data)
  return {
      "status": "autorizado",
      "nome": nome,
      "data": data,
      "mensagem": "Confirmação recebida. A autorização já está gravada.",
  }
