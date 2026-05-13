from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .exceptions import RN03MissingCriticalDataError


@dataclass(frozen=True)
class TriageInput:
    spo2: int | None
    frecuencia_cardiaca: int | None
    temperatura: Decimal | None
    red_flag: str | None = None


class RuleEngine(ABC):
    """Contrato para reglas de prioridad clinica (OCP)."""

    @abstractmethod
    def evaluate(self, triage_input: TriageInput) -> int | None:
        """Retorna prioridad [1..5] o None si la regla no aplica."""


class RedFlagRule(RuleEngine):
    """Aplica prioridad urgente por sintomas de alto riesgo."""

    CRITICAL_FLAGS = {
        "DOLOR_TORACICO",
        "DIFICULTAD_RESPIRATORIA",
        "HEMORRAGIA_ACTIVA",
    }

    def evaluate(self, triage_input: TriageInput) -> int | None:
        if triage_input.red_flag in self.CRITICAL_FLAGS:
            return 2
        return None


class BasicVitalSignsRule(RuleEngine):
    """Regla base de signos vitales para MVP2."""

    def evaluate(self, triage_input: TriageInput) -> int | None:
        spo2_priority = self._priority_by_spo2(triage_input.spo2)
        hr_priority = self._priority_by_heart_rate(triage_input.frecuencia_cardiaca)
        temp_priority = self._priority_by_temperature(triage_input.temperatura)
        return min(spo2_priority, hr_priority, temp_priority)

    @staticmethod
    def _priority_by_spo2(spo2: int | None) -> int:
        if spo2 is None:
            return 5
        if spo2 < 85:
            return 1
        if spo2 <= 89:
            return 2
        if spo2 <= 94:
            return 3
        return 5

    @staticmethod
    def _priority_by_heart_rate(heart_rate: int | None) -> int:
        if heart_rate is None:
            return 5
        if heart_rate < 40 or heart_rate > 140:
            return 1
        if 40 <= heart_rate <= 49 or 121 <= heart_rate <= 140:
            return 2
        if 50 <= heart_rate <= 59 or 101 <= heart_rate <= 120:
            return 3
        return 5

    @staticmethod
    def _priority_by_temperature(temperature: Decimal | None) -> int:
        if temperature is None:
            return 5
        if temperature < Decimal("35.0") or temperature >= Decimal("41.0"):
            return 1
        if Decimal("35.0") <= temperature < Decimal("36.0") or Decimal(
            "39.0"
        ) <= temperature < Decimal("41.0"):
            return 2
        if Decimal("38.0") <= temperature < Decimal("39.0"):
            return 3
        return 5


class TriageCalculatorService:
    """Orquesta reglas y retorna el nivel de prioridad final."""

    def __init__(self, rules: Iterable[RuleEngine] | None = None):
        self.rules = list(rules) if rules else [RedFlagRule(), BasicVitalSignsRule()]

    def calculate(self, triage_input: TriageInput) -> int:
        self._validate_required_input(triage_input)

        priorities = [
            rule_priority
            for rule in self.rules
            for rule_priority in [rule.evaluate(triage_input)]
            if rule_priority is not None
        ]
        return min(priorities) if priorities else 5

    @staticmethod
    def _validate_required_input(triage_input: TriageInput) -> None:
        missing_fields = []
        if triage_input.spo2 is None:
            missing_fields.append("spo2")
        if triage_input.frecuencia_cardiaca is None:
            missing_fields.append("frecuencia_cardiaca")
        if triage_input.temperatura is None:
            missing_fields.append("temperatura")
        if missing_fields:
            raise RN03MissingCriticalDataError(missing_fields)
