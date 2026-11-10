"""Consulta ao regulamento por capítulo, sem carregar o texto inteiro."""

import re

from app.config import DIR_DADOS

_TEXTO = (DIR_DADOS / "regulamento.md").read_text(encoding="utf-8")
# Cada capítulo começa em um título "## ..." e vai até o próximo.
_CAPITULOS = [
    bloco.strip() for bloco in re.split(r"(?m)^(?=## )", _TEXTO)
    if bloco.startswith("## ")
]
TITULOS = [bloco.splitlines()[0].removeprefix("## ") for bloco in _CAPITULOS]

INDICE = "\n".join(f"{i}. {titulo}" for i, titulo in enumerate(TITULOS, 1))


def consultar_regulamento(capitulo: int) -> dict:
  """Devolve o texto de um capítulo do regulamento interno.

  Args:
    capitulo: número do capítulo no índice (começa em 1).
  """
  if not 1 <= capitulo <= len(_CAPITULOS):
    return {
        "status": "erro",
        "mensagem": f"Capítulo inexistente. Escolha de 1 a {len(_CAPITULOS)}.",
    }
  return {"capitulo": TITULOS[capitulo - 1], "texto": _CAPITULOS[capitulo - 1]}
