"""Psychrométrie de l'air humide, le strict nécessaire.

Formule de Magnus pour la pression de vapeur saturante (coefficients
Alduchov et Eskridge 1996), humidité absolue en kg d'eau par kg d'air sec.
Pression atmosphérique fixée à 101325 Pa, l'altitude des bâtiments que je
regarde ne justifie pas mieux.
"""
import numpy as np

P_ATM = 101325.0      # Pa
RHO = 1.2             # kg/m3, masse volumique de l'air
CP = 1006.0           # J/(kg.K), chaleur massique de l'air
L_V = 2.45e6          # J/kg, chaleur latente de vaporisation vers 20 °C


def p_sat(t):
    """Pression de vapeur saturante (Pa) à la température t (°C)"""
    return 610.94 * np.exp(17.625 * t / (t + 243.04))


def humidite_absolue(t, hr):
    """kg d'eau / kg d'air sec, à partir de t (°C) et hr (%)"""
    pv = hr / 100.0 * p_sat(t)
    return 0.622 * pv / (P_ATM - pv)


def humidite_relative(t, w):
    """hr (%) à partir de t (°C) et de l'humidité absolue w. Bornée à 100"""
    pv = w * P_ATM / (0.622 + w)
    return np.clip(100.0 * pv / p_sat(t), 0.0, 100.0)


def temperature_humide(t, hr):
    """Température de bulbe humide (°C), formule empirique de Stull (2011)

    Valable entre 5 et 99 % d'humidité et -20 et 50 °C, écart annoncé
    inférieur à 1 °C. Largement suffisant pour un indice de stress
    """
    hr = np.clip(hr, 5.0, 99.0)
    return (t * np.arctan(0.151977 * np.sqrt(hr + 8.313659))
            + np.arctan(t + hr) - np.arctan(hr - 1.676331)
            + 0.00391838 * hr ** 1.5 * np.arctan(0.023101 * hr)
            - 4.686035)


def thi_volailles(t, hr):
    """Indice température-humidité pour poulets de chair, Tao et Xin (2003)

    THI = 0,85 Tsec + 0,15 Thumide. Les seuils dépendent de l'âge et de la
    souche, je ne les code pas ici, je sors juste l'indice
    """
    return 0.85 * t + 0.15 * temperature_humide(t, hr)
