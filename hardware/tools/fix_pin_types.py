#!/usr/bin/env python3
"""Assegna il tipo elettrico ai pin dei simboli generati da easyeda2kicad.

easyeda2kicad marca tutti i pin come `unspecified`: con quello l'ERC non
distingue un'alimentazione da un ingresso e segnala decine di falsi positivi
"Unspecified e Unspecified sono connessi". Qui i tipi vengono messi a mano
seguendo i datasheet.

Idempotente: si puo' rilanciare, e va rilanciato dopo ogni easyeda2kicad che
rigeneri uno di questi simboli.

    python hardware/tools/fix_pin_types.py
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib", "contapassi.kicad_sym")

# Tipo per numero di pin. "*" = valore predefinito per i pin non elencati.
TYPES = {
    "E73-2G4M08S1C": {
        "*": "bidirectional",   # GPIO
        "5": "power_in", "21": "power_in", "24": "power_in",   # GND
        "19": "power_out",      # VDD = uscita di REG0, alimenta la scheda
        "23": "power_in",       # VDDH = cella
        "25": "passive",        # DCCH -> L1
        "11": "passive", "13": "passive",                      # XL1 / XL2
        "26": "input",          # RESET
        "27": "passive",        # VBUS non usato
        "29": "passive", "31": "passive",                      # USB D- / D+
    },
    "LSM6DSV16XTR": {
        "*": "passive",
        "5": "power_in", "8": "power_in",                      # Vdd_IO / Vdd
        "6": "power_in", "7": "power_in",                      # GND
        "1": "tri_state",       # SDO: tre stati, condiviso con la flash
        "4": "output", "9": "output",                          # INT1 / INT2
        "12": "input", "13": "input", "14": "input",           # CS / SPC / SDI
    },
    "W25Q256JVEIQTR": {
        "*": "input",
        "8": "power_in", "4": "power_in",                      # VCC / GND
        "9": "passive",         # exposed pad
        "2": "tri_state",       # DO: tre stati, condiviso con l'IMU
    },
    "MCP73831T-2ATI_OT": {
        "*": "passive",
        "4": "power_in", "2": "power_in",                      # VDD / VSS
        "3": "power_out",       # VBAT: pilota la rete della cella
        "1": "open_collector",  # STAT
    },
    "AO3401A": {"*": "passive"},
}

VALID = ("input output bidirectional tri_state passive free unspecified "
         "power_in power_out open_collector open_emitter no_connect").split()


def symbol_span(text, name):
    """(inizio, fine) del blocco (symbol "name" ...) bilanciando le parentesi."""
    m = re.search(r'\(symbol\s+"%s"' % re.escape(name), text)
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
        if ch == '"':
            instr = not instr
            continue
        if instr:
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i, j + 1
    raise ValueError(name)


PIN_RE = re.compile(
    r'\(pin\s+(' + "|".join(VALID) + r')\s+(\w+)'          # tipo, forma
    r'([\s\S]*?\(number\s+"([^"]+)")',                     # fino al numero
)


def main():
    text = open(LIB, encoding="utf-8").read()
    total = 0
    for name, table in TYPES.items():
        try:
            a, b = symbol_span(text, name)
        except KeyError:
            print("  simbolo assente, saltato: %s" % name)
            continue
        block = text[a:b]
        count = [0]

        def repl(m):
            _tipo, forma, rest, num = m.groups()
            nuovo = table.get(num, table["*"])
            count[0] += 1
            return "(pin %s %s%s" % (nuovo, forma, rest)

        block = PIN_RE.sub(repl, block)
        text = text[:a] + block + text[b:]
        total += count[0]
        print("  %-20s %d pin" % (name, count[0]))
    open(LIB, "w", encoding="utf-8").write(text)
    print("aggiornati %d pin in %s" % (total, LIB))


if __name__ == "__main__":
    main()
