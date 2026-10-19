"""Cálculo de plazos legales en días hábiles (Ley N.° 20.584: 15 días hábiles para responder).

Se consideran inhábiles los sábados, domingos y los feriados registrados en la tabla `feriado`.
Las funciones puras reciben el conjunto de feriados para ser probadas de forma unitaria sin BD."""
from datetime import date, timedelta

SEMAFORO_VERDE, SEMAFORO_AMARILLO, SEMAFORO_ROJO = "VERDE", "AMARILLO", "ROJO"
UMBRAL_AMARILLO = 5


def es_habil(dia: date, feriados: set) -> bool:
    return dia.weekday() < 5 and dia not in feriados


def sumar_dias_habiles(inicio: date, dias: int, feriados: set) -> date:
    """Devuelve la fecha en que se cumplen `dias` hábiles contados desde el día siguiente a `inicio`."""
    if dias < 0:
        raise ValueError("La cantidad de días debe ser positiva")
    actual, contados = inicio, 0
    while contados < dias:
        actual += timedelta(days=1)
        if es_habil(actual, feriados):
            contados += 1
    return actual


def dias_habiles_restantes(hoy: date, vencimiento: date, feriados: set) -> int:
    """Positivo: días hábiles que quedan. 0: vence hoy. Negativo: días hábiles de atraso."""
    if hoy == vencimiento:
        return 0
    paso = 1 if vencimiento > hoy else -1
    actual, cuenta = hoy, 0
    while actual != vencimiento:
        actual += timedelta(days=paso)
        if es_habil(actual, feriados):
            cuenta += paso
    return cuenta


def semaforo(restantes: int) -> str:
    if restantes < 0:
        return SEMAFORO_ROJO
    if restantes <= UMBRAL_AMARILLO:
        return SEMAFORO_AMARILLO
    return SEMAFORO_VERDE


def feriados_bd(desde=None, hasta=None) -> set:
    from apps.catalogos.models import Feriado
    qs = Feriado.objects.all()
    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)
    return set(qs.values_list("fecha", flat=True))
