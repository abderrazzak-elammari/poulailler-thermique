"""Génère toutes les figures du README, d'une seule commande.

    python scripts/figures.py

Chaque figure est décrite par une ligne de la liste FIGURES : son nom de
fichier et les options passées à simuler.py. Pour renommer une figure, on
change son nom ici et on relance ce script.
"""
import os
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)

FIGURES = [
    ("figures/ambiance_canicule_sans_cooling.png", []),
    ("figures/ambiance_canicule_avec_pads.png", ["--pads", "0.7"]),
    ("figures/ambiance_lot_jeune_temps_frais.png",
     ["--debut", "2022-03-15", "--tmin", "4", "--tmax", "14", "--jours", "3", "--masse", "0.3",
      "--consigne", "29", "--chauffage", "150",
      "--titre", "Lot de deux semaines par temps frais, chauffage 150 kW"]),
]

for nom, options in FIGURES:
    print(f"--- {nom}")
    subprocess.run([sys.executable, os.path.join(ICI, "simuler.py"), *options, "--figure", nom],
                   cwd=RACINE, check=True)