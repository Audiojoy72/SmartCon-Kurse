#!/usr/bin/env python3
"""WCAG-Kontrast zweier Farben. Ohne Argumente: alle Token-Paare des Themes
(Default-Preset cinematic; bei anderem Preset/design.md die Werte unten anpassen
oder zwei Hex-Farben als Argumente uebergeben).

    python3 kontrast.py "#D97A67" "#101120"
    python3 kontrast.py
"""
import sys

THEME = {
    "--ink": "#F5F3EC", "--goldlt": "#E6CF8A", "--gold": "#C9A84C",
    "--mute": "#989AB2", "--wrong": "#D97A67",
}
BACKGROUNDS = {"--navy": "#060611", "--panel": "#101120", "--panel2": "#17182B"}


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminanz(hexfarbe):
    h = hexfarbe.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def kontrast(a, b):
    la, lb = luminanz(a), luminanz(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def urteil(wert):
    if wert >= 7:
        return "AAA"
    if wert >= 4.5:
        return "AA"
    if wert >= 3:
        return "nur Grossschrift"
    return "DURCHGEFALLEN"


if len(sys.argv) == 3:
    v = kontrast(sys.argv[1], sys.argv[2])
    print(f"{sys.argv[1]} auf {sys.argv[2]}: {v:.2f}:1  ({urteil(v)})")
    sys.exit(0 if v >= 4.5 else 1)

fehler = 0
for bg_name, bg in BACKGROUNDS.items():
    for fg_name, fg in THEME.items():
        v = kontrast(fg, bg)
        note = urteil(v)
        if v < 4.5:
            fehler += 1
        print(f"{fg_name:9s} auf {bg_name:9s} {v:6.2f}:1  {note}")
sys.exit(1 if fehler else 0)
