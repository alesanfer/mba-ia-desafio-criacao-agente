# Assistente virtual do Residencial Aurora

API em Python com um assistente construído em Google ADK. Pelo chat, o morador reserva áreas comuns, cancela as próprias reservas, autoriza visitantes e tira dúvidas sobre o regulamento. As regras críticas estão no código: o modelo decide o caminho da conversa, e o código decide o que é permitido.

- Python 3.12+, projeto gerenciado por `uv`
- `google-adk==2.14.0` (versão fixada em `pyproject.toml`)
- FastAPI e SQLite, sem serviço externo

## Arquitetura

```
morador ── API (FastAPI) ── Runner do ADK ── assistente_aurora (principal)
                                              ├── transferência ── reservas ──── tools de reservas ──┐
                                              ├── transferência ── visitantes ── tools de visitantes ├── SQLite
                                              └── AgentTool ────── regulamento ─ consultar_regulamento (dados/regulamento.md)
```

### Agentes

| Agente | Arquivo | Responsabilidade | Como é acionado |
|---|---|---|---|
| `assistente_aurora` (principal) | `app/agentes/principal.py` | Recebe cada mensagem do morador e encaminha. Não tem tools de dados. | É o agente raiz do `App`. |
| `reservas` | `app/agentes/reservas.py` | Reservar, cancelar, listar reservas e ver disponibilidade. | Transferência (`sub_agents`). |
| `visitantes` | `app/agentes/visitantes.py` | Autorizar e listar visitantes. | Transferência (`sub_agents`). |
| `regulamento` | `app/agentes/regulamento.py` | Responder dúvidas lendo um capítulo do regulamento por vez. | `AgentTool` chamada pelo principal. |

Por que cada um é acionado assim:

- **`reservas` e `visitantes` por transferência.** As tools desses agentes pedem confirmação e pausam a execução. A retomada só funciona se a resposta da confirmação chegar ao agente que fez o pedido, e o Runner localiza esse agente pelos eventos da sessão. Com transferência, o especialista escreve na própria sessão do morador e o Runner o encontra, inclusive depois de reiniciar a API. Uma `AgentTool` não serve aqui: ela roda em sessão descartável e o ADK não consegue retomar uma pausa dentro dela.
- **`disallow_transfer_to_parent=True` nos dois.** Sem esse bloqueio, a mensagem seguinte iria para o último especialista que respondeu. Com ele, toda mensagem nova entra pelo principal, e o roteamento não depende do assunto anterior. A resposta de uma confirmação continua indo ao especialista certo, porque nesse caso o Runner segue o autor da chamada. A transferência entre os dois especialistas segue liberada para pedidos que misturam reservas e visitantes.
- **`regulamento` como `AgentTool`.** Aqui a sessão descartável é a vantagem: o texto do capítulo consultado fica na sessão interna, e só a resposta final volta para a conversa do morador.

### Demais peças

| Arquivo | Papel |
|---|---|
| `app/main.py` | Rotas do contrato e rotas de verificação. |
| `app/runtime.py` | `App`, `Runner` e serviço de sessão persistido. |
| `app/confirmacoes.py` | Lista as confirmações pendentes a partir dos eventos e monta a resposta do morador. |
| `app/tools/` | Tools dos especialistas e os dois pontos de controle (`sessao.py`). |
| `app/repositorio.py` | SQL de reservas e visitantes. |
| `app/db.py` | Schema, carga dos dados iniciais e restauração. |

Os arquivos de `dados/` são somente leitura. O estado vivo fica em `var/` (fora do Git): `var/condominio.db` guarda reservas e visitantes, e `var/sessoes.db` guarda as sessões do ADK. Na primeira subida, se `var/condominio.db` não existir, ele é criado com os dados iniciais.

## Garantias

### Garantia 1: cobrança ou acesso só com confirmação

- **`exigir_confirmacao` em `app/tools/sessao.py`.** As tools `reservar_area` (quando a área tem taxa) e `autorizar_visitante` chamam essa função antes de gravar. Na primeira chamada ela registra a pendência com `tool_context.request_confirmation` e a tool retorna sem gravar. A gravação só acontece quando `tool_context.tool_confirmation.confirmed` é verdadeiro.
- **`reservar_area` em `app/tools/reservas.py`.** Área com taxa zero pula a confirmação; cancelamento nunca pede.
- **`montar_resposta` em `app/confirmacoes.py`.** `tool_confirmation` só é preenchido pelo ADK a partir de uma `FunctionResponse` de nome `adk_request_confirmation`, e só a rota de confirmações monta esse tipo de mensagem. A rota de mensagens envia apenas texto.
- **`responder_confirmacao` em `app/main.py`.** Antes de chamar o agente, a rota confere se o id está na lista de pendências daquela sessão (`pendentes` em `app/confirmacoes.py`). Id desconhecido, de outra sessão ou já respondido recebe 409 e o Runner não é chamado.

Não depende do modelo porque o texto do morador não tem como virar `tool_confirmation`: "já estou confirmando aqui" é só texto, e a tool continua retornando sem gravar.

### Garantia 2: cada sessão pertence a um apartamento

- **`criar_sessao` em `app/runtime.py`.** Único ponto em que o apartamento entra no `state` da sessão.
- **`apartamento_da_sessao` em `app/tools/sessao.py`.** Todas as tools obtêm o apartamento por essa função. Nenhuma tool tem parâmetro de apartamento, então o modelo não tem como informar outro.
- **`app/repositorio.py`.** `listar_reservas`, `listar_visitantes` e `cancelar_reserva` filtram por apartamento no próprio SQL. Uma reserva de outro apartamento simplesmente não é encontrada, e a resposta é a mesma de uma reserva inexistente.
- **`data_ocupada` em `app/repositorio.py`.** Devolve só verdadeiro ou falso. O código e o apartamento da reserva alheia nunca chegam à tool, logo não chegam aos eventos.

Não depende do modelo porque os dados de outro apartamento nunca são lidos para dentro da conversa: não há o que o prompt possa vazar.

### Garantia 3: nada se perde no reinício

- **`servico_sessoes` em `app/runtime.py`.** `SqliteSessionService` grava sessões e eventos em `var/sessoes.db`.
- **`ResumabilityConfig(is_resumable=True)` em `app/runtime.py`.** Permite retomar uma execução pausada em confirmação, mesmo em outro processo.
- **`pendentes` em `app/confirmacoes.py`.** As pendências são derivadas dos eventos persistidos, não de memória do processo.
- **`app/db.py` e `app/repositorio.py`.** Reservas e visitantes ficam em `var/condominio.db`. O código da reserva é chave primária de uma tabela que mantém também as canceladas, então `criar_reserva` nunca repete um código.

### Garantia 4: o regulamento é consultado, não carregado

- **`AgentTool(agent=agente_regulamento)` em `app/agentes/principal.py`.** O especialista roda em sessão interna descartável; na sessão do morador entram apenas a pergunta e a resposta final.
- **`consultar_regulamento` em `app/tools/regulamento.py`.** Devolve um capítulo por chamada. O especialista recebe nas instruções só o índice de títulos.
- **`INSTRUCAO` em `app/agentes/principal.py`.** O principal não recebe texto do regulamento, só a existência do especialista.

Não depende do modelo porque, mesmo que o especialista consulte o capítulo errado, esse texto fica na sessão descartável e não nos eventos do morador.

### Garantia 5: dois moradores, uma reserva

- **`uq_reserva_ativa` em `app/db.py`.** Índice único parcial em `(area, data)` para reservas com `status = 'ativa'`.
- **`criar_reserva` em `app/repositorio.py`.** Faz o `INSERT` direto. Se o índice recusar, devolve `None`, e `reservar_area` responde "indisponível" como resultado normal da tool, sem erro de servidor.

A conferência de disponibilidade feita antes (`data_ocupada`) serve só para não pedir confirmação de cobrança por uma data já ocupada. Quem garante a exclusividade é o banco, no instante da gravação.

## Como rodar

### Pré-requisitos

- Python 3.12 ou superior
- [uv](https://docs.astral.sh/uv/)
- Uma chave do [Google AI Studio](https://aistudio.google.com/apikey)

### Variáveis do `.env`

```
cp .env.example .env
```

| Variável | Obrigatória | Descrição |
|---|---|---|
| `GOOGLE_API_KEY` | sim | Chave do Google AI Studio. |
| `MODELO_GEMINI` | não | Modelo usado pelos agentes. Padrão: `gemini-3.5-flash`. |

O fluxo completo do avaliador faz algumas dezenas de chamadas ao modelo. Se a sua chave tiver limite diário baixo para o modelo padrão, escolha outro em `MODELO_GEMINI`.

### Instalar

```
uv sync
```

### Restaurar os dados iniciais

```
uv run python -m app.restaurar
```

Volta reservas e visitantes ao estado de `dados/` e apaga todas as sessões.

### Subir a API

```
uv run uvicorn app.main:app --port 8000
```

A API responde em `http://localhost:8000`.

### Roteiro de verificação (opcional)

Com a API no ar e os dados restaurados:

```
uv run python scripts/roteiro_avaliador.py parte1   # passos 1 a 12
# pare a API com Ctrl+C e suba de novo, sem restaurar
uv run python scripts/roteiro_avaliador.py parte2   # passos 13 e 14
```
