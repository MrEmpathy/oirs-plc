from django.contrib.auth.hashers import Argon2PasswordHasher


class Argon2idOWASP(Argon2PasswordHasher):
    """Argon2id con los parámetros mínimos recomendados por OWASP (m=19 MiB, t=2, p=1).
    Mantiene la resistencia a ataques por GPU y reduce la latencia/uso de memoria del login
    en un servidor de 2 vCPU (incidencia de rendimiento INC-03)."""
    memory_cost = 19456
    time_cost = 2
    parallelism = 1
