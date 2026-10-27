"""Géométrie et enveloppe du bâtiment.

Valeurs par défaut : un bâtiment de 1200 m2 en panneaux sandwich, le format
courant en poulet de chair standard. Les U sont ceux de panneaux de 60 mm
de mousse, le toit un peu mieux isolé que les murs. Le sol est une dalle
béton avec sa litière, c'est lui qui fait l'inertie.
"""
from dataclasses import dataclass


@dataclass
class Batiment:
    longueur: float = 80.0        # m
    largeur: float = 15.0         # m
    hauteur: float = 3.5          # m, hauteur moyenne sous toit

    u_murs: float = 0.45          # W/(m2.K)
    u_toit: float = 0.35          # W/(m2.K)
    u_sol: float = 0.30           # W/(m2.K), dalle vers le sol profond

    alpha_toit: float = 0.60      # absorptivité solaire du toit (gris clair)
    h_ext: float = 20.0           # W/(m2.K), échange toit / air extérieur
    h_int: float = 4.0            # W/(m2.K), échange air intérieur / sol

    # Inertie du noeud "masse" : couche active de la dalle plus la litière.
    # 1e8 J/K correspond à peu près à 4 cm de béton sur 1200 m2. La dalle
    # entière en ferait trois fois plus, mais le fond ne suit pas les
    # variations horaires.
    capacite_masse: float = 1.0e8  # J/K
    t_sol_profond: float = 14.0    # °C, sous la dalle, constant à l'échelle d'une semaine

    @property
    def surface(self):
        return self.longueur * self.largeur

    @property
    def volume(self):
        return self.surface * self.hauteur

    @property
    def surface_murs(self):
        return 2.0 * (self.longueur + self.largeur) * self.hauteur

    @property
    def surface_toit(self):
        # pente faible, 10 % de plus que l'emprise au sol
        return 1.1 * self.surface

    # Conductances globales en W/K, pour écrire les bilans sans refaire
    # les produits U.A partout.
    @property
    def h_murs(self):
        return self.u_murs * self.surface_murs

    @property
    def h_toit(self):
        return self.u_toit * self.surface_toit

    @property
    def h_air_masse(self):
        return self.h_int * self.surface

    @property
    def h_masse_sol(self):
        return self.u_sol * self.surface

    def temperature_sol_air(self, t_ext, rayonnement):
        """Température "sol-air" du toit : la température extérieure
        équivalente qui inclut l'apport solaire absorbé par la couverture."""
        return t_ext + self.alpha_toit * rayonnement / self.h_ext
