from poulailler.animaux import Lot, chaleur_totale, part_sensible


def test_chaleur_totale_reference_cigr():
    # 10,62 x 2^0,75 = 17,86 W pour un poulet de 2 kg à 20 °C
    assert abs(chaleur_totale(2.0, 20.0) - 17.86) < 0.01


def test_chaleur_totale_baisse_au_chaud():
    assert chaleur_totale(2.0, 32.0) < chaleur_totale(2.0, 20.0) < chaleur_totale(2.0, 10.0)


def test_part_sensible_decroit_avec_la_temperature():
    assert 0.5 < part_sensible(30.0) < part_sensible(20.0) < 0.65


def test_lot_somme_sensible_latente():
    lot = Lot(nombre=1000, masse_kg=1.5)
    qs, ql = lot.chaleur(25.0)
    assert abs(qs + ql - 1000 * chaleur_totale(1.5, 25.0)) < 1e-6
    assert qs > 0 and ql > 0


def test_lot_vide():
    assert Lot(nombre=0).chaleur(20.0) == (0.0, 0.0)
