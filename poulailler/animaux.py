"""Chaleur produite par les animaux.

Les formules viennent du 4e rapport du groupe de travail CIGR sur la
climatisation des bâtiments d'élevage (Pedersen et Sällvik, 2002, "Heat and
moisture production at animal and house levels"), chapitre poulets de chair.
Elles sont écrites au niveau du bâtiment, c'est-à-dire qu'elles incluent
déjà l'évaporation de la litière et des abreuvoirs, ce qui m'arrange : je
n'ai pas à modéliser la litière à part.
"""
from dataclasses import dataclass
import numpy as np


def chaleur_totale(masse_kg, t_air):
    """Chaleur totale par animal (W) pour un poulet de chair de masse m

    Référence CIGR à 20 °C : 10,62 m^0,75. La correction en température est
    celle du rapport, cubique autour de 20 °C : les animaux produisent un
    peu plus de chaleur au froid et un peu moins au chaud
    """
    base = 10.62 * masse_kg ** 0.75
    return base * (1.0 + 4.0e-5 * (20.0 - t_air) ** 3)


def part_sensible(t_air):
    """Fraction sensible de la chaleur totale, poulets de chair, CIGR 2002.

    Décroît avec la température : à 20 °C environ 59 %, à 30 °C environ
    55 %, le reste part en chaleur latente (respiration, litière)
    """
    return 0.61 - 0.228e-7 * (t_air + 10.0) ** 4


@dataclass
class Lot:
    """Le lot présent dans le bâtiment."""
    nombre: int = 22000       # poulets
    masse_kg: float = 2.0     # masse vive moyenne, ~35 jours en standard

    @property
    def masse_totale(self):
        return self.nombre * self.masse_kg

    def chaleur(self, t_air):
        """(sensible, latente) en W pour tout le lot à la température t_air"""
        tot = self.nombre * chaleur_totale(self.masse_kg, t_air)
        fs = np.clip(part_sensible(t_air), 0.0, 1.0)
        return tot * fs, tot * (1.0 - fs)
