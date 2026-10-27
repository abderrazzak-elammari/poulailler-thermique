"""Lance une simulation et trace la page de synthèse de l'ambiance.

    python scripts/simuler.py                       # canicule synthétique de 5 jours
    python scripts/simuler.py --meteo meteo/rennes_2022-07.csv --pads 0.7
    python scripts/simuler.py --tmin 4 --tmax 14 --masse 0.3 --consigne 29 --chauffage 150

Le premier jour de météo est joué deux fois et la première passe est jetée,
le temps que la dalle se mette en température

"""
import argparse
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from poulailler import Batiment, Lot, Regulation, meteo, simuler  
from poulailler.modele import bilan 

# couleurs : surface claire, trois encres pour le texte, quelques séries
SURFACE = "#fcfcfb"
ENCRE = "#0b0b0b"
ENCRE_2 = "#52514e"
ENCRE_3 = "#8a8984"
GRILLE = "#e8e7e3"
NUIT = "#f1f0ed"
EXTERIEUR = "#9a9994"       # la météo, en retrait
INTERIEUR = "#2a78d6"       # l'air du bâtiment, la série principale
DALLE = "#eb6834"
ENTRANT = "#1baf7a"
CHAUFFAGE = "#eb6834"
ALERTE = "#d03b3b"          # zone au-dessus du seuil

JOURS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août",
        "sept.", "oct.", "nov.", "déc."]


def fr(x, dec=1):
    """Nombre à la française, virgule décimale, espace fine des milliers."""
    s = f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def _date_fr(x, pos=None):
    d = mdates.num2date(x)
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]}"


def _style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.facecolor": SURFACE,
        "figure.facecolor": SURFACE,
        "axes.edgecolor": GRILLE,
        "axes.linewidth": 0.8,
        "axes.labelcolor": ENCRE_2,
        "axes.titlecolor": ENCRE,
        "xtick.color": ENCRE_2,
        "ytick.color": ENCRE_2,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "grid.color": GRILLE,
        "grid.linewidth": 0.8,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
    })


def _axe_sobre(ax, ylabel):
    ax.set_facecolor(SURFACE)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(GRILLE)
    ax.grid(axis="y", lw=0.8, color=GRILLE)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="both", length=0, pad=4)
    ax.set_ylabel(ylabel, fontsize=8.5, color=ENCRE_2, labelpad=6)
    ax.margins(x=0)


def _nuits(ax, res):
    """Grise les heures sans soleil, pour lire le cycle jour-nuit."""
    nuit = res["rayonnement"].to_numpy() <= 0.0
    t = res.index
    debut = None
    for i in range(len(t)):
        if nuit[i] and debut is None:
            debut = t[i]
        if (not nuit[i] or i == len(t) - 1) and debut is not None:
            ax.axvspan(debut, t[i], color=NUIT, lw=0, zorder=0)
            debut = None


def _zone_alerte(ax, res, seuil, etiquette=True):
    chaud = (res["t_air"] > seuil).to_numpy()
    if not chaud.any():
        return
    y0, y1 = ax.get_ylim()
    ax.fill_between(res.index, y0, y1, where=chaud, color=ALERTE, alpha=0.08, lw=0, zorder=0.5)
    if etiquette:
        i = int(np.argmax(chaud))
        ax.text(res.index[i], y1 - 0.04 * (y1 - y0), f"  air intérieur > {fr(seuil, 0)} °C",  color=ALERTE, fontsize=8, va="top", ha="left", zorder=5)


def _tuile(ax, titre, valeur, note):
    ax.set_axis_off()
    ax.text(0.0, 0.95, titre, transform=ax.transAxes, fontsize=8.5, color=ENCRE_2,  va="top", ha="left")
    ax.text(0.0, 0.52, valeur, transform=ax.transAxes, fontsize=22, color=ENCRE, fontweight="bold", va="center", ha="left")
    ax.text(0.0, 0.08, note, transform=ax.transAxes, fontsize=8, color=ENCRE_3, va="bottom", ha="left")
    ax.plot([0, 1], [0.0, 0.0], transform=ax.transAxes, color=GRILLE, lw=0.8, clip_on=False)


def _annoter_max(ax, serie, couleur, unite="°C"):
    i = serie.idxmax()
    v = serie.max()
    a_droite = (i - serie.index[0]) < 0.85 * (serie.index[-1] - serie.index[0])
    ax.plot([i], [v], marker="o", ms=7, mfc=couleur, mec=SURFACE, mew=1.5, zorder=6)
    ax.annotate(f"{fr(v)} {unite}", (i, v), xytext=(8 if a_droite else -8, 8),
                textcoords="offset points", fontsize=9, color=ENCRE, fontweight="bold", va="bottom", ha="left" if a_droite else "right", zorder=6)


def tracer(res, reg, chemin, seuil=30.0, titre=None, sous_titre=None, lot=None, bat=None):
    _style()
    b = bilan(res, seuil)
    chauffe = res["chauffage_W"].max() > 0
    pads = reg.pad_efficacite > 0

    fig = plt.figure(figsize=(12, 10.2 if chauffe else 9.2))
    hauteurs = [0.55, 1.6, 1.0, 0.8] + ([0.8] if chauffe else [])
    gs = GridSpec(len(hauteurs), 4, figure=fig, height_ratios=hauteurs,
                  left=0.07, right=0.985, top=0.90, bottom=0.06, hspace=0.42, wspace=0.35)

    # titre
    jours = (res.index[-1] - res.index[0]).total_seconds() / 86400.0
    if titre is None:
        titre = "Ambiance d'un bâtiment de poulets de chair"
    if sous_titre is None:
        morceaux = []
        if bat is not None:
            morceaux.append(f"{fr(bat.surface, 0)} m²")
        if lot is not None:
            morceaux.append(f"{fr(lot.nombre, 0)} animaux de {fr(lot.masse_kg)} kg")
        morceaux.append(f"consigne {fr(reg.consigne, 0)} °C")
        morceaux.append(f"pads de cooling à {fr(100 * reg.pad_efficacite, 0)} %" if pads
                        else "sans cooling")
        if chauffe:
            morceaux.append(f"chauffage {fr(reg.chauffage_max / 1e3, 0)} kW")
        morceaux.append(f"{fr(jours, 0)} jours, du {_date_fr(mdates.date2num(res.index[0]))} "
                        f"au {_date_fr(mdates.date2num(res.index[-1]))}")
        sous_titre = "  ·  ".join(morceaux)
    fig.text(0.07, 0.965, titre, fontsize=16, color=ENCRE, fontweight="bold", va="top")
    fig.text(0.07, 0.932, sous_titre, fontsize=9.5, color=ENCRE_2, va="top")

    #  chiffres clés
    tuiles = [
        ("Maximum de l'air intérieur", f"{fr(b['t_air_max'])} °C",
         f"extérieur {fr(b['t_ext_max'])} °C, écart max {fr(b['ecart_int_ext_max'])} K"),
        (f"Heures au-dessus de {fr(seuil, 0)} °C", f"{fr(b['heures_au_dessus_seuil'], 0)} h",
         f"sur {fr(np.round(jours + 1 / 24), 0)} jours simulés"),
        ("THI maximal", fr(b["thi_max"]), "indice de Tao et Xin (2003)"),
    ]
    if chauffe:
        tuiles.append(("Énergie de chauffage", f"{fr(b['chauffage_kWh'], 0)} kWh",
                       f"puissance installée {fr(reg.chauffage_max / 1e3, 0)} kW"))
    else:
        tuiles.append(("Ventilation moyenne", f"{fr(b['debit_moyen_m3h_kg'])} m³/h·kg",
                       f"plage {fr(reg.debit_min)} à {fr(reg.debit_max)} m³/h par kg vif"))
    for k, (t, v, n) in enumerate(tuiles):
        _tuile(fig.add_subplot(gs[0, k]), t, v, n)

    # températures
    ax1 = fig.add_subplot(gs[1, :])
    _axe_sobre(ax1, "température (°C)")
    _nuits(ax1, res)
    ax1.plot(res.index, res["t_ext"], color=EXTERIEUR, lw=1.3, label="extérieur")
    if pads:
        ax1.plot(res.index, res["t_entrant"], color=ENTRANT, lw=1.3, label="air entrant après pads")
    ax1.plot(res.index, res["t_masse"], color=DALLE, lw=1.3, label="dalle et litière")
    ax1.plot(res.index, res["t_air"], color=INTERIEUR, lw=2.0, label="air intérieur", zorder=4)
    ax1.axhline(reg.consigne, color=ENCRE_3, lw=0.9, ls=(0, (4, 3)), zorder=1,
                label=f"consigne {fr(reg.consigne, 0)} °C")
    lo = min(res["t_ext"].min(), res["t_air"].min(), res["t_masse"].min())
    hi = max(res["t_ext"].max(), res["t_air"].max(), res["t_masse"].max())
    ax1.set_ylim(np.floor(lo / 5) * 5, np.ceil(hi / 5) * 5 + 2)
    _zone_alerte(ax1, res, seuil)
    _annoter_max(ax1, res["t_air"], INTERIEUR)
    ax1.legend(loc="upper left", ncol=5, handlelength=1.8, bbox_to_anchor=(0, 1.13))
    ax1.set_title("Températures", loc="left", fontsize=10.5, fontweight="bold", pad=22)

    # humidité
    ax2 = fig.add_subplot(gs[2, :], sharex=ax1)
    _axe_sobre(ax2, "humidité relative (%)")
    _nuits(ax2, res)
    ax2.plot(res.index, res["hr_ext"], color=EXTERIEUR, lw=1.3, label="extérieur")
    ax2.plot(res.index, res["hr_air"], color=INTERIEUR, lw=2.0, label="air intérieur", zorder=4)
    ax2.set_ylim(0, 100)
    ax2.set_yticks([0, 25, 50, 75, 100])
    _zone_alerte(ax2, res, seuil, etiquette=False)
    ax2.legend(loc="upper left", ncol=2, handlelength=1.8, bbox_to_anchor=(0, 1.2))
    ax2.set_title("Humidité", loc="left", fontsize=10.5, fontweight="bold", pad=22)

    # ventilation
    ax3 = fig.add_subplot(gs[3, :], sharex=ax1)
    _axe_sobre(ax3, "m³/h par kg vif")
    _nuits(ax3, res)
    ax3.fill_between(res.index, 0, res["debit_m3h_kg"], color=INTERIEUR, alpha=0.07, lw=0)
    ax3.plot(res.index, res["debit_m3h_kg"], color=INTERIEUR, lw=2.0, zorder=4)
    ax3.set_ylim(0, reg.debit_max * 1.15)
    ax3.set_yticks([0, reg.debit_min, reg.debit_max])
    _zone_alerte(ax3, res, seuil, etiquette=False)
    ax3.set_title("Débit de ventilation", loc="left", fontsize=10.5, fontweight="bold", pad=6)

    # chauffage
    axes = [ax1, ax2, ax3]
    if chauffe:
        ax4 = fig.add_subplot(gs[4, :], sharex=ax1)
        _axe_sobre(ax4, "kW")
        _nuits(ax4, res)
        ax4.fill_between(res.index, 0, res["chauffage_W"] / 1e3, color=CHAUFFAGE, alpha=0.07, lw=0)
        ax4.plot(res.index, res["chauffage_W"] / 1e3, color=CHAUFFAGE, lw=2.0, zorder=4)
        ax4.set_ylim(0, reg.chauffage_max / 1e3 * 1.15)
        ax4.set_title("Puissance de chauffage", loc="left", fontsize=10.5, fontweight="bold", pad=6)
        axes.append(ax4)

    for ax in axes[:-1]:
        plt.setp(ax.get_xticklabels(), visible=False)
    axes[-1].xaxis.set_major_locator(mdates.DayLocator())
    axes[-1].xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_date_fr))
    axes[-1].xaxis.set_minor_locator(mdates.HourLocator(byhour=[12]))
    for ax in axes:
        ax.tick_params(axis="x", which="both", length=0)
    for lab in axes[-1].get_xticklabels():
        lab.set_ha("left")

    fig.text(0.985, 0.06 - 0.045, "zones grisées : nuit (rayonnement nul)", fontsize=8,
             color=ENCRE_3, ha="right", va="top")

    fig.savefig(chemin, dpi=170, facecolor=SURFACE)
    plt.close(fig)


def avec_mise_en_regime(df_h):
    """Préfixe la série horaire par une copie de son premier jour."""
    premier = df_h.iloc[:24].copy()
    premier.index = premier.index - pd.Timedelta(days=1)
    return pd.concat([premier, df_h])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--meteo", help="CSV horaire (temps, t_ext, hr_ext, rayonnement)")
    p.add_argument("--jours", type=int, default=5, help="durée de la météo synthétique")
    p.add_argument("--tmin", type=float, default=18.0, help="minimum nocturne de la météo synthétique (°C)")
    p.add_argument("--tmax", type=float, default=36.0, help="maximum du premier jour de la météo synthétique (°C)")
    p.add_argument("--debut", default="2022-07-14", help="premier jour de la météo synthétique (AAAA-MM-JJ)")
    p.add_argument("--nb", type=int, default=22000, help="nombre d'animaux")
    p.add_argument("--masse", type=float, default=2.0, help="masse vive moyenne (kg)")
    p.add_argument("--consigne", type=float, default=22.0, help="consigne de température (°C)")
    p.add_argument("--pads", type=float, default=0.0, help="efficacité des pads de cooling, 0 à 1")
    p.add_argument("--chauffage", type=float, default=0.0, help="puissance de chauffage (kW)")
    p.add_argument("--seuil", type=float, default=30.0, help="seuil d'inconfort tracé (°C)")
    p.add_argument("--titre", help="titre de la figure")
    p.add_argument("--figure", default="figures/ambiance.png")
    p.add_argument("--csv", help="écrire les résultats au pas de 10 min dans ce fichier")
    args = p.parse_args()

    if args.meteo:
        df_h = meteo.lire_csv(args.meteo)
    else:
        df_h = meteo.synthetique(jours=args.jours, t_min=args.tmin, t_max=args.tmax, debut=args.debut)
    df = meteo.interpoler(avec_mise_en_regime(df_h))

    lot = Lot(nombre=args.nb, masse_kg=args.masse)
    reg = Regulation(consigne=args.consigne, pad_efficacite=args.pads,
                     chauffage_max=args.chauffage * 1e3)
    bat = Batiment()
    res = simuler(df, bat, lot, reg)
    res = res[res.index >= df_h.index[0]] 

    for k, v in bilan(res, args.seuil).items():
        print(f"{k:26s} {v:10.2f}")

    os.makedirs(os.path.dirname(args.figure) or ".", exist_ok=True)
    titre = args.titre
    if titre is None:
        titre = ("Ambiance d'un bâtiment de poulets de chair, "
                 + (f"météo {os.path.basename(args.meteo)}" if args.meteo else "canicule synthétique"))
    tracer(res, reg, args.figure, args.seuil, titre=titre, lot=lot, bat=bat)
    print(f"figure : {args.figure}")

    if args.csv:
        res.resample("10min").mean().to_csv(args.csv, float_format="%.3f")
        print(f"résultats : {args.csv}")


if __name__ == "__main__":
    main()