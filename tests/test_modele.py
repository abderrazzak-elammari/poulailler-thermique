import numpy as np
import pandas as pd

from poulailler import Batiment, Lot, Regulation, air, meteo, simuler
from poulailler.modele import bilan


def meteo_constante(t_ext=25.0, hr_ext=50.0, rayonnement=0.0, heures=72):
    idx = pd.date_range("2022-07-01", periods=heures, freq="h")
    df = pd.DataFrame({"t_ext": t_ext, "hr_ext": hr_ext, "rayonnement": rayonnement}, index=idx)
    return meteo.interpoler(df)


def test_sans_source_l_interieur_rejoint_l_exterieur():
    # sans animaux il n'y a pas de ventilation, la dalle ne se vide que par
    # l'enveloppe : constante de temps d'une journée, d'où les dix jours
    bat = Batiment(t_sol_profond=25.0)
    res = simuler(meteo_constante(heures=240), bat, Lot(nombre=0), t_air0=35.0, t_masse0=35.0)
    assert abs(res["t_air"].iloc[-1] - 25.0) < 0.1
    assert abs(res["t_masse"].iloc[-1] - 25.0) < 0.1


def test_regime_permanent_verifie_les_bilans():
    # météo constante, lot présent : au bout de trois jours les deux
    # noeuds doivent être à l'équilibre des équations écrites dans modele.py
    bat, lot, reg = Batiment(), Lot(), Regulation()
    res = simuler(meteo_constante(t_ext=28.0, hr_ext=40.0), bat, lot, reg)
    r = res.iloc[-1]
    qs, ql = lot.chaleur(r["t_air"])
    qv = reg.debit(r["t_air"], lot.masse_totale)
    flux_air = (qs + air.RHO * air.CP * qv * (28.0 - r["t_air"])
                + (bat.h_murs + bat.h_toit) * (28.0 - r["t_air"])
                + bat.h_air_masse * (r["t_masse"] - r["t_air"]))
    flux_masse = (bat.h_air_masse * (r["t_air"] - r["t_masse"])
                  + bat.h_masse_sol * (bat.t_sol_profond - r["t_masse"]))
    # tolérance : 1 % de la chaleur sensible du lot
    assert abs(flux_air) < 0.01 * qs
    assert abs(flux_masse) < 0.01 * qs
    # et l'humidité : ce qui entre en vapeur ressort par la ventilation
    w_in = air.humidite_absolue(28.0, 40.0)
    assert abs(ql / air.L_V - air.RHO * qv * (r["w_air"] - w_in)) < 0.01 * ql / air.L_V


def test_la_ventilation_suit_la_chaleur():
    df = meteo.interpoler(meteo.synthetique(jours=3))
    res = simuler(df)
    i_max = res["t_ext"].idxmax()
    i_min = res["t_ext"].idxmin()
    assert res.loc[i_max, "debit_m3h_kg"] > res.loc[i_min, "debit_m3h_kg"]
    assert res["debit_m3h_kg"].between(1.0 - 1e-9, 5.0 + 1e-9).all()


def test_les_pads_refroidissent():
    df = meteo.interpoler(meteo.synthetique(jours=3))
    sans = simuler(df, regulation=Regulation())
    avec = simuler(df, regulation=Regulation(pad_efficacite=0.7))
    assert bilan(avec)["t_air_max"] < bilan(sans)["t_air_max"] - 3.0
    # refroidissement adiabatique : plus humide à l'intérieur
    assert bilan(avec)["hr_air_max"] > bilan(sans)["hr_air_max"]


def test_chauffage_tient_la_consigne_pour_un_lot_jeune():
    reg = Regulation(consigne=30.0, chauffage_max=150e3, bande_chauffage=2.0)
    lot = Lot(nombre=22000, masse_kg=0.2)
    res = simuler(meteo_constante(t_ext=8.0, hr_ext=80.0), Batiment(), lot, reg, t_air0=30.0, t_masse0=30.0)
    dernier_jour = res.iloc[-1440:]
    assert dernier_jour["t_air"].min() > 30.0 - 2.0
    assert dernier_jour["t_air"].max() < 30.0 + 0.3
    assert 0 < bilan(res)["chauffage_kWh"] < 150 * 72


def test_pas_de_nan():
    df = meteo.interpoler(meteo.synthetique(jours=2))
    res = simuler(df)
    assert not res.isna().any().any()
