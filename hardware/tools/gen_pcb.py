#!/usr/bin/env python3
"""Genera la prima stesura del PCB: contorno, piazzamento, keepout, piani di massa.

Non instrada niente: le piste si tirano a mano in pcbnew. Qui c'e' la geometria,
che e' la parte dove un errore costa un giro di produzione.

La netlist arriva da gen_schematic.COMPONENTS: unica fonte, mai riscritta a mano.

Disposizione "corta e larga" (doc 01 §7), scheda 24 x 41 mm, origine in alto a
sinistra, Y crescente verso il basso:

    Y 0-21   zona cella   cella 12 x 20 sotto, a destra (X 11-23)
                          a sinistra (X 1-10) resta libero: carica e alimentazione
    Y 22-40  zona modulo  modulo a sinistra (X 1-14), striscia componenti a destra
    Y 38-41  ANTENNA      keepout su tutti gli strati, tutta la larghezza

    python hardware/tools/gen_pcb.py
"""
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
KI_FP = r"C:\Program Files\KiCad\9.0\share\kicad\footprints"
OUT = os.path.join(HW, "contapassi.kicad_pcb")

sys.path.insert(0, HERE)
from gen_schematic import COMPONENTS  # noqa: E402
import route as router  # noqa: E402

# ------------------------------------------------------------------ geometria
OFF_X, OFF_Y = 100.0, 60.0     # posizione della scheda sul foglio
BW, BH = 24.0, 41.0            # scheda: larghezza x lunghezza
ANT_Y = 37.4                   # oltre questa Y c'e' l'antenna: niente rame
CELL = (11.0, 1.0, 23.0, 21.0) # ingombro cella sul retro (x1, y1, x2, y2)

# ref -> (x, y) in coordinate scheda. Tutto a rotazione 0: ruotare in pcbnew
# se serve, cosi' il file resta semplice e verificabile.
PLACEMENT = {
    # --- zona modulo: modulo a sinistra, striscia componenti a destra -------
    "U1": (8.0, 29.5),     # modulo: antenna verso Y alta, y 22,5-40,5
    "Y1": (17.5, 23.7),    # quarzo, vicino a XL1/XL2 (pad a X 11,2-12,5 / Y 22,5)
    "C1": (20.7, 23.2),
    "C2": (22.7, 23.2),
    "U2": (17.3, 26.5),    # IMU, vicino ai pad SPI del modulo
    "C7": (21.4, 24.9),
    "C8": (21.4, 26.3),
    "C9": (21.4, 27.7),
    "U3": (18.45, 32.8),   # flash 6x8: il pezzo piu' grande della striscia
    "R2": (22.7, 30.5),
    "R3": (22.7, 32.5),
    "R4": (22.7, 34.5),
    # --- zona cella, meta' sinistra libera: carica e alimentazione ----------
    "J1": (5.5, 3.0),      # piazzole pogo, estremita' opposta all'antenna
    "D1": (2.5, 6.8),
    "Q1": (6.0, 6.8),
    "R8": (9.0, 6.8),
    "R5": (2.0, 9.5),
    "R7": (4.5, 9.5),
    "D2": (7.5, 9.5),
    "U4": (2.5, 12.0),
    "C10": (6.0, 12.0),
    "R6": (9.0, 12.0),
    "C3": (3.0, 15.5),     # bulk 47 uF
    "J2": (8.8, 15.5),     # fori per i fili: entrambi FUORI dall'ingombro cella
    "L1": (2.5, 18.5),     # induttore REG0: il piu' vicino possibile a DCH
    "C4": (5.8, 18.5),
    "C5": (9.0, 18.5),
    "C6": (2.5, 20.8),
    "R1": (7.0, 20.6),     # pull-up CS_IMU: sta bene ovunque
    # --- pad di test: solo rame, possono stare sopra la cella --------------
    "TP1": (13.0, 8.0),
    "TP2": (16.0, 8.0),
    "TP3": (19.0, 8.0),
    "TP4": (22.0, 8.0),
    "TP5": (14.5, 11.5),
    "TP6": (17.5, 11.5),
}

# Pad senza numero: le via termiche dentro l'exposed pad della flash. Vanno
# alla stessa rete dell'EP, altrimenti il DRC le vede come rame scollegato.
EXTRA_PAD_NETS = {"U3": {"": "GND"}}

FP_DIRS = [os.path.join(HW, "lib", "contapassi.pretty")] + [
    os.path.join(KI_FP, d) for d in os.listdir(KI_FP) if d.endswith(".pretty")
]


def uid():
    return str(uuid.uuid4())


def find_fp(lib_id):
    lib, name = lib_id.split(":", 1)
    for d in FP_DIRS:
        if os.path.basename(d) == lib + ".pretty":
            p = os.path.join(d, name + ".kicad_mod")
            if os.path.exists(p):
                return open(p, encoding="utf-8").read()
    raise FileNotFoundError(lib_id)


def strip_head(txt, lib_id):
    """Toglie version/generator/generator_version: dentro il .kicad_pcb non vanno."""
    txt = re.sub(r'\(footprint\s+"[^"]+"', '(footprint "%s"' % lib_id, txt, count=1)
    for tag in ("version", "generator_version", "generator"):
        txt = re.sub(r'\n\s*\(%s [^)]*\)' % tag, "", txt, count=1)
    return txt


PAD_RE = re.compile(
    r'\(pad\s+"([^"]*)"\s+(smd|thru_hole|np_thru_hole)\s+\w+'
    r'[\s\S]*?\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)'
    r'[\s\S]*?\(size\s+([\d.]+)\s+([\d.]+)\)')


def pads_of(txt, x0, y0, nets):
    """Pad in coordinate scheda: posizione, ingombro, rete, foro passante."""
    out = []
    for m in PAD_RE.finditer(txt):
        num, kind, px, py, rot, w, h = m.groups()
        w, h = float(w), float(h)
        if rot and int(float(rot)) % 180 == 90:
            w, h = h, w
        net = nets.get(num)
        if not net:
            continue
        out.append({"num": num, "x": x0 + float(px), "y": y0 + float(py),
                    "w": w, "h": h, "net": net, "th": kind != "smd"})
    return out


def set_pad_nets(txt, nets_by_pad):
    """Aggiunge (net n "nome") a ogni pad che ha una rete."""
    out = []
    i = 0
    for m in re.finditer(r'\(pad\s+"([^"]*)"\s', txt):
        num = m.group(1)
        # fine del blocco pad
        depth = 0
        j = m.start()
        while True:
            if txt[j] == "(":
                depth += 1
            elif txt[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        blk = txt[m.start():j]
        if num in nets_by_pad:
            code, name = nets_by_pad[num]
            blk += '\n\t\t(net %d "%s")' % (code, name)
        out.append(txt[i:m.start()])
        out.append(blk)
        i = j
    out.append(txt[i:])
    return "".join(out)


LAYERS = """\t(layers
\t\t(0 "F.Cu" signal)
\t\t(1 "In1.Cu" signal "GND")
\t\t(2 "In2.Cu" signal)
\t\t(31 "B.Cu" signal)
\t\t(32 "B.Adhes" user "B.Adhesive")
\t\t(33 "F.Adhes" user "F.Adhesive")
\t\t(34 "B.Paste" user)
\t\t(35 "F.Paste" user)
\t\t(36 "B.SilkS" user "B.Silkscreen")
\t\t(37 "F.SilkS" user "F.Silkscreen")
\t\t(38 "B.Mask" user)
\t\t(39 "F.Mask" user)
\t\t(40 "Dwgs.User" user "User.Drawings")
\t\t(41 "Cmts.User" user "User.Comments")
\t\t(42 "Eco1.User" user "User.Eco1")
\t\t(43 "Eco2.User" user "User.Eco2")
\t\t(44 "Edge.Cuts" user)
\t\t(45 "Margin" user)
\t\t(46 "B.CrtYd" user "B.Courtyard")
\t\t(47 "F.CrtYd" user "F.Courtyard")
\t\t(48 "B.Fab" user)
\t\t(49 "F.Fab" user)
\t)
"""

SETUP = """\t(setup
\t\t(pad_to_mask_clearance 0)
\t\t(allow_soldermask_bridges_in_footprints yes)
\t\t(pcbplotparams
\t\t\t(layerselection 0x00000000_00000000_55555555_5755f5ff)
\t\t\t(plot_on_all_layers_selection 0x0000000_00000000_00000000_00000000)
\t\t\t(disableapertmacros no) (usegerberextensions no) (usegerberattributes yes)
\t\t\t(usegerberadvancedattributes yes) (creategerberjobfile yes)
\t\t\t(dashed_line_dash_ratio 12.000000) (dashed_line_gap_ratio 3.000000)
\t\t\t(svgprecision 4) (plotframeref no) (mode 1) (useauxorigin no)
\t\t\t(dxfpolygonmode yes) (dxfimperialunits yes) (dxfusepcbnewfont yes)
\t\t\t(psnegative no) (psa4output no) (plot_black_and_white yes)
\t\t\t(sketchpadsonfab no) (plotpadnumbers no) (hidednponfab no)
\t\t\t(sketchdnponfab yes) (crossoutdnponfab yes) (subtractmaskfromsilk no)
\t\t\t(outputformat 1) (mirror no) (drillshape 1) (scaleselection 1)
\t\t\t(outputdirectory "")
\t\t)
\t)
"""


def line(x1, y1, x2, y2, layer, width=0.1):
    return ('\t(gr_line (start %.3f %.3f) (end %.3f %.3f)\n'
            '\t\t(stroke (width %.3f) (type solid)) (layer "%s") (uuid "%s")\n\t)\n'
            % (OFF_X + x1, OFF_Y + y1, OFF_X + x2, OFF_Y + y2, width, layer, uid()))


def poly(pts):
    return "\t\t\t(pts\n" + "".join(
        "\t\t\t\t(xy %.3f %.3f)\n" % (OFF_X + x, OFF_Y + y) for x, y in pts) + "\t\t\t)\n"


def keepout(name, pts, layers, pads="allowed", footprints="allowed"):
    """Area vietata. I pad del modulo stesso stanno per forza dentro l'area
    dell'antenna: quello che va vietato sono piste, via e riempimenti."""
    return ('\t(zone\n\t\t(net 0)\n\t\t(net_name "")\n\t\t(layers %s)\n'
            '\t\t(uuid "%s")\n\t\t(name "%s")\n\t\t(hatch edge 0.5)\n'
            '\t\t(connect_pads (clearance 0))\n\t\t(min_thickness 0.25)\n'
            '\t\t(filled_areas_thickness no)\n'
            '\t\t(keepout (tracks not_allowed) (vias not_allowed) (pads %s)\n'
            '\t\t\t(copperpour not_allowed) (footprints %s))\n'
            '\t\t(fill (thermal_gap 0.5) (thermal_bridge_width 0.5))\n'
            '\t\t(polygon\n%s\t\t)\n\t)\n'
            % (" ".join('"%s"' % l for l in layers), uid(), name,
               pads, footprints, poly(pts)))


def plane(layer, code, name, pts):
    return ('\t(zone\n\t\t(net %d)\n\t\t(net_name "%s")\n\t\t(layer "%s")\n'
            '\t\t(uuid "%s")\n\t\t(name "%s %s")\n\t\t(hatch edge 0.5)\n'
            '\t\t(connect_pads (clearance 0.2))\n\t\t(min_thickness 0.25)\n'
            '\t\t(filled_areas_thickness no)\n'
            '\t\t(fill yes (thermal_gap 0.3) (thermal_bridge_width 0.3))\n'
            '\t\t(polygon\n%s\t\t)\n\t)\n'
            % (code, name, layer, uid(), name, layer, poly(pts)))


def seg(x1, y1, x2, y2, layer, code):
    return ('\t(segment (start %.3f %.3f) (end %.3f %.3f) (width %.2f)'
            ' (layer "%s") (net %d) (uuid "%s"))\n'
            % (OFF_X + x1, OFF_Y + y1, OFF_X + x2, OFF_Y + y2,
               router.TRACK_W, layer, code, uid()))


def via(x, y, code):
    return ('\t(via (at %.3f %.3f) (size %.2f) (drill %.2f)'
            ' (layers "F.Cu" "B.Cu") (net %d) (uuid "%s"))\n'
            % (OFF_X + x, OFF_Y + y, router.VIA_DIA, router.VIA_DRILL,
               code, uid()))


def main():
    # ---- reti ------------------------------------------------------------
    names = sorted({n for c in COMPONENTS for n in c[6].values()})
    code = {n: i + 1 for i, n in enumerate(names)}
    nets = '\t(net 0 "")\n' + "".join(
        '\t(net %d "%s")\n' % (code[n], n) for n in names)

    # ---- footprint -------------------------------------------------------
    body = []
    mancanti = []
    tutti_pad = []
    for ref, lib_id, val, fp, lcsc, at, pinnets in COMPONENTS:
        if ref.startswith("#"):
            continue
        if ref not in PLACEMENT:
            mancanti.append(ref)
            continue
        x, y = PLACEMENT[ref]
        txt = strip_head(find_fp(fp), fp)
        pn = {p: (code[n], n) for p, n in pinnets.items()}
        # pad senza numero (via termiche nell'exposed pad): stessa rete dell'EP
        for p, n in EXTRA_PAD_NETS.get(ref, {}).items():
            pn[p] = (code[n], n)
        txt = set_pad_nets(txt, pn)
        # riferimento, valore, posizione
        txt = re.sub(r'\(property "Reference" "[^"]*"', '(property "Reference" "%s"' % ref, txt, count=1)
        # sigle sul lato fabbricazione, non in serigrafia: la scheda e' troppo
        # piccola perche' le scritte non si sovrappongano ai componenti
        txt = re.sub(r'(\(property "Reference"[\s\S]{0,120}?\(layer ")F\.SilkS(")',
                     r'\1F.Fab\2', txt, count=1)
        txt = re.sub(r'\(property "Value" "[^"]*"', '(property "Value" "%s"' % val, txt, count=1)
        head = '(footprint "%s"\n\t\t(layer "F.Cu")\n\t\t(uuid "%s")\n\t\t(at %.3f %.3f)' % (
            fp, uid(), OFF_X + x, OFF_Y + y)
        txt = re.sub(r'\(footprint "[^"]*"\n?\s*\(layer "[^"]*"\)', head, txt, count=1)
        if not txt.startswith("(footprint"):
            raise ValueError(ref)
        body.append("\t" + txt.strip() + "\n")
        tutti_pad.extend(pads_of(txt, x, y, {p: n for p, n in pinnets.items()}))

    # ---- contorno --------------------------------------------------------
    edge = "".join([line(0, 0, BW, 0, "Edge.Cuts"), line(BW, 0, BW, BH, "Edge.Cuts"),
                    line(BW, BH, 0, BH, "Edge.Cuts"), line(0, BH, 0, 0, "Edge.Cuts")])

    # ---- ingombro cella, disegnato per riferimento -----------------------
    x1, y1, x2, y2 = CELL
    edge += "".join([line(x1, y1, x2, y1, "Dwgs.User", 0.15),
                     line(x2, y1, x2, y2, "Dwgs.User", 0.15),
                     line(x2, y2, x1, y2, "Dwgs.User", 0.15),
                     line(x1, y2, x1, y1, "Dwgs.User", 0.15)])

    # ---- keepout antenna: tutti gli strati, tutta la larghezza -----------
    ko = keepout("keepout antenna E73",
                 [(-0.2, ANT_Y), (BW + 0.2, ANT_Y), (BW + 0.2, BH + 0.2), (-0.2, BH + 0.2)],
                 ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"])
    # ---- ingombro cella: niente componenti sul retro sotto la cella -------
    ko += keepout("ingombro cella LiPo",
                  [(x1, y1), (x2, y1), (x2, y2), (x1, y2)], ["B.Cu"],
                  pads="allowed", footprints="not_allowed")

    # ---- piani: In1 massa (schermo sotto il modulo), In2 alimentazione ----
    board = [(0.6, 0.6), (BW - 0.6, 0.6), (BW - 0.6, BH - 0.6), (0.6, BH - 0.6)]
    zones = (plane("In1.Cu", code["GND"], "GND", board)
             + plane("In2.Cu", code["+3V0"], "+3V0", board))

    # ---- instradamento ----------------------------------------------------
    f_seg, b_seg, vias, aperte = router.route(tutti_pad, BW, BH, ANT_Y)
    tracks = "".join(
        seg(a, b, c, d, "F.Cu", code[n]) for a, b, c, d, n in f_seg)
    tracks += "".join(
        seg(a, b, c, d, "B.Cu", code[n]) for a, b, c, d, n in b_seg)
    tracks += "".join(via(x, y, code[n]) for x, y, n in vias)

    out = ('(kicad_pcb\n\t(version 20241229)\n\t(generator "contapassi/gen_pcb.py")\n'
           '\t(generator_version "9.0")\n'
           '\t(general\n\t\t(thickness 0.8)\n\t\t(legacy_teardrops no)\n\t)\n'
           '\t(paper "A4")\n' + LAYERS + SETUP + nets
           + "".join(body) + edge + ko + tracks + zones + ')\n')
    open(OUT, "w", encoding="utf-8").write(out)
    print("scritto %s" % OUT)
    print("scheda %.0f x %.0f mm, %d footprint, %d reti"
          % (BW, BH, len(body), len(names)))
    print("instradamento: %d via, %d tratti su B.Cu, %d moncherini su F.Cu"
          % (len(vias), len(b_seg), len(f_seg)))
    if aperte:
        print("NON INSTRADATE (%d):" % len(aperte))
        for n, a, b in aperte:
            print("   %-12s (%.1f,%.1f) -> (%.1f,%.1f)" % (n, a[0], a[1], b[0], b[1]))
    if mancanti:
        print("SENZA POSIZIONE: %s" % ", ".join(mancanti))


if __name__ == "__main__":
    main()
