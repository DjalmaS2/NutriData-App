# Jejum intermitente: protocolos e cálculos de duração
from datetime import timedelta

# Nome do protocolo: horas de jejum (o resto do dia é a janela para comer)
PROTOCOLOS = {
    "12:12": 12,
    "14:10": 14,
    "16:8": 16,
    "18:6": 18,
    "20:4": 20,
}


def horas_decorridas(inicio, agora):
    return (agora - inicio).total_seconds() / 3600


def previsao_fim(inicio, meta_horas):
    return inicio + timedelta(hours=meta_horas)


def formatar_duracao(horas):
    """2.5 -> '2h30'"""
    minutos = int(round(horas * 60))
    return f"{minutos // 60}h{minutos % 60:02d}"
