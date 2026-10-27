"""Le modèle lui-même : deux noeuds thermiques et un bilan d'humidité.

Noeud "air" : l'air intérieur, supposé bien mélangé.
    C_a dTa/dt = Qs + Qch + rho.cp.Qv (Tin - Ta) + Hm (Te - Ta)
                 + Ht (Tsa - Ta) + Ham (Tm - Ta)
    Qs    chaleur sensible des animaux
    Qch   chauffage
    Qv    débit de ventilation, Tin température de l'air entrant
          (Te, ou moins si les pads de refroidissement tournent)
    Hm    conductance des murs, Ht celle du toit vers la température sol-air Tsa
    Ham   échange entre l'air et le noeud masse

Noeud "masse" : la dalle et la litière, qui lissent les variations.
    C_m dTm/dt = Ham (Ta - Tm) + Hms (Tsol - Tm)

Humidité absolue w de l'air intérieur :
    rho.V dw/dt = Ql / Lv + rho.Qv (win - w)
    Ql    chaleur latente des animaux (litière comprise, cf. animaux.py)

Pas de temps de 60 s. Le noeud air a une constante de temps de l'ordre de
la minute quand la ventilation est à fond, un Euler explicite y serait
instable ou demanderait un pas ridicule. Comme les bilans sont linéaires
en Ta et en w à coefficients gelés sur le pas, je les intègre exactement
(solution exponentielle vers l'équilibre). Le noeud masse a une constante
de temps de plusieurs heures, un Euler explicite lui suffit.
"""
import numpy as np
import pandas as pd

from . import air
from .animaux import Lot
from .batiment import Batiment
from .regulation import Regulation


def _pas_lineaire(x, a, b, c, dt):
    """Solution exacte de c dx/dt = b - a x sur un pas dt (a >= 0)."""
    if a <= 0.0:
        return x + b * dt / c
    x_eq = b / a
    return x_eq + (x - x_eq) * np.exp(-a * dt / c)


def simuler(meteo, batiment=None, lot=None, regulation=None, dt=60.0,
            t_air0=None, t_masse0=None):
    """Simule l'ambiance du bâtiment sur la période couverte par `meteo`.

    meteo : DataFrame indexé en temps, colonnes t_ext (°C), hr_ext (%),
            rayonnement (W/m2), au pas dt (voir meteo.interpoler).
    Renvoie un DataFrame au même index avec l'état intérieur et les
    commandes à chaque pas.
    """
    bat = batiment or Batiment()
    lot = lot or Lot()
    reg = regulation or Regulation()

    n = len(meteo)
    t_ext = meteo["t_ext"].to_numpy(float)
    hr_ext = meteo["hr_ext"].to_numpy(float)
    ray = meteo["rayonnement"].to_numpy(float)
    w_ext = air.humidite_absolue(t_ext, hr_ext)
    t_hum_ext = air.temperature_humide(t_ext, hr_ext)

    c_air = air.RHO * air.CP * bat.volume
    c_eau = air.RHO * bat.volume
    masse = lot.masse_totale

    # état initial : à la consigne, l'air et la dalle à la même température.
    # Pour une étude sérieuse il faut un jour de mise en régime, le script le fait en doublant le premier jour.
    ta = reg.consigne if t_air0 is None else t_air0
    tm = ta if t_masse0 is None else t_masse0
    x_pads = 0.0
    w = air.humidite_absolue(ta, 60.0)

    out = np.empty((n, 9))
    for i in range(n):
        qs, ql = lot.chaleur(ta)
        qv = reg.debit(ta, masse)
        qch = reg.chauffage(ta)
        tsa = bat.temperature_sol_air(t_ext[i], ray[i])
        x_pads += dt / reg.pad_tau * (reg.consigne_pads(ta) - x_pads)
        t_in, w_in = reg.air_entrant(t_ext[i], w_ext[i], t_hum_ext[i], x_pads)
        out[i] = ta, tm, w, qv, qch, qs, ql, tsa, t_in

        # noeud air
        a = air.RHO * air.CP * qv + bat.h_murs + bat.h_toit + bat.h_air_masse
        b = (qs + qch + air.RHO * air.CP * qv * t_in
             + bat.h_murs * t_ext[i] + bat.h_toit * tsa
             + bat.h_air_masse * tm)
        ta_new = _pas_lineaire(ta, a, b, c_air, dt)

        # noeud masse, avec la température d'air du début du pas
        flux_m = bat.h_air_masse * (ta - tm) + bat.h_masse_sol * (bat.t_sol_profond - tm)
        tm = tm + dt * flux_m / bat.capacite_masse

        # humidité
        aw = air.RHO * qv
        bw = ql / air.L_V + air.RHO * qv * w_in
        w = _pas_lineaire(w, aw, bw, c_eau, dt)

        ta = ta_new

    res = pd.DataFrame(out, index=meteo.index, columns=[
        "t_air", "t_masse", "w_air", "debit_m3s", "chauffage_W",
        "q_sensible_W", "q_latente_W", "t_sol_air", "t_entrant"])
    res.insert(0, "t_ext", t_ext)
    res.insert(1, "hr_ext", hr_ext)
    res.insert(2, "rayonnement", ray)
    res["hr_air"] = air.humidite_relative(res["t_air"], res["w_air"])
    res["debit_m3h_kg"] = res["debit_m3s"] * 3600.0 / masse if masse > 0 else 0.0
    res["thi"] = air.thi_volailles(res["t_air"], res["hr_air"])
    return res


def bilan(res, seuil=30.0):
    """Quelques chiffres pour résumer une simulation."""
    dt_h = (res.index[1] - res.index[0]).total_seconds() / 3600.0
    return {
        "t_air_max": float(res["t_air"].max()),
        "t_ext_max": float(res["t_ext"].max()),
        "ecart_int_ext_max": float((res["t_air"] - res["t_ext"]).max()),
        "heures_au_dessus_seuil": float((res["t_air"] > seuil).sum() * dt_h),
        "hr_air_max": float(res["hr_air"].max()),
        "thi_max": float(res["thi"].max()),
        "debit_moyen_m3h_kg": float(res["debit_m3h_kg"].mean()),
        "chauffage_kWh": float(res["chauffage_W"].sum() * dt_h / 1000.0),
    }
