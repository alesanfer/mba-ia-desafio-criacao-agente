"""Acesso das tools ao que vem do sistema: apartamento e confirmação."""

from google.adk.tools import ToolContext

CHAVE_APARTAMENTO = "apartamento"


def apartamento_da_sessao(tool_context: ToolContext) -> str:
  """Garantia 2: o apartamento vem do state gravado na criação da sessão.

  Nenhuma tool tem parâmetro de apartamento, então o modelo não tem como
  escolher outro.
  """
  return tool_context.state[CHAVE_APARTAMENTO]


def exigir_confirmacao(
    tool_context: ToolContext, *, hint: str, detalhes: dict
) -> dict | None:
  """Garantia 1: só deixa a tool seguir com confirmação vinda do sistema.

  Devolve None quando o morador aprovou pela rota de confirmações. Caso
  contrário devolve o resultado que a tool deve retornar sem gravar nada:
  na primeira chamada registra a pendência e pausa a execução; na retomada
  com resposta negativa informa a recusa.

  `tool_confirmation` só é preenchido pelo ADK a partir de uma FunctionResponse
  `adk_request_confirmation` enviada pela API; texto do morador não chega aqui.
  """
  confirmacao = tool_context.tool_confirmation
  if confirmacao is None:
    tool_context.request_confirmation(hint=hint, payload=detalhes)
    tool_context.actions.skip_summarization = True
    return {"status": "aguardando_confirmacao", **detalhes}
  if not confirmacao.confirmed:
    return {
        "status": "nao_confirmada",
        "mensagem": "O morador negou a confirmação. Nada foi gravado.",
    }
  return None
