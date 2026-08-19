#!/usr/bin/env python3
"""Genera la prima stesura dello schematico contapassi (KiCad 9).

Le connessioni sono espresse per NOME DI RETE: ogni pin collegato riceve uno
stub e un'etichetta. Uno schematico "a netlist", pensato per essere corretto e
verificabile con `kicad-cli sch erc`, non per essere bello. Dopo averlo
riordinato a mano in Eeschema NON rilanciare questo script: sovrascrive il file.

    python hardware/tools/gen_schematic.py
"""
import os
import re
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
KI = r"C:\Program Files\KiCad\9.0\share\kicad\symbols"
OUT = os.path.join(HW, "contapassi.kicad_sch")

LIBS = {
    "Device": os.path.join(KI, "Device.kicad_sym"),
    "Connector": os.path.join(KI, "Connector.kicad_sym"),
    "power": os.path.join(KI, "power.kicad_sym"),
    "contapassi": os.path.join(HW, "lib", "contapassi.kicad_sym"),
}

DQ = chr(34)


# ---------------------------------------------------------------- s-expression
def find_block(text, name):
    """Testo del blocco (symbol "name" ...), bilanciando le parentesi."""
    m = re.search(r"\(symbol\s+" + DQ + re.escape(name) + DQ, text)
    if not m:
        raise KeyError(name)
    i = m.start()
    depth = 0
    instr = False
    esc = False
    for j in range(i, len(text)):
        ch = text[j]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == DQ:
            instr = not instr
            continue
        if instr:
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    raise ValueError("blocco non bilanciato: " + name)


def tokenize(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c in "()":
            out.append(c)
            i += 1
        elif c.isspace():
            i += 1
        elif c == DQ:
            j = i + 1
            buf = []
            while s[j] != DQ or s[j - 1] == "\\":
                buf.append(s[j])
                j += 1
            out.append(DQ + "".join(buf))
            i = j + 1
        else:
            j = i
            while j < len(s) and not s[j].isspace() and s[j] not in "()":
                j += 1
            out.append(s[i:j])
            i = j
    return out


def parse(s):
    toks = tokenize(s)
    pos = [0]

    def rd():
        t = toks[pos[0]]
        pos[0] += 1
        if t == "(":
            lst = []
            while toks[pos[0]] != ")":
                lst.append(rd())
            pos[0] += 1
            return lst
        return t

    return rd()


def sym_pins(block):
    """{numero: (x, y, angolo)} nel sistema di riferimento del simbolo."""
    tree = parse(block)
    pins = {}

    def walk(node):
        if not isinstance(node, list):
            return
        if node and node[0] == "pin":
            at = num = None
            for it in node[1:]:
                if isinstance(it, list) and it[0] == "at":
                    ang = float(it[3]) if len(it) > 3 else 0.0
                    at = (float(it[1]), float(it[2]), ang)
                if isinstance(it, list) and it[0] == "number":
                    num = it[1].lstrip(DQ)
            if at and num is not None:
                pins[num] = at
        for it in node:
            walk(it)

    walk(tree)
    return pins


CACHE = {}


def get_symbol(lib_id):
    if lib_id in CACHE:
        return CACHE[lib_id]
    lib, name = lib_id.split(":", 1)
    text = open(LIBS[lib], encoding="utf-8").read()
    block = find_block(text, name)
    CACHE[lib_id] = (block, sym_pins(block))
    return CACHE[lib_id]


def uid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------- distinta base
FP_R = "Resistor_SMD:R_0402_1005Metric"
FP_C4 = "Capacitor_SMD:C_0402_1005Metric"
FP_C6 = "Capacitor_SMD:C_0603_1608Metric"
FP_C12 = "Capacitor_SMD:C_1206_3216Metric"

# ref, lib_id, valore, footprint, LCSC, (x, y), {pin: rete}
COMPONENTS = [
    # ---- modulo radio ----------------------------------------------------
    ("U1", "contapassi:E73-2G4M08S1C", "E73-2G4M08S1C",
     "contapassi:WIRELM-SMD_E73-2G4M08S1C", "C356849", (170, 150), {
         "5": "GND", "9": "LED_DRV", "10": "CHG_STAT", "11": "XL1",
         "12": "SPI_MISO", "13": "XL2", "14": "SPI_MOSI", "15": "IMU_INT1",
         "16": "SPI_SCK", "17": "IMU_INT2", "18": "SPARE", "19": "+3V0",
         "20": "CS_FLASH", "21": "GND", "22": "CS_IMU", "23": "VBAT",
         "24": "GND", "25": "DCH", "26": "RESET", "37": "SWDIO",
         "39": "SWCLK"}),
    # ---- IMU -------------------------------------------------------------
    ("U2", "contapassi:LSM6DSV16XTR", "LSM6DSV16XTR",
     "contapassi:LGA-14_L3.0-W2.5-P0.50-BR", "C5267406", (360, 90), {
         "1": "SPI_MISO", "2": "GND", "3": "GND", "4": "IMU_INT1",
         "5": "+3V0", "6": "GND", "7": "GND", "8": "+3V0", "9": "IMU_INT2",
         "10": "+3V0", "11": "+3V0", "12": "CS_IMU", "13": "SPI_SCK",
         "14": "SPI_MOSI"}),
    # ---- flash (solo v1) -------------------------------------------------
    ("U3", "contapassi:W25Q256JVEIQTR", "W25Q256JVEIQ",
     "contapassi:WSON-8_L8.0-W6.10-P1.27-BL-EP", "C97522", (360, 175), {
         "1": "CS_FLASH", "2": "SPI_MISO", "3": "FLASH_WP", "4": "GND",
         "5": "SPI_MOSI", "6": "SPI_SCK", "7": "FLASH_HOLD", "8": "+3V0",
         "9": "GND"}),
    # ---- carica ----------------------------------------------------------
    ("U4", "contapassi:MCP73831T-2ATI_OT", "MCP73831T-2ATI/OT",
     "contapassi:SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR", "C14879", (360, 250), {
         "1": "CHG_STAT", "2": "GND", "3": "VBAT", "4": "VIN_SW",
         "5": "IPROG"}),
    ("Q1", "contapassi:AO3401A", "AO3401A",
     "contapassi:SOT-23_L2.9-W1.3-P1.90-LS2.4-BR", "C15127", (170, 260), {
         "1": "VIN_GATE", "2": "VIN", "3": "VIN_SW"}),
    # ---- alimentazione ---------------------------------------------------
    ("L1", "Device:L", "10uH", "Inductor_SMD:L_0603_1608Metric", "C76798",
     (60, 205), {"1": "DCH", "2": "+3V0"}),
    ("Y1", "Device:Crystal", "32.768kHz",
     "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", "C32346", (60, 120),
     {"1": "XL1", "2": "XL2"}),
    ("C1", "Device:C", "18pF", FP_C4, "C1549", (30, 150),
     {"1": "XL1", "2": "GND"}),
    ("C2", "Device:C", "18pF", FP_C4, "C1549", (90, 150),
     {"1": "XL2", "2": "GND"}),
    ("C3", "Device:C", "47uF", FP_C12, "C96123", (270, 320),
     {"1": "VBAT", "2": "GND"}),
    ("C4", "Device:C", "4.7uF", FP_C6, "C19666", (300, 320),
     {"1": "VBAT", "2": "GND"}),
    ("C5", "Device:C", "4.7uF", FP_C6, "C19666", (60, 260),
     {"1": "+3V0", "2": "GND"}),
    ("C6", "Device:C", "100nF", FP_C4, "C1525", (90, 260),
     {"1": "+3V0", "2": "GND"}),
    ("C7", "Device:C", "100nF", FP_C4, "C1525", (450, 60),
     {"1": "+3V0", "2": "GND"}),
    ("C8", "Device:C", "100nF", FP_C4, "C1525", (480, 60),
     {"1": "+3V0", "2": "GND"}),
    ("C9", "Device:C", "100nF", FP_C4, "C1525", (450, 155),
     {"1": "+3V0", "2": "GND"}),
    ("C10", "Device:C", "4.7uF", FP_C6, "C19666", (270, 255),
     {"1": "VIN_SW", "2": "GND"}),
    # ---- resistenze ------------------------------------------------------
    ("R1", "Device:R", "10k", FP_R, "C25744", (450, 105),
     {"1": "+3V0", "2": "CS_IMU"}),
    ("R2", "Device:R", "10k", FP_R, "C25744", (480, 200),
     {"1": "+3V0", "2": "CS_FLASH"}),
    ("R3", "Device:R", "10k", FP_R, "C25744", (510, 200),
     {"1": "+3V0", "2": "FLASH_WP"}),
    ("R4", "Device:R", "10k", FP_R, "C25744", (540, 200),
     {"1": "+3V0", "2": "FLASH_HOLD"}),
    ("R5", "Device:R", "100k", FP_R, "C25741", (450, 255),
     {"1": "+3V0", "2": "CHG_STAT"}),
    ("R6", "Device:R", "20k", FP_R, "C25765", (420, 310),
     {"1": "IPROG", "2": "GND"}),
    ("R7", "Device:R", "1k", FP_R, "C11702", (500, 310),
     {"1": "LED_DRV", "2": "LED_A"}),
    ("R8", "Device:R", "100k", FP_R, "C25741", (140, 320),
     {"1": "VIN_GATE", "2": "GND"}),
    ("D1", "Device:D_TVS", "PESD5V0S1BA", "Diode_SMD:D_SOD-323", "C2827694",
     (110, 320), {"1": "VIN", "2": "GND"}),
    ("D2", "Device:LED", "rosso", "LED_SMD:LED_0603_1608Metric", "C2286",
     (540, 310), {"1": "LED_A", "2": "GND"}),
    # ---- connettori a filo (footprint da disegnare) ----------------------
    ("J1", "Connector:Conn_01x02_Pin", "piazzole pogo",
     "contapassi:PogoPads_2P_P5.0mm", "", (60, 320),
     {"1": "VIN", "2": "GND"}),
    ("J2", "Connector:Conn_01x02_Pin", "cella LiPo",
     "contapassi:CellPads_2P_P4.0mm", "", (210, 320),
     {"1": "VBAT", "2": "GND"}),
    # ---- pad di test (accessibili prima del potting) ---------------------
    ("TP1", "Connector:TestPoint", "SWDIO",
     "TestPoint:TestPoint_Pad_1.5x1.5mm", "", (590, 60), {"1": "SWDIO"}),
    ("TP2", "Connector:TestPoint", "SWCLK",
     "TestPoint:TestPoint_Pad_1.5x1.5mm", "", (590, 85), {"1": "SWCLK"}),
    ("TP3", "Connector:TestPoint", "GND",
     "TestPoint:TestPoint_Pad_1.5x1.5mm", "", (590, 110), {"1": "GND"}),
    ("TP4", "Connector:TestPoint", "+3V0",
     "TestPoint:TestPoint_Pad_1.5x1.5mm", "", (590, 135), {"1": "+3V0"}),
    ("TP5", "Connector:TestPoint", "RESET",
     "TestPoint:TestPoint_Pad_1.5x1.5mm", "", (590, 160), {"1": "RESET"}),
    ("TP6", "Connector:TestPoint", "P0.04",
     "TestPoint:TestPoint_Pad_1.5x1.5mm", "", (590, 185), {"1": "SPARE"}),
    # ---- bandierine di alimentazione (solo per l'ERC, non in distinta) ----
    ("#FLG01", "power:PWR_FLAG", "PWR_FLAG", "", "", (240, 330), {"1": "GND"}),
    ("#FLG02", "power:PWR_FLAG", "PWR_FLAG", "", "", (300, 260),
     {"1": "VIN_SW"}),
]

STUB = 5.08  # lunghezza stub, multiplo di 2.54


def pin_xy(inst_xy, p):
    """Punto di connessione del pin in coordinate schematico."""
    return (inst_xy[0] + p[0], inst_xy[1] - p[1])


def outward(angle):
    """Direzione uscente dal corpo, a partire dal punto di connessione."""
    a = int(angle) % 360
    return {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[a]


def main():
    root = uid()
    body = []
    libsyms = []
    seen = set()
    for ref, lib_id, val, fp, lcsc, at, nets in COMPONENTS:
        at = (round(at[0] / 2.54) * 2.54, round(at[1] / 2.54) * 2.54)
        in_bom = "no" if ref.startswith("#") else "yes"
        block, pins = get_symbol(lib_id)
        if lib_id not in seen:
            seen.add(lib_id)
            libname = lib_id.split(":", 1)[1]
            libsyms.append(block.replace(DQ + libname + DQ, DQ + lib_id + DQ, 1))

        props = [("Reference", ref, False), ("Value", val, False),
                 ("Footprint", fp, True), ("Datasheet", "", True),
                 ("Description", "", True)]
        if lcsc:
            props.append(("LCSC", lcsc, True))
        ptxt = ""
        for i, (k, v, hide) in enumerate(props):
            ptxt += ('\t\t(property "%s" "%s" (at %.2f %.2f 0)'
                     ' (effects (font (size 1.27 1.27)) (justify left)%s))\n'
                     % (k, v, at[0] + 2.54, at[1] - 14 - i * 2.54,
                        " (hide yes)" if hide else ""))
        body.append(
            '\t(symbol (lib_id "%s") (at %.2f %.2f 0) (unit 1)\n'
            '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n'
            '\t\t(uuid "%s")\n%s'
            '\t\t(instances (project "contapassi"'
            ' (path "/%s" (reference "%s") (unit 1))))\n'
            '\t)\n' % (lib_id, at[0], at[1], uid(), ptxt, root, ref))

        for num, p in sorted(pins.items(),
                             key=lambda kv: int(re.sub(r"\D", "", kv[0]) or 0)):
            x, y = pin_xy(at, p)
            net = nets.get(num)
            if net is None:  # pin non usato -> no-connect esplicito
                body.append('\t(no_connect (at %.2f %.2f) (uuid "%s"))\n'
                            % (x, y, uid()))
                continue
            dx, dy = outward(p[2])
            ex, ey = x + dx * STUB, y + dy * STUB
            body.append('\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f))'
                        ' (stroke (width 0) (type default)) (uuid "%s"))\n'
                        % (x, y, ex, ey, uid()))
            if dx:
                rot = 0 if dx > 0 else 180
            else:
                rot = 90 if dy < 0 else 270
            body.append('\t(label "%s" (at %.2f %.2f %d)'
                        ' (effects (font (size 1.27 1.27)) (justify left bottom))'
                        ' (uuid "%s"))\n' % (net, ex, ey, rot, uid()))

    out = ('(kicad_sch\n\t(version 20250114)\n\t(generator "eeschema")\n'
           '\t(generator_version "9.0")\n\t(uuid "%s")\n\t(paper "A2")\n'
           '\t(lib_symbols\n%s\n\t)\n%s'
           '\t(sheet_instances (path "/" (page "1")))\n\t(embedded_fonts no)\n)\n'
           % (root, "\n".join(libsyms), "".join(body)))
    open(OUT, "w", encoding="utf-8").write(out)
    nets = sorted({n for comp in COMPONENTS for n in comp[6].values()})
    print("scritto %s" % OUT)
    print("%d componenti, %d reti" % (len(COMPONENTS), len(nets)))
    print("reti: %s" % ", ".join(nets))


if __name__ == "__main__":
    main()
