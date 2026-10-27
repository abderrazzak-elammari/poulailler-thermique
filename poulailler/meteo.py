"""Données météo : lecture d'un CSV horaire, génération d'une canicule
synthétique pour les essais, téléchargement depuis Open-Meteo.

Format attendu partout : un DataFrame indexé par l'heure, trois colonnes
    t_ext        température de l'air à 2 m, °C
    hr_ext       humidité relative, %
    rayonnement  rayonnement global horizontal, W/m2
"""
import json
import urllib.request

import numpy as np
import pandas as pd

COLONNES = ["t_ext", "hr_ext", "rayonnement"]


def lire_csv(chemin):
    df = pd.read_csv(chemin, parse_dates=["temps"], index_col="temps")
    manque = [c for c in COLONNES if c not in df.columns]
    if manque:
        raise ValueError(f"colonnes absentes du fichier météo : {manque}")
    return df[COLONNES].astype(float)


def synthetique(jours=5, t_min=18.0, t_max=36.0, montee=4.0, debut="2022-07-14"):
    """Une canicule inventée : journées sinusoïdales dont le maximum monte
    de `montee` degrés sur la période, humidité qui baisse quand il fait
    chaud, soleil de juillet. Sert aux tests et à faire tourner le modèle
    sans connexion."""
    idx = pd.date_range(debut, periods=24 * jours, freq="h")
    h = idx.hour.to_numpy() + idx.minute.to_numpy() / 60.0
    j = np.arange(len(idx)) / 24.0
    # minimum vers 5 h, maximum vers 16 h
    cycle = 0.5 - 0.5 * np.cos(2 * np.pi * (h - 5.0) / 24.0)
    cycle = cycle ** 1.3  # après-midi plus large que la nuit
    tmax = t_max + montee * j / max(jours - 1, 1)
    t = t_min + (tmax - t_min) * cycle
    hr = 85.0 - 55.0 * cycle
    ray = 850.0 * np.clip(np.sin(np.pi * (h - 6.0) / 14.5), 0.0, None)
    return pd.DataFrame({"t_ext": t, "hr_ext": hr, "rayonnement": ray}, index=idx)


def interpoler(df, dt=60.0):
    """Passe de l'horaire au pas du modèle par interpolation linéaire."""
    idx = pd.date_range(df.index[0], df.index[-1], freq=f"{int(dt)}s")
    return df.reindex(df.index.union(idx)).interpolate("time").reindex(idx)


def telecharger_open_meteo(latitude, longitude, debut, fin, chemin=None):
    """Archive ERA5 via l'API Open-Meteo, gratuite et sans clé.

    debut, fin : 'AAAA-MM-JJ'. Si `chemin` est donné, écrit le CSV au
    format attendu par lire_csv. Exemple pour Rennes pendant la canicule
    de juillet 2022 :
        telecharger_open_meteo(48.11, -1.68, "2022-07-14", "2022-07-20",
                               "meteo/rennes_2022-07.csv")
    """
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={latitude}&longitude={longitude}"
           f"&start_date={debut}&end_date={fin}"
           "&hourly=temperature_2m,relative_humidity_2m,shortwave_radiation"
           "&timezone=Europe%2FParis")
    with urllib.request.urlopen(url, timeout=30) as rep:
        data = json.load(rep)["hourly"]
    df = pd.DataFrame({
        "t_ext": data["temperature_2m"],
        "hr_ext": data["relative_humidity_2m"],
        "rayonnement": data["shortwave_radiation"],
    }, index=pd.to_datetime(data["time"]))
    df.index.name = "temps"
    if chemin:
        df.to_csv(chemin)
    return df
