"""Confirmações pendentes: leitura a partir dos eventos e resposta do morador."""

from google.adk.events import Event
from google.genai import types

NOME_CHAMADA = "adk_request_confirmation"


def pendentes(eventos: list[Event]) -> list[dict]:
  """Lista os pedidos de confirmação da sessão que ainda não têm resposta.

  O ADK registra cada pedido como uma chamada `adk_request_confirmation`. Ela
  deixa de estar pendente quando existe uma resposta do usuário com o mesmo
  id. Como tudo é derivado dos eventos persistidos, o resultado é o mesmo
  antes e depois de reiniciar a API.
  """
  respondidas = {
      resposta.id
      for evento in eventos
      if evento.author == "user"
      for resposta in evento.get_function_responses()
  }
  lista = []
  for evento in eventos:
    for chamada in evento.get_function_calls():
      if chamada.name != NOME_CHAMADA or chamada.id in respondidas:
        continue
      args = chamada.args or {}
      original = args.get("originalFunctionCall") or {}
      confirmacao = args.get("toolConfirmation") or {}
      lista.append({
          "id": chamada.id,
          "acao": original.get("name", ""),
          "detalhes": confirmacao.get("payload") or original.get("args") or {},
      })
  return lista


def montar_resposta(id_confirmacao: str, confirmado: bool) -> types.Content:
  """Monta a mensagem que entrega ao ADK a decisão do morador.

  É a única origem de `tool_confirmation` nas tools: uma FunctionResponse com
  o id do pedido. A rota de mensagens só envia texto, então a conversa não
  consegue produzir isto.
  """
  return types.Content(
      role="user",
      parts=[
          types.Part(
              function_response=types.FunctionResponse(
                  id=id_confirmacao,
                  name=NOME_CHAMADA,
                  response={"confirmed": confirmado},
              )
          )
      ],
  )
