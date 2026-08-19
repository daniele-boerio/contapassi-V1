# Setup Claude Code — contapassi

## Struttura del repo

```
contapassi/
├── .claude/
│   ├── CLAUDE.md                       ← contesto sempre caricato
│   └── skills/
│       ├── kicad-jlcpcb/SKILL.md
│       ├── nrf52840-firmware/SKILL.md
│       └── analisi-andatura/SKILL.md
├── .gitignore
├── README.md
│
├── docs/
│   ├── 01-design.md
│   ├── 02-bom-jlcpcb.md
│   ├── 03-firmware-taratura.md
│   └── datasheet/              ← E73, LSM6DSV16X, MCP73831, cella
│
├── hardware/
│   ├── contapassi.kicad_pro
│   ├── contapassi.kicad_sch
│   ├── contapassi.kicad_pcb
│   ├── lib/
│   │   ├── contapassi.kicad_sym
│   │   ├── contapassi.pretty/  ← footprint
│   │   └── 3dmodels/
│   └── production/
│       └── 2026-XX-XX-v1/      ← gerber + BOM + CPL di ogni ordine
│
├── firmware/
│   ├── CMakeLists.txt
│   ├── prj.conf
│   ├── boards/                 ← definizione board custom
│   └── src/
│
├── analysis/
│   ├── notebooks/
│   ├── src/                    ← parser, ZUPT, metriche
│   └── data/
│       ├── raw/                ← dump binari (NON versionati)
│       └── ground-truth.csv    ← versionato, è prezioso
│
└── ios/
```

### Le scelte che contano

**`lib/` va dentro `hardware/`.** KiCad risolve le librerie di progetto con
`${KIPRJMOD}`, che punta alla cartella del `.kicad_pro`. Fuori da lì i percorsi
si rompono appena sposti il progetto.

**Un solo repo, non tre.** Hardware, firmware e analisi cambiano insieme: se
sposti un pin nello schematico devi toccare anche il firmware. Con repo separati
quella correlazione si perde, e il CLAUDE.md andrebbe duplicato.

**`hardware/production/` con una cartella datata per ordine.** I file di
produzione sono generati, ma sono l'unica traccia di _cosa hai effettivamente
ordinato_. Quando la scheda arriva e qualcosa non torna, vuoi guardare i file
spediti — non rigenerarli da un progetto nel frattempo modificato.

**`firmware/boards/` non è opzionale.** L'nRF Connect SDK ha bisogno di una
definizione di board per il PCB custom: è lì che si dichiara quali pin sono SPI,
dove stanno gli interrupt e la configurazione del quarzo. È la traduzione in
codice della mappatura pin del doc 01.

**`analysis/data/raw/` fuori da git** — sono ~27 MB al giorno di dump, il repo
diventerebbe ingestibile in una settimana. Tienili in una cartella sincronizzata
o su un disco esterno.

**`ground-truth.csv` invece va versionato.** È piccolo e irripetibile: sono le
camminate fatte contando i passi a mano. Se lo perdi, rifai tutta la raccolta.

### .gitignore minimo

```gitignore
# KiCad
*-backups/
*.kicad_prl
*.bak
fp-info-cache
~*.*

# Firmware
build/

# Analisi
analysis/data/raw/
__pycache__/
.ipynb_checkpoints/
```

`.kicad_prl` è escluso ma `.kicad_pro` no: il primo contiene preferenze locali di
visualizzazione, il secondo le impostazioni di progetto da condividere.

## CLAUDE.md vs skill — la differenza

**CLAUDE.md** viene caricato in ogni conversazione. Contiene solo ciò che serve
sempre: cos'è il progetto, le decisioni congelate, i vincoli non negoziabili.
Tenerlo corto è importante — occupa contesto a ogni messaggio.

**Le skill** si caricano solo quando servono, in base alla loro `description`.
Contengono il dettaglio operativo di un dominio specifico. Le tre qui sono
disgiunte: hardware/produzione, firmware, analisi dati.

## Le tre skill

| Skill               | Si attiva su                                                    |
| ------------------- | --------------------------------------------------------------- |
| `kicad-jlcpcb`      | KiCad, schematico, PCB, footprint, BOM, CPL, componenti, ordini |
| `nrf52840-firmware` | Codice firmware, driver, BLE, interrupt, consumo, bring-up      |
| `analisi-andatura`  | Python, notebook, ZUPT, stance detection, taratura, validazione |

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
- quote PCB ~48 × 17 mm (kicad-jlcpcb)
- codice LCSC del modulo `C356849` (CLAUDE.md, kicad-jlcpcb)
- configurazione IMU ±16 g / 416 Hz (firmware, analisi)
