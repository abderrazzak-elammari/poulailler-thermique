"""Régulation de l'ambiance : ventilation proportionnelle au-dessus de la
consigne, chauffage proportionnel en dessous, refroidissement évaporatif
en option. C'est ce que fait un boîtier de régulation d'élevage ordinaire,
en plus simple.

Les débits sont exprimés en m3/h par kg de poids vif, comme dans les
recommandations techniques, et convertis en m3/s dans le modèle.
"""
from dataclasses import dataclass

from . import air


@dataclass
class Regulation:
    consigne: float = 22.0         #°C, dépend de l'âge du lot
    bande: float = 4.0             #K, largeur de la bande proportionnelle
    debit_min: float = 1.0         #m3/h/kg, ventilation minimale (hygiène)
    debit_max: float = 5.0         #m3/h/kg, plein débit en été
    chauffage_max: float = 0.0     #W, 0 en été; 100 à 150 kW pour 1200 m2
    bande_chauffage: float = 2.0   #K, pleine puissance 2 K sous la consigne

    # Pads de cooling. 0 = pas de pads, un pad en bon état fait 0,6 à 0,8 de l'écart sec-humide. Déclenchés sur la température intérieure,
    # comme un vrai boîtier. Le pad_tau de 15 min est l'inertie de la pompe et du pad mouillé; sans lui la boucle oscille.
    pad_efficacite: float = 0.0
    pad_seuil: float = 28.0        # °C intérieurs à partir desquels on arrose
    pad_bande: float = 2.0         # K, montée progressive de l'arrosage
    pad_tau: float = 900.0         # s, temps de réponse de l'arrosage

    def debit(self, t_air, masse_totale):
        """Débit de ventilation en m3/s, linéaire entre min et max sur la
        bande proportionnelle au-dessus de la consigne."""
        x = (t_air - self.consigne) / self.bande
        x = min(max(x, 0.0), 1.0)
        q_kg = self.debit_min + x * (self.debit_max - self.debit_min)
        return q_kg * masse_totale / 3600.0

    def chauffage(self, t_air):
        """Puissance de chauffage (W), linéaire de 0 à la consigne jusqu'au maximum `bande_chauffage` kelvins plus bas"""
        if self.chauffage_max <= 0.0:
            return 0.0
        x = (self.consigne - t_air) / self.bande_chauffage
        return self.chauffage_max * min(max(x, 0.0), 1.0)

    def consigne_pads(self, t_air):
        """Fraction d'arrosage demandée de 0 à 1 selon la température intérieure"""
        if self.pad_efficacite <= 0.0:
            return 0.0
        x = (t_air - self.pad_seuil) / self.pad_bande
        return min(max(x, 0.0), 1.0)

    def air_entrant(self, t_ext, w_ext, t_hum_ext, x):
        """Température et humidité absolue de l'air qui entre dans le  bâtiment, pour une fraction d'arrosage x. Sans pads c'est l'air
        extérieur. Avec, refroidissement adiabatique : la chaleur sensible perdue part en vapeur d'eau"""
        if self.pad_efficacite <= 0.0 or x <= 0.0:
            return t_ext, w_ext
        t_in = t_ext - x * self.pad_efficacite * max(t_ext - t_hum_ext, 0.0)
        w_in = w_ext + air.CP * (t_ext - t_in) / air.L_V
        return t_in, w_in
