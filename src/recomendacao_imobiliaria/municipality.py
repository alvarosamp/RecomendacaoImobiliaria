"""Identidade municipal compartilhada pelos provedores do piloto."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class MunicipalityMismatch(ValueError):
    """Uma fonte retornou dados de outro municipio."""


@dataclass(frozen=True)
class Municipality:
    name: str
    state: str
    ibge_code: str

    @property
    def datasus_code(self) -> str:
        return self.ibge_code[:6]

    def validate_code(self, code: str | int, *, datasus: bool = False) -> None:
        expected = self.datasus_code if datasus else self.ibge_code
        if str(code) != expected:
            raise MunicipalityMismatch(f"Municipio inesperado: {code}; esperado {expected} ({self.name}).")

    def validate_sector(self, code: str) -> None:
        if not code.startswith(self.ibge_code):
            raise MunicipalityMismatch(f"Setor censitario fora de {self.name}: {code}.")
        if len(code) != 15 or not code.isdigit():
            raise ValueError(f"Identificador nao representa setor censitario: {code}.")


def load_municipality() -> Municipality:
    path = Path(__file__).resolve().parents[2] / "config/cities/pouso_alegre.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    code = str(data["ibge_code"])
    if len(code) != 7 or not code.isdigit():
        raise ValueError("Codigo IBGE municipal deve conter sete digitos.")
    return Municipality(data["name"], data["state"], code)


MUNICIPALITY = load_municipality()
