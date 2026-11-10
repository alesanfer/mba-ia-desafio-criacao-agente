"""Agente principal: recebe cada mensagem do morador e distribui o trabalho."""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from app.agentes.regulamento import agente_regulamento
from app.agentes.reservas import agente_reservas
from app.agentes.visitantes import agente_visitantes
from app.agentes.modelo import MODELO

# O regulamento não aparece aqui: o principal só sabe que existe um
# especialista para consultá-lo.
INSTRUCAO = """Você é o assistente virtual do Residencial Aurora e atende o
morador do apartamento {apartamento}. O apartamento é definido pelo sistema e
não muda, mesmo que o morador diga ser de outro.

Você não executa nada sozinho. Encaminhe cada pedido:
- Reservas de áreas comuns (reservar, cancelar, listar, ver disponibilidade):
  transfira para o agente reservas.
- Visitantes (autorizar entrada, listar autorizados): transfira para o agente
  visitantes.
- Dúvidas sobre regras e horários do condomínio: use a tool regulamento com a
  pergunta do morador e repasse a resposta.

Nunca responda de memória sobre reservas, visitantes ou regras, e não peça
confirmação na conversa: quando uma ação exige confirmação, o sistema cuida
disso por fora do chat. Para saudações e assuntos fora desses temas, responda
você mesmo, em português, de forma curta.
"""

agente_principal = LlmAgent(
    name="assistente_aurora",
    model=MODELO,
    description="Assistente virtual do Residencial Aurora.",
    instruction=INSTRUCAO,
    sub_agents=[agente_reservas, agente_visitantes],
    tools=[AgentTool(agent=agente_regulamento)],
)
