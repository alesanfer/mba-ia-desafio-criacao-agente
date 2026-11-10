"""Tools de reservas. O apartamento vem sempre da sessão."""

from google.adk.tools import ToolContext

from app import repositorio
from app.tools.sessao import apartamento_da_sessao, exigir_confirmacao

ERRO_AREA = {
    "status": "erro",
    "mensagem": "Área desconhecida. Use um destes ids: "
    + ", ".join(repositorio.AREAS),
}
ERRO_DATA = {
    "status": "erro",
    "mensagem": "Data inválida. Use o formato AAAA-MM-DD.",
}


def listar_minhas_reservas(tool_context: ToolContext) -> dict:
  """Lista as reservas ativas do apartamento do morador autenticado."""
  apartamento = apartamento_da_sessao(tool_context)
  return {"reservas": repositorio.listar_reservas(apartamento)}


def verificar_disponibilidade(area: str, data: str) -> dict:
  """Informa se uma área comum está livre em uma data.

  Args:
    area: id da área (salao-de-festas, churrasqueira ou quadra).
    data: data no formato AAAA-MM-DD.
  """
  registro = repositorio.resolver_area(area)
  if not registro:
    return ERRO_AREA
  if not repositorio.data_valida(data):
    return ERRO_DATA
  ocupada = repositorio.data_ocupada(registro["id"], data)
  return {"area": registro["id"], "data": data, "disponivel": not ocupada}


def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict:
  """Reserva uma área comum para o apartamento do morador autenticado.

  Quando a área tem taxa, o sistema pede a confirmação do morador por fora da
  conversa e a reserva só é gravada depois dela.

  Args:
    area: id da área (salao-de-festas, churrasqueira ou quadra).
    data: data no formato AAAA-MM-DD.
  """
  registro = repositorio.resolver_area(area)
  if not registro:
    return ERRO_AREA
  if not repositorio.data_valida(data):
    return ERRO_DATA
  apartamento = apartamento_da_sessao(tool_context)
  indisponivel = {
      "status": "indisponivel",
      "area": registro["id"],
      "data": data,
      "mensagem": "A área já está reservada nessa data.",
  }

  if registro["taxa"] > 0:
    # Data já ocupada: recusa direto, sem gerar cobrança para confirmar.
    if repositorio.data_ocupada(registro["id"], data):
      return indisponivel
    pendente = exigir_confirmacao(
        tool_context,
        hint=(
            f"Reservar {registro['nome']} em {data} gera cobrança de"
            f" R$ {registro['taxa']:.2f}."
        ),
        detalhes={
            "area": registro["id"],
            "data": data,
            "taxa": registro["taxa"],
        },
    )
    if pendente:
      return pendente

  # A conferência acima é só cortesia; quem decide é o índice único no INSERT.
  codigo = repositorio.criar_reserva(apartamento, registro["id"], data)
  if codigo is None:
    return indisponivel
  return {
      "status": "reservada",
      "codigo": codigo,
      "area": registro["id"],
      "data": data,
      "cobranca": registro["taxa"],
      "mensagem": "A reserva já está gravada.",
  }


def cancelar_reserva(
    tool_context: ToolContext, codigo: str = "", area: str = "", data: str = ""
) -> dict:
  """Cancela uma reserva do apartamento do morador autenticado.

  Informe o código da reserva OU a área e a data.

  Args:
    codigo: código da reserva (ex.: RSV-123456).
    area: id da área (salao-de-festas, churrasqueira ou quadra).
    data: data no formato AAAA-MM-DD.
  """
  apartamento = apartamento_da_sessao(tool_context)
  registro = repositorio.resolver_area(area) if area else None
  if not codigo and not (registro and data):
    return {
        "status": "erro",
        "mensagem": "Informe o código da reserva ou a área e a data.",
    }
  cancelada = repositorio.cancelar_reserva(
      apartamento,
      codigo=codigo,
      area_id=registro["id"] if registro else "",
      data=data,
  )
  if not cancelada:
    return {
        "status": "nao_encontrada",
        "mensagem": "O seu apartamento não tem reserva ativa com esses dados.",
    }
  return {"status": "cancelada", **cancelada}
