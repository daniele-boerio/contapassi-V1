#!/usr/bin/env python3
"""Disegna i due footprint che non esistono a catalogo: piazzole pogo e cella.

Non sono componenti: sono contatti e punti di saldatura a mano. Quindi niente
pasta saldante (solo rame e apertura solder mask) e niente riga nel file CPL.

I numeri in cima sono i soli da toccare quando arriva il cavo magnetico vero:
il passo dei contatti deve corrispondere al suo.

    python hardware/tools/gen_footprints.py
"""
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PRETTY = os.path.join(os.path.dirname(HERE), "lib", "contapassi.pretty")

# ---------------------------------------------------------------- parametri
POGO_PITCH = 5.0    # interasse dei due contatti [mm] -> DAL CAVO MAGNETICO
POGO_DIA = 3.0      # diametro della piazzola [mm]: il puntale deve centrarla
                    # anche con qualche decimo di disallineamento

CELL_PITCH = 4.0    # interasse dei due fori della cella [mm]
CELL_DRILL = 1.0    # foro [mm]: ci passa il filo della cella, che sta sul retro
CELL_PAD = 1.9      # diametro della corona di rame [mm]

NL = chr(10)
TAB = chr(9)


def uid():
    return str(uuid.uuid4())


def header(name, descr, tags):
    return (
        '(footprint "%s"' + NL +
        TAB + '(version 20241229)' + NL +
        TAB + '(generator "contapassi/gen_footprints.py")' + NL +
        TAB + '(generator_version "9.0")' + NL +
        TAB + '(layer "F.Cu")' + NL +
        TAB + '(descr "%s")' + NL +
        TAB + '(tags "%s")' + NL +
        TAB + '(attr smd exclude_from_pos_files exclude_from_bom)' + NL
    ) % (name, descr, tags)


def text(kind, value, x, y, layer):
    return (
        TAB + '(property "%s" "%s"' + NL +
        TAB * 2 + '(at %.3f %.3f 0)' + NL +
        TAB * 2 + '(layer "%s")' + NL +
        TAB * 2 + '(uuid "%s")' + NL +
        TAB * 2 + '(effects (font (size 1 1) (thickness 0.15)))' + NL +
        TAB + ')' + NL
    ) % (kind, value, x, y, layer, uid())


def smd_pad(num, shape, x, y, w, h):
    """Contatto: rame e apertura maschera, MAI pasta saldante."""
    extra = (TAB * 2 + '(roundrect_rratio 0.25)' + NL) if shape == "roundrect" else ""
    return (
        TAB + '(pad "%s" smd %s' + NL +
        TAB * 2 + '(at %.3f %.3f)' + NL +
        TAB * 2 + '(size %.3f %.3f)' + NL +
        TAB * 2 + '(layers "F.Cu" "F.Mask")' + NL +
        '%s' +
        TAB * 2 + '(uuid "%s")' + NL +
        TAB + ')' + NL
    ) % (num, shape, x, y, w, h, extra, uid())


def th_pad(num, x, y, dia, drill):
    """Foro passante: il filo della cella sale dal retro e si salda davanti."""
    return (
        TAB + '(pad "%s" thru_hole circle' + NL +
        TAB * 2 + '(at %.3f %.3f)' + NL +
        TAB * 2 + '(size %.3f %.3f)' + NL +
        TAB * 2 + '(drill %.3f)' + NL +
        TAB * 2 + '(layers "*.Cu" "*.Mask")' + NL +
        TAB * 2 + '(uuid "%s")' + NL +
        TAB + ')' + NL
    ) % (num, x, y, dia, dia, drill, uid())


def line(x1, y1, x2, y2, layer, width=0.12):
    return (
        TAB + '(fp_line (start %.3f %.3f) (end %.3f %.3f)' + NL +
        TAB * 2 + '(stroke (width %.2f) (type solid))' + NL +
        TAB * 2 + '(layer "%s") (uuid "%s")' + NL +
        TAB + ')' + NL
    ) % (x1, y1, x2, y2, width, layer, uid())


def rect(x1, y1, x2, y2, layer, width=0.05):
    return "".join([line(x1, y1, x2, y1, layer, width),
                    line(x2, y1, x2, y2, layer, width),
                    line(x2, y2, x1, y2, layer, width),
                    line(x1, y2, x1, y1, layer, width)])


def silk_text(value, x, y, layer="F.SilkS", size=0.8):
    return (
        TAB + '(fp_text user "%s"' + NL +
        TAB * 2 + '(at %.3f %.3f 0)' + NL +
        TAB * 2 + '(layer "%s")' + NL +
        TAB * 2 + '(uuid "%s")' + NL +
        TAB * 2 + '(effects (font (size %.2f %.2f) (thickness 0.12)))' + NL +
        TAB + ')' + NL
    ) % (value, x, y, layer, uid(), size, size)


def pogo():
    name = "PogoPads_2P_P%.1fmm" % POGO_PITCH
    hp = POGO_PITCH / 2.0
    r = POGO_DIA / 2.0
    cx = hp + r + 0.5
    cy = r + 0.5
    s = header(name,
               "Piazzole di contatto per cavo di ricarica magnetico a 2 pin. "
               "Solo rame e maschera: nessuna pasta, nessun componente montato. "
               "Richiede finitura ENIG. Passo da adeguare al cavo scelto.",
               "pogo magnetic charger contact pad")
    s += text("Reference", "J**", 0, -cy - 1.2, "F.SilkS")
    s += text("Value", name, 0, cy + 1.2, "F.Fab")
    s += smd_pad("1", "circle", -hp, 0, POGO_DIA, POGO_DIA)
    s += smd_pad("2", "circle", +hp, 0, POGO_DIA, POGO_DIA)
    # il segno "+" marca il contatto 1
    s += line(-hp - 0.6, -r - 0.8, -hp + 0.6, -r - 0.8, "F.SilkS", 0.15)
    s += line(-hp, -r - 1.4, -hp, -r - 0.2, "F.SilkS", 0.15)
    s += rect(-cx, -cy, cx, cy, "F.CrtYd")
    s += rect(-cx, -cy, cx, cy, "F.Fab")
    s += ")" + NL
    return name, s


def cell():
    name = "CellPads_2P_P%.1fmm" % CELL_PITCH
    hp = CELL_PITCH / 2.0
    cx = hp + CELL_PAD / 2 + 0.5
    cy = CELL_PAD / 2 + 0.5
    s = header(name,
               "Fori passanti per i due fili della cella LiPo. La cella e' "
               "incollata sul retro: il filo passa nel foro e si salda davanti, "
               "senza girare attorno al bordo scheda.",
               "battery lipo wire through hole")
    s += text("Reference", "J**", 0, -cy - 1.2, "F.SilkS")
    s += text("Value", name, 0, cy + 1.2, "F.Fab")
    s += th_pad("1", -hp, 0, CELL_PAD, CELL_DRILL)
    s += th_pad("2", +hp, 0, CELL_PAD, CELL_DRILL)
    s += silk_text("+", -hp, -cy - 0.1)
    s += silk_text("-", +hp, -cy - 0.1)
    s += rect(-cx, -cy, cx, cy, "F.CrtYd")
    s += rect(-cx, -cy, cx, cy, "F.Fab")
    s += ")" + NL
    return name, s


def main():
    os.makedirs(PRETTY, exist_ok=True)
    for name, body in (pogo(), cell()):
        path = os.path.join(PRETTY, name + ".kicad_mod")
        open(path, "w", encoding="utf-8").write(body)
        print("scritto %s" % path)


if __name__ == "__main__":
    main()
