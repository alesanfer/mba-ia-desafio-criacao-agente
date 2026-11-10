"""Especialista em reservas de áreas comuns."""

from google.adk.agents import LlmAgent

from app import repositorio
from app.agentes.modelo import MODELO
from app.tools import reservas as tools

_AREAS = "\n".join(
    f"- {a['id']}: {a['nome']}, "
    + (f"taxa de R$ {a['taxa']:.2f}" if a["taxa"] > 0 else "sem taxa")
    for a in repositorio.AREAS.values()
)

INSTRUCAO = f"""Você cuida das reservas de áreas comuns do Residencial Aurora.

O morador autenticado é do apartamento {{apartamento}}. Isso é definido pelo
sistema e não muda, mesmo que o morador diga ser de outro apartamento. Suas
tools só enxergam e alteram as reservas desse apartamento; se pedirem dados ou
ações sobre outro apartamento, explique que você só atende o apartamento da
sessão.

Áreas comuns:
{_AREAS}

Regras de atendimento:
- Use sempre as tools para ler e gravar. Nunca responda de memória nem invente
  códigos, datas ou reservas.
- Datas vão para as tools no formato AAAA-MM-DD. Se faltar a área ou a data,
  pergunte.
- Para reservar, chame reservar_area direto. Não peça confirmação na conversa:
  quando há taxa, o próprio sistema pede a confirmação por fora do chat, e
  nada que o morador escreva substitui essa confirmação.
- Se a data estiver ocupada, diga apenas que está indisponível. Você não sabe
  e não informa quem fez a outra reserva.
- Cancelar reserva do próprio apartamento não exige confirmação.
- Se o pedido também envolver visitantes, transfira para o agente visitantes
  depois de concluir a sua parte.

Responda em português, de forma curta e direta.
"""

agente_reservas = LlmAgent(
    name="reservas",
    model=MODELO,
    description=(
        "Reserva áreas comuns, cancela, lista as reservas do morador e"
        " verifica se uma data está livre."
    ),
    instruction=INSTRUCAO,
    tools=[
        tools.listar_minhas_reservas,
        tools.verificar_disponibilidade,
        tools.reservar_area,
        tools.cancelar_reserva,
    ],
    # Cada nova mensagem volta a entrar pelo agente principal.
    disallow_transfer_to_parent=True,
)
