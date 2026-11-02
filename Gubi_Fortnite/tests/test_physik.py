import pytest

from dash.level import ROBOT, SCHIFF, SPIDER, SWING, WUERFEL, Level, LevelFehler
from dash.physik import LAEUFT, TOD, ZIEL, Zustand, fortschritt_pixel, schritt, startzustand
from werkzeuge.schaffbarkeit import pruefen

H = True  # Eingabe gehalten
L = False  # losgelassen


def level(*zeilen, startmodus=WUERFEL):
    """Level aus 8 Rasterzeilen; ein langer leerer Auslauf verhindert ein vorzeitiges Ziel."""
    auslauf = "." * 30
    return Level("test", ["\n".join(z + auslauf for z in zeilen)], startmodus)


LEER = ("........",) * 8


def laufen(lv, eingaben, z=None):
    """Führt die Eingaben aus; gibt die Höhen über dem unteren Rand und das letzte Ergebnis zurück."""
    z = z or startzustand(lv)
    hoehen = []
    ergebnis = LAEUFT
    for gehalten in eingaben:
        ergebnis, z = schritt(lv, z, gehalten)
        hoehen.append(7 - z.y)
        if ergebnis != LAEUFT:
            break
    return hoehen, ergebnis, z


def boden(reihe):
    """Leeres Level, dessen unterste Zeile durch `reihe` ersetzt wird."""
    return LEER[:7] + (reihe,)


# --- Würfel ---------------------------------------------------------------


def test_wuerfel_laeuft_auf_dem_rand():
    hoehen, ergebnis, _ = laufen(level(*LEER), [L] * 5)
    assert hoehen == [0] * 5 and ergebnis == LAEUFT


def test_wuerfelsprung_ist_2_hoch_und_4_spalten_lang():
    hoehen, _, _ = laufen(level(*LEER), [H, L, L, L, L, L])
    assert hoehen == [1, 2, 2, 1, 0, 0]


def test_wuerfel_springt_bei_gehaltener_eingabe_nach_der_landung_erneut():
    hoehen, _, _ = laufen(level(*LEER), [H] * 7)
    assert hoehen == [1, 2, 2, 1, 0, 1, 2]


def test_wuerfel_ueberspringt_drei_spitzen():
    lv = level(*boden("..^^^..."))
    _, ergebnis, _ = laufen(lv, [H, L, L, L, L, L, L])
    assert ergebnis == LAEUFT


def test_vier_spitzen_sind_fuer_den_wuerfel_unschaffbar():
    assert not pruefen(level(*boden("..^^^^.."))).schaffbar


def test_seitlich_gegen_einen_block_ist_tod():
    _, ergebnis, _ = laufen(level(*boden("...#....")), [L] * 4)
    assert ergebnis == TOD


def test_wuerfel_landet_auf_einem_block():
    lv = level(*boden("...#####"))
    hoehen, ergebnis, _ = laufen(lv, [H, L, L, L, L, L])
    assert ergebnis == LAEUFT
    assert hoehen == [1, 2, 2, 1, 1, 1]


def test_wuerfel_faellt_von_einer_kante():
    lv = level(*boden("####...."))
    hoehen, _, _ = laufen(lv, [L] * 5, Zustand(0, 6, WUERFEL))
    assert hoehen == [1, 1, 1, 1, 0]


def test_stoss_von_unten_gegen_einen_block_ist_fuer_den_wuerfel_tod():
    zeilen = list(LEER)
    zeilen[5] = "..######"
    _, ergebnis, _ = laufen(level(*zeilen), [L, H, L, L])
    assert ergebnis == TOD


def test_stoss_gegen_den_oberen_rand_ist_fuer_den_wuerfel_tod():
    zeilen = list(LEER)
    zeilen[2] = "########"
    _, ergebnis, _ = laufen(level(*zeilen), [H, L], Zustand(0, 1, WUERFEL))
    assert ergebnis == TOD


# --- Schiff ---------------------------------------------------------------


def test_schiff_steigt_beim_halten_und_sinkt_beim_loslassen():
    lv = level(*LEER, startmodus=SCHIFF)
    hoehen, _, _ = laufen(lv, [H, H, H, L, L])
    assert hoehen == [1, 2, 3, 2, 1]


def test_schiff_gleitet_am_rand_entlang():
    lv = level(*LEER, startmodus=SCHIFF)
    hoehen, ergebnis, _ = laufen(lv, [H] * 10)
    assert ergebnis == LAEUFT and hoehen[-3:] == [7, 7, 7]


def test_schiff_gleitet_unter_einem_block_entlang():
    zeilen = list(LEER)
    zeilen[5] = "########"
    lv = level(*zeilen, startmodus=SCHIFF)
    hoehen, ergebnis, _ = laufen(lv, [H] * 5)
    assert ergebnis == LAEUFT and hoehen == [1, 1, 1, 1, 1]


# --- Spider ---------------------------------------------------------------


def test_spider_wechselt_sofort_an_den_oberen_rand():
    lv = level(*LEER, startmodus=SPIDER)
    hoehen, _, _ = laufen(lv, [H, L, L])
    assert hoehen == [7, 7, 7]


def test_spider_wechselt_bei_gehaltener_eingabe_nicht_erneut():
    lv = level(*LEER, startmodus=SPIDER)
    hoehen, _, _ = laufen(lv, [H, H, H])
    assert hoehen == [7, 7, 7]


def test_spider_wechselt_bei_jedem_neuen_druck():
    lv = level(*LEER, startmodus=SPIDER)
    hoehen, _, _ = laufen(lv, [H, L, H, L])
    assert hoehen == [7, 7, 0, 0]


def test_spider_landet_unter_einem_block():
    zeilen = list(LEER)
    zeilen[2] = "########"
    lv = level(*zeilen, startmodus=SPIDER)
    hoehen, _, _ = laufen(lv, [H])
    assert hoehen == [4]


def test_spider_stirbt_an_einer_spitze_auf_der_zielseite():
    zeilen = list(LEER)
    zeilen[0] = "v......."
    _, ergebnis, _ = laufen(level(*zeilen, startmodus=SPIDER), [H])
    assert ergebnis == TOD


# --- Swing ----------------------------------------------------------------


def test_swing_fliegt_nach_jedem_wechsel_eine_spalte_geradeaus():
    lv = level(*LEER, startmodus=SWING)
    z = Zustand(0, 4, SWING)
    hoehen, _, _ = laufen(lv, [L, H, L, L, H, L], z)
    assert hoehen == [2, 2, 3, 4, 4, 3]


# --- Robot ----------------------------------------------------------------


def test_robot_kurz_getippt_springt_1_pixel():
    lv = level(*LEER, startmodus=ROBOT)
    hoehen, _, _ = laufen(lv, [H, L, L, L])
    assert hoehen == [1, 1, 0, 0]


def test_robot_lang_gehalten_springt_hoechstens_3_pixel():
    lv = level(*LEER, startmodus=ROBOT)
    hoehen, _, _ = laufen(lv, [H] * 9)
    assert hoehen == [1, 2, 3, 3, 2, 1, 0, 0, 0]


def test_robot_braucht_fuer_jeden_sprung_einen_neuen_druck():
    lv = level(*LEER, startmodus=ROBOT)
    hoehen, _, _ = laufen(lv, [H, L, L, H, L, L])
    assert hoehen == [1, 1, 0, 1, 1, 0]


# --- Sprungpad und Sprungring ----------------------------------------------


def test_sprungpad_loest_einen_sprung_von_4_pixeln_aus():
    hoehen, _, _ = laufen(level(*boden(".=......")), [L] * 10)
    assert hoehen == [0, 1, 2, 3, 4, 4, 3, 2, 1, 0]


def test_sprungpad_wirkt_nicht_auf_das_schiff():
    lv = level(*boden(".=......"), startmodus=SCHIFF)
    hoehen, _, _ = laufen(lv, [L] * 4)
    assert hoehen == [0, 0, 0, 0]


def test_sprungring_loest_einen_sprung_in_der_luft_aus():
    zeilen = list(LEER)
    zeilen[5] = "...o...."
    # Sprung; im Ring (Spalte 3, Höhe 2) erneut drücken
    hoehen, _, _ = laufen(level(*zeilen), [L, H, L, H, L, L, L, L])
    assert hoehen[:7] == [0, 1, 2, 3, 4, 4, 3]


# --- Portal und Ziel -------------------------------------------------------


def test_portal_wechselt_den_modus():
    zeilen = list(LEER)
    zeilen[0] = "...S...."
    _, _, z = laufen(level(*zeilen), [L] * 4)
    assert z.modus == SCHIFF


def test_portal_fuellt_die_ganze_spalte():
    zeilen = list(LEER)
    zeilen[0] = "...S...."
    lv = level(*zeilen)
    assert [lv.feld(3, y) for y in range(8)] == ["S"] * 8


def test_ziel_am_levelende():
    lv = Level("t", ["\n".join(LEER)], WUERFEL)
    _, ergebnis, z = laufen(lv, [L] * 10)
    assert ergebnis == ZIEL
    assert fortschritt_pixel(lv, z, ergebnis) == 64


# --- Levelraster ------------------------------------------------------------


def test_abschnitt_mit_falscher_zeilenzahl_wird_abgelehnt():
    with pytest.raises(LevelFehler):
        Level("t", ["\n".join(LEER[:7])], WUERFEL)


def test_portal_mit_block_in_derselben_spalte_wird_abgelehnt():
    zeilen = list(LEER)
    zeilen[0] = "...S...."
    zeilen[7] = "...#...."
    with pytest.raises(LevelFehler):
        Level("t", ["\n".join(zeilen)], WUERFEL)


def test_abschnitte_werden_aneinandergehaengt():
    lv = Level("t", ["\n".join(LEER), "\n".join(boden("....^..."))], WUERFEL)
    assert lv.laenge == 16 and lv.feld(12, 7) == "^"
