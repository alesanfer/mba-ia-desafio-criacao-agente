"""Especialista no regulamento interno.

É acionado pelo agente principal como AgentTool: roda em uma sessão própria e
descartável, e só a resposta final volta para a sessão do morador. O texto dos
capítulos consultados nunca entra nos eventos da conversa (Garantia 4).
"""

from google.adk.agents import LlmAgent

from app.agentes.modelo import MODELO
from app.tools.regulamento import INDICE, consultar_regulamento

INSTRUCAO = f"""Você responde dúvidas sobre o regulamento interno do Residencial
Aurora.

Índice dos capítulos:
{INDICE}

Como trabalhar:
- Escolha pelo índice o capítulo que trata do assunto e leia-o com
  consultar_regulamento. Só consulte outro capítulo se o primeiro não trouxer
  a resposta.
- Responda apenas com base no texto consultado, em uma ou duas frases, citando
  o dado pedido (horário, limite, prazo). Não copie artigos inteiros.
- Se o regulamento não tratar do assunto, diga isso.
"""

agente_regulamento = LlmAgent(
    name="regulamento",
    model=MODELO,
    description=(
        "Responde dúvidas sobre o regulamento interno do condomínio: horários,"
        " regras de uso das áreas, silêncio, animais, obras, mudanças, garagem,"
        " lixo e penalidades. Envie a pergunta completa do morador."
    ),
    instruction=INSTRUCAO,
    tools=[consultar_regulamento],
)
