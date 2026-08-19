# Setup Claude Code — contapassi

## Dove mettere i file

Nella radice del repo del progetto:

```
contapassi-v1/
├── .claude/
│   ├── CLAUDE.md                       ← contesto sempre caricato
│   └── skills/
│       ├── kicad-jlcpcb/SKILL.md
│       ├── nrf52840-firmware/SKILL.md
│       └── analisi-andatura/SKILL.md
├── docs/
│   ├── 01-design.md
│   ├── 02-bom-jlcpcb.md
│   └── 03-firmware-taratura.md
├── lib/          ← simboli e footprint custom KiCad
├── hardware/     ← progetto KiCad
├── firmware/
└── analysis/     ← notebook Python
```

I tre documenti di design vanno in `docs/`: le skill e il CLAUDE.md li
referenziano con quei percorsi.

## CLAUDE.md vs skill — la differenza

**CLAUDE.md** viene caricato in ogni conversazione. Contiene solo ciò che serve
sempre: cos'è il progetto, le decisioni congelate, i vincoli non negoziabili.
Tenerlo corto è importante — occupa contesto a ogni messaggio.

**Le skill** si caricano solo quando servono, in base alla loro `description`.
Contengono il dettaglio operativo di un dominio specifico. Le tre qui sono
disgiunte: hardware/produzione, firmware, analisi dati.

## Le tre skill

| Skill | Si attiva su |
|---|---|
| `kicad-jlcpcb` | KiCad, schematico, PCB, footprint, BOM, CPL, componenti, ordini |
| `nrf52840-firmware` | Codice firmware, driver, BLE, interrupt, consumo, bring-up |
| `analisi-andatura` | Python, notebook, ZUPT, stance detection, taratura, validazione |

## Verifica che funzionino

In Claude Code, `/skills` elenca le skill disponibili. Se una non compare,
controlla che il frontmatter YAML sia valido e che `name` coincida con il nome
della cartella.

Per testare il triggering, prova richieste generiche e osserva se la skill si
attiva:

- "aggiungi un condensatore di bypass all'IMU" → `kicad-jlcpcb`
- "perché il consumo in idle è più alto del previsto?" → `nrf52840-firmware`
- "il conteggio passi sbaglia sulle camminate lente" → `analisi-andatura`

Se una skill non si attiva quando dovrebbe, il problema è quasi sempre nella
`description`: aggiungi i termini che l'utente userebbe realmente. Le descrizioni
sono volutamente "spinte" (elencano molti sinonimi e casi generici) proprio
perché la tendenza tipica è di non attivarle abbastanza.

## Manutenzione

Le skill contengono numeri che possono cambiare — budget energetico, quote,
codici LCSC. Quando un documento in `docs/` cambia, **controlla se la skill
corrispondente ripete quel numero**. Meglio ancora: dove possibile la skill
rimanda al documento invece di duplicare il valore.

I punti attualmente duplicati e da tenere allineati:

- budget ~161 µA e autonomia ~10 giorni (CLAUDE.md, firmware)
- quote PCB ~32 × 18 mm (kicad-jlcpcb)
- codice LCSC del modulo `C356849` (CLAUDE.md, kicad-jlcpcb)
- configurazione IMU ±16 g / 416 Hz (firmware, analisi)
