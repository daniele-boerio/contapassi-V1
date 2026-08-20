#!/usr/bin/env python3
"""Instradatore minimo per il contapassi. Usato da gen_pcb.py.

Non e' un autorouter serio: e' un Lee (ricerca in ampiezza su griglia) su un
solo strato, con i piani a fare il lavoro pesante.

Impilaggio deciso qui:

    F.Cu    componenti + moncherini pad->via
    In1.Cu  MASSA piena  <- e' lo schermo sotto il modulo, quello che conta
    In2.Cu  +3V0 pieno
    B.Cu    segnali (la faccia posteriore non ha componenti: e' tutta libera)

Massa e alimentazione non si instradano: ogni pad prende una via al suo fianco
e il piano fa il resto. E' anche il modo giusto di collegare i condensatori di
disaccoppiamento, non una scorciatoia.
"""
import heapq

GRID = 0.2          # passo griglia [mm]; l'isolamento lo garantisce free()
TRACK_W = 0.2       # larghezza pista [mm]
VIA_DIA = 0.6       # diametro via [mm]
VIA_DRILL = 0.3     # foro via [mm]
EDGE = 0.7          # margine dal bordo scheda [mm]
PAD_CLR = 0.10      # isolamento attorno ai pad [mm]

PLANE_NETS = ("GND", "+3V0")

# 🔴 Questo generatore NON instrada. Ci ho provato e va tolto dalle mani:
# il fan-out dei componenti a passo 0,5 mm chiede una precisione sotto il passo
# di griglia, e i moncherini di uscita finivano sopra i pad vicini — il DRC
# tirava fuori cortocircuiti veri. Le piste si tirano in pcbnew, con
# l'instradatore interattivo, che quel lavoro lo fa bene.
#
# Quello che resta qui e' la geometria: contorno, piazzamento, keepout e i due
# piani. Mettere a `True` serve solo a rivedere il tentativo.
SEGNALI = False
VIE = False


class Grid:
    """Griglia che ricorda DI CHI e' ogni cella.

    Serve perche' una pista puo' passare accanto a una via della propria rete
    ma non accanto a quella di un'altra: con un semplice "occupato/libero" la
    partenza sarebbe murata dalla via stessa.
    """

    def __init__(self, w, h):
        self.nx = int(w / GRID) + 1
        self.ny = int(h / GRID) + 1
        self.owner = [[None] * self.ny for _ in range(self.nx)]

    def cell(self, x, y):
        return int(round(x / GRID)), int(round(y / GRID))

    def pos(self, i, j):
        return i * GRID, j * GRID

    def inside(self, i, j):
        return 0 <= i < self.nx and 0 <= j < self.ny

    def take_rect(self, x1, y1, x2, y2, who, hard=True):
        """`hard=True` -> nessuno puo' passare nemmeno accanto (piste, via,
        bordo scheda). `hard=False` -> i pad: una pista puo' passargli a
        fianco, perche' fra due pad di un chip fine c'e' spazio per una pista
        anche se non per una pista con la sua fascia di rispetto."""
        i1, j1 = self.cell(x1, y1)
        i2, j2 = self.cell(x2, y2)
        for i in range(min(i1, i2), max(i1, i2) + 1):
            for j in range(min(j1, j2), max(j1, j2) + 1):
                if self.inside(i, j) and self.owner[i][j] is None:
                    self.owner[i][j] = (who, hard)

    def free(self, i, j, net):
        if not self.inside(i, j):
            return False
        o = self.owner[i][j]
        if o is not None and o[0] != net:
            return False
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                ii, jj = i + a, j + b
                if not self.inside(ii, jj):
                    continue
                o = self.owner[ii][jj]
                if o is not None and o[0] != net and o[1]:
                    return False
        return True

    def owned_by(self, i, j, net):
        o = self.owner[i][j] if self.inside(i, j) else ("#", True)
        return o is None or o[0] == net


def pad_box(p, margin=0.0):
    return (p["x"] - p["w"] / 2 - margin, p["y"] - p["h"] / 2 - margin,
            p["x"] + p["w"] / 2 + margin, p["y"] + p["h"] / 2 + margin)


def overlaps(box, boxes):
    x1, y1, x2, y2 = box
    for bx1, by1, bx2, by2 in boxes:
        if x1 < bx2 and bx1 < x2 and y1 < by2 and by1 < y2:
            return True
    return False


def place_vias(pads, bw, bh, ant_y):
    """Una via al fianco di ogni pad che serve. Prova quattro direzioni."""
    fixed = [pad_box(p, PAD_CLR) for p in pads]
    vias = []
    taken = []
    for p in pads:
        if p["th"]:                      # foro passante: gia' su tutti gli strati
            p["via"] = (p["x"], p["y"])
            continue
        best = None
        for d in (0.55, 0.75, 0.95, 1.15):
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                off = max(p["w"], p["h"]) / 2 + d
                vx = p["x"] + dx * off
                vy = p["y"] + dy * off
                if not (EDGE < vx < bw - EDGE and EDGE < vy < bh - EDGE):
                    continue
                if vy > ant_y - 0.3:      # zona antenna: niente via
                    continue
                box = (vx - VIA_DIA / 2 - 0.2, vy - VIA_DIA / 2 - 0.2,
                       vx + VIA_DIA / 2 + 0.2, vy + VIA_DIA / 2 + 0.2)
                # non deve toccare pad altrui ne' altre via
                others = [b for q, b in zip(pads, fixed) if q is not p]
                if overlaps(box, others) or overlaps(box, taken):
                    continue
                best = (vx, vy)
                break
            if best:
                break
        p["via"] = best
        if best:
            taken.append((best[0] - VIA_DIA / 2 - 0.2, best[1] - VIA_DIA / 2 - 0.2,
                          best[0] + VIA_DIA / 2 + 0.2, best[1] + VIA_DIA / 2 + 0.2))
            vias.append((best[0], best[1], p["net"]))
    return vias


def lee(grid, start, goal, net):
    """Percorso a costo minimo per la rete `net`, con penalita' sulle curve."""
    si, sj = start
    gi, gj = goal
    if not grid.inside(si, sj) or not grid.inside(gi, gj):
        return None
    dist = {}
    pq = [(0, si, sj, 0, 0)]
    prev = {}
    while pq:
        c, i, j, di, dj = heapq.heappop(pq)
        if (i, j, di, dj) in dist:
            continue
        dist[(i, j, di, dj)] = c
        if (i, j) == (gi, gj):
            path = [(i, j)]
            k = (i, j, di, dj)
            while k in prev:
                k = prev[k]
                if (k[0], k[1]) != path[-1]:
                    path.append((k[0], k[1]))
            return list(reversed(path))
        for ndi, ndj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ni, nj = i + ndi, j + ndj
            if not grid.free(ni, nj, net):
                continue
            turn = 3 if (di, dj) != (0, 0) and (ndi, ndj) != (di, dj) else 0
            nc = c + 1 + turn
            key = (ni, nj, ndi, ndj)
            if key not in dist:
                prev[key] = (i, j, di, dj)
                heapq.heappush(pq, (nc, ni, nj, ndi, ndj))
    return None


def mst_edges(points):
    """Albero di copertura minimo: l'ordine in cui collegare i pad di una rete."""
    if len(points) < 2:
        return []
    inside = {0}
    edges = []
    while len(inside) < len(points):
        best = None
        for a in inside:
            for b in range(len(points)):
                if b in inside:
                    continue
                d = abs(points[a][0] - points[b][0]) + abs(points[a][1] - points[b][1])
                if best is None or d < best[0]:
                    best = (d, a, b)
        edges.append((best[1], best[2]))
        inside.add(best[2])
    return edges


def compact(pts_mm):
    """Toglie i punti allineati: tre punti in fila diventano un segmento solo."""
    comp = [pts_mm[0]]
    for k in range(1, len(pts_mm) - 1):
        x0, y0 = comp[-1]
        x1, y1 = pts_mm[k]
        x2, y2 = pts_mm[k + 1]
        if (x1 - x0) * (y2 - y1) != (x2 - x1) * (y1 - y0):
            comp.append((x1, y1))
    comp.append(pts_mm[-1])
    return comp


def route(pads, bw, bh, ant_y):
    """Instrada. Prima prova sul rame davanti, che non costa via; se non passa
    scende sul retro, che e' vuoto.

    Ritorna (segmenti F.Cu, segmenti B.Cu, via, collegamenti rimasti aperti).
    """
    f_seg = []
    b_seg = []
    vias = []

    # ---- griglia del lato componenti: i pad sono ostacoli, ma ognuno e'
    # attraversabile dalla propria rete
    gf = Grid(bw, bh)
    gf.take_rect(0, 0, bw, EDGE, "#")
    gf.take_rect(0, bh - EDGE, bw, bh, "#")
    gf.take_rect(0, 0, EDGE, bh, "#")
    gf.take_rect(bw - EDGE, 0, bw, bh, "#")
    gf.take_rect(0, ant_y, bw, bh, "#")
    for p in pads:
        gf.take_rect(*pad_box(p, PAD_CLR), who=p["net"], hard=False)

    # ---- griglia del retro: libera, non ci sono componenti
    gb = Grid(bw, bh)
    gb.take_rect(0, 0, bw, EDGE, "#")
    gb.take_rect(0, bh - EDGE, bw, bh, "#")
    gb.take_rect(0, 0, EDGE, bh, "#")
    gb.take_rect(bw - EDGE, 0, bw, bh, "#")
    gb.take_rect(0, ant_y, bw, bh, "#")
    for p in pads:
        if p["th"]:
            gb.take_rect(*pad_box(p, 0.3), who=p["net"], hard=False)

    def breakout(p):
        """Tira il pad fuori dal chip in linea retta, come si fa a mano.

        Senza questo passo i chip a passo fine sono inattaccabili: la griglia
        vede solo i pad vicini e blocca ogni uscita. Il moncherino invece
        corre parallelo a quelli dei pad accanto, alla loro stessa distanza.
        """
        if "bo" in p:
            return p["bo"]
        for d in (0.45, 0.7, 0.95, 1.25, 1.6):
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                off = (p["h"] if dy else p["w"]) / 2 + d
                bx, by = p["x"] + dx * off, p["y"] + dy * off
                if not (EDGE < bx < bw - EDGE and EDGE < by < bh - EDGE):
                    continue
                if by > ant_y - 0.3:
                    continue
                i, j = gf.cell(bx, by)
                if not gf.free(i, j, p["net"]):
                    continue
                bx, by = gf.pos(i, j)
                p["bo"] = (bx, by)
                f_seg.append((p["x"], p["y"], bx, by, p["net"]))
                # il moncherino occupa la griglia: da qui in poi e' un ostacolo
                x1, x2 = sorted((p["x"], bx))
                y1, y2 = sorted((p["y"], by))
                gf.take_rect(x1, y1, x2, y2, p["net"], hard=True)
                return p["bo"]
        p["bo"] = (p["x"], p["y"])
        return p["bo"]

    def via_ok(i, j, net):
        """Serve un quadrato di 5 celle (+-0,4 mm) libero su tutti e due i
        rami di rame: la via e' larga 0,6 mm e vuole 0,2 di rispetto."""
        for a in range(-2, 3):
            for c in range(-2, 3):
                if not gb.inside(i + a, j + c):
                    return False
                if not gb.owned_by(i + a, j + c, net) or not gf.owned_by(i + a, j + c, net):
                    return False
        return True

    def add_via(p):
        """Via all'estremita' del moncherino di uscita; se li' non ci sta, il
        moncherino si allunga finche' non trova posto."""
        if p.get("via"):
            return p["via"]
        if p["th"]:
            p["via"] = (p["x"], p["y"])
            return p["via"]
        bx, by = breakout(p)
        dx = 0 if abs(bx - p["x"]) < 1e-6 else (1 if bx > p["x"] else -1)
        dy = 0 if abs(by - p["y"]) < 1e-6 else (1 if by > p["y"] else -1)
        if dx == 0 and dy == 0:
            dy = -1
        for k in range(0, 12):
            vx, vy = bx + dx * k * GRID, by + dy * k * GRID
            if not (EDGE < vx < bw - EDGE and EDGE < vy < bh - EDGE):
                break
            if vy > ant_y - 0.5:
                break
            i, j = gb.cell(vx, vy)
            if not via_ok(i, j, p["net"]):
                continue
            vx, vy = gb.pos(i, j)
            p["via"] = (vx, vy)
            vias.append((vx, vy, p["net"]))
            gb.take_rect(vx - 0.4, vy - 0.4, vx + 0.4, vy + 0.4, p["net"])
            gf.take_rect(vx - 0.4, vy - 0.4, vx + 0.4, vy + 0.4, p["net"])
            if k:
                f_seg.append((bx, by, vx, vy, p["net"]))
                x1, x2 = sorted((bx, vx))
                y1, y2 = sorted((by, vy))
                gf.take_rect(x1, y1, x2, y2, p["net"])
            return p["via"]
        p["via"] = None
        return None

    # ---- segnali: prima le reti lunghe, che sono quelle che si incastrano.
    # I piani vengono dopo: se prendessero posto per primi murerebbero i chip
    # piccoli, che hanno meta' dei pad su massa e alimentazione
    per_net = {}
    for p in pads:
        if p["net"] not in PLANE_NETS:
            per_net.setdefault(p["net"], []).append(p)

    def lunghezza(ps):
        pts = [(q["x"], q["y"]) for q in ps]
        return sum(abs(pts[a][0] - pts[b][0]) + abs(pts[a][1] - pts[b][1])
                   for a, b in mst_edges(pts))

    aperte = []
    for net in (sorted(per_net, key=lambda n: -lunghezza(per_net[n]))
               if SEGNALI else []):
        ps = per_net[net]
        pts = [(q["x"], q["y"]) for q in ps]
        for q in ps:
            breakout(q)
        for a, b in mst_edges(pts):
            pa, pb = ps[a], ps[b]
            oa, ob = pa["bo"], pb["bo"]
            # 1) tentativo sul rame davanti, senza via
            path = lee(gf, gf.cell(*oa), gf.cell(*ob), net)
            if path:
                mm = [gf.pos(i, j) for i, j in path]
                mm[0], mm[-1] = oa, ob
                for i, j in path:
                    if gf.inside(i, j) and gf.owner[i][j] is None:
                        gf.owner[i][j] = (net, True)
                c = compact(mm)
                for k in range(len(c) - 1):
                    f_seg.append((c[k][0], c[k][1], c[k + 1][0], c[k + 1][1], net))
                continue
            # 2) altrimenti si scende sul retro
            va, vb = add_via(pa), add_via(pb)
            if not va or not vb:
                aperte.append((net, (pa["x"], pa["y"]), (pb["x"], pb["y"])))
                continue
            path = lee(gb, gb.cell(*va), gb.cell(*vb), net)
            if not path:
                aperte.append((net, va, vb))
                continue
            mm = [gb.pos(i, j) for i, j in path]
            mm[0], mm[-1] = va, vb
            for i, j in path:
                if gb.inside(i, j) and gb.owner[i][j] is None:
                    gb.owner[i][j] = (net, True)
            c = compact(mm)
            for k in range(len(c) - 1):
                b_seg.append((c[k][0], c[k][1], c[k + 1][0], c[k + 1][1], net))

    # ---- massa e alimentazione: una via al fianco di ogni pad, il piano fa
    # il resto. E' anche il modo giusto di collegare i disaccoppiamenti
    if VIE:
        senza_via = []
        for p in pads:
            if p["net"] in PLANE_NETS:
                breakout(p)
                if not add_via(p):
                    senza_via.append((p["net"], (p["x"], p["y"]), (p["x"], p["y"])))
        aperte.extend(senza_via)
    return f_seg, b_seg, vias, aperte


def _vecchio_route(pads, bw, bh, ant_y):
    """Ritorna (segmenti F.Cu, segmenti B.Cu, via, reti non instradate)."""
    vias = place_vias(pads, bw, bh, ant_y)
    f_seg = []
    b_seg = []

    # moncherino pad -> via, su F.Cu
    for p in pads:
        if p["th"] or not p["via"]:
            continue
        f_seg.append((p["x"], p["y"], p["via"][0], p["via"][1], p["net"]))

    # griglia del lato B: parte libera, si riempie man mano
    g = Grid(bw, bh)
    g.take_rect(0, 0, bw, EDGE, "#")
    g.take_rect(0, bh - EDGE, bw, bh, "#")
    g.take_rect(0, 0, EDGE, bh, "#")
    g.take_rect(bw - EDGE, 0, bw, bh, "#")
    g.take_rect(0, ant_y, bw, bh, "#")
    for p in pads:
        if p["th"]:
            g.take_rect(*pad_box(p, 0.3), who=p["net"])

    # ogni via si prende il proprio quadrato: le piste altrui devono girarci
    # attorno, la propria ci passa
    for vx, vy, vnet in vias:
        g.take_rect(vx - 0.45, vy - 0.45, vx + 0.45, vy + 0.45, vnet)

    per_net = {}
    for p in pads:
        if p["net"] in PLANE_NETS or not p["via"]:
            continue
        per_net.setdefault(p["net"], []).append(p["via"])

    non_instradate = []
    for net, pts in sorted(per_net.items()):
        for a, b in mst_edges(pts):
            start = g.cell(*pts[a])
            goal = g.cell(*pts[b])
            path = lee(g, start, goal, net)
            if not path:
                non_instradate.append((net, pts[a], pts[b]))
                continue
            # compatta i tratti dritti e occupa la griglia
            pts_mm = [g.pos(i, j) for i, j in path]
            pts_mm[0] = pts[a]
            pts_mm[-1] = pts[b]
            for i, j in path:
                if g.inside(i, j) and g.owner[i][j] is None:
                    g.owner[i][j] = net
            comp = [pts_mm[0]]
            for k in range(1, len(pts_mm) - 1):
                x0, y0 = comp[-1]
                x1, y1 = pts_mm[k]
                x2, y2 = pts_mm[k + 1]
                if (x1 - x0) * (y2 - y1) != (x2 - x1) * (y1 - y0):
                    comp.append((x1, y1))
            comp.append(pts_mm[-1])
            for k in range(len(comp) - 1):
                b_seg.append((comp[k][0], comp[k][1],
                              comp[k + 1][0], comp[k + 1][1], net))
    return f_seg, b_seg, vias, non_instradate
