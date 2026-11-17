# Data e hora sempre no fuso de Brasília.
# O Streamlit Cloud roda em UTC (3 horas à frente); com datetime.now() as refeições,
# a água e o jejum seriam registrados com a hora errada no app online.
from datetime import datetime
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")


def agora():
    """Data e hora de agora em Brasília, sem fuso anexado (igual aos registros do banco)."""
    return datetime.now(FUSO).replace(tzinfo=None)


def hoje():
    return agora().date()
