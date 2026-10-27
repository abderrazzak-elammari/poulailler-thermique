import numpy as np

from poulailler import air


def test_pression_saturante_20_degres():
    # valeur tabulée : 2339 Pa, Magnus donne 2333, c'est dans les 0,3 %
    assert abs(air.p_sat(20.0) - 2339.0) / 2339.0 < 0.005


def test_humidite_absolue_aller_retour():
    for t, hr in [(5.0, 90.0), (20.0, 50.0), (35.0, 30.0)]:
        w = air.humidite_absolue(t, hr)
        assert abs(air.humidite_relative(t, w) - hr) < 1e-6


def test_humidite_absolue_valeur_connue():
    # air à 20 °C et 50 % : 7,3 g d'eau par kg d'air sec d'après le diagramme
    assert abs(air.humidite_absolue(20.0, 50.0) - 0.0073) < 0.0002


def test_temperature_humide_exemple_stull():
    # l'exemple de l'article de Stull (2011) : 20 °C, 50 % -> 13,7 °C
    assert abs(air.temperature_humide(20.0, 50.0) - 13.7) < 0.1


def test_temperature_humide_sous_la_seche():
    t = np.array([10.0, 25.0, 40.0])
    hr = np.array([30.0, 60.0, 90.0])
    tw = air.temperature_humide(t, hr)
    assert np.all(tw < t)
    assert np.all(tw > t - 20.0)


def test_thi_croit_avec_humidite():
    assert air.thi_volailles(32.0, 80.0) > air.thi_volailles(32.0, 30.0)
