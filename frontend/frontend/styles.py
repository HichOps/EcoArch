# --- CSS VARIABLES & ANIMATIONS ---

GLOBAL_ANIMATIONS = """
@keyframes pulse-red {
    0% { box-shadow: 0 0 0 0 rgba(229, 62, 62, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(229, 62, 62, 0); }
    100% { box-shadow: 0 0 0 0 rgba(229, 62, 62, 0); }
}
@keyframes pulse-green {
    0% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(72, 187, 120, 0); }
    100% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0); }
}
"""

# Couleurs Néon pour les graphiques (utilisées par Recharts)
NEON_GREEN = "#39ff14"
NEON_RED = "#ff003c"