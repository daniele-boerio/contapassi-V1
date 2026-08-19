# Contapassi ad alta precisione — Documento di design

**Versione doc:** 1.1
**Stato:** requisiti congelati, **mappatura pin verificata (§5)**, schematico da disegnare
**Target produzione:** KiCad 9.0 → JLCPCB (PCB + PCBA)

---

## 1. Obiettivo

Dispositivo indossabile da caviglia per misurare con precisione:

- **conteggio passi** (24/7)
- **distanza percorsa** (errore target < 1%)
- **parametri di andatura**: cadenza, tempo di appoggio/volo, variabilità del passo

Sincronizzazione con iPhone via BLE, scrittura su HealthKit.
Autonomia target: **1 settimana** (progettato per ~10 giorni reali).
**Indossabile in continuo**, doccia e piscina incluse — mai da togliere.

### Non obiettivi (esplicitamente esclusi)

- Asimmetria destra/sinistra → richiede due unità sincronizzate
- Cinematica del tronco (tilt/obliquità/rotazione pelvica) → richiede posizione lombare
- Classificazione posturale (seduto/in piedi/sdraiato) → impossibile da caviglia
- Display, GPS, cardiofrequenzimetro

---

## 2. Decisione di posizionamento

**Scelta: caviglia**, sopra il malleolo.

| Criterio | Caviglia | Lombare (L3-L5) |
|---|---|---|
| Conteggio passi | ✅ superiore (cammino lento/strascicato) | buono |
| Distanza | ✅ **< 1% via ZUPT**, senza calibrazione | 2-4% via modello, calibrazione personale |
| Eventi temporali (heel strike, toe off) | ✅ precisi al ms | indiretti |
| Cinematica tronco | ❌ | ✅ |
| Asimmetria dx/sx con 1 device | ❌ | ✅ |
| Postura | ❌ | ✅ |
| Qualità RF | ❌ 10 cm da terra, peggiore | ✅ |
| Vincolo ingombro | ✅ permissivo | 4-5 mm max (schienale sedia) |

**Motivazione:** priorità dichiarata = passi + distanza. Lo ZUPT è possibile solo
dove il segmento corporeo si ferma completamente a ogni passo, cioè al piede/caviglia.

---

## 3. Principio ZUPT (Zero Velocity Update)

L'integrazione dell'accelerazione per ottenere posizione accumula errore
quadraticamente: in ~10 s la stima è inutilizzabile.

A ogni passo però il piede resta **fermo a terra per ~0,3-0,5 s**. In quella
finestra la velocità reale è nota e vale zero. Quindi:

1. Rileva la fase di appoggio (stance detection)
2. Azzera velocità e correggi la deriva del giroscopio
3. Integra solo la fase di volo successiva
4. Ripeti

L'errore non si accumula mai oltre una singola falcata.
Analogia: NTP che risincronizza un clock che deriva.

**Conseguenza architetturale:** il giroscopio deve essere attivo durante *tutto*
il cammino, non a campione. Non è duty-ciclabile.

---

## 4. Architettura hardware

```
  pogo (+) ──▶ TVS + prot. inversione ──▶ MCP73831 ──▶ LiPo 301220 (80 mAh, con PCM)
                                              │              │
                                            /STAT            │
                                              │              ▼
                                         ┌────┴───────────  VDH  (VDDH)
                                         │  E73-2G4M08S1C
                                L1 ──── DCH   (nRF52840)
                             (~10 µH)     │                   │
                                  SWD ────┤              2.4 GHz ~~~
                                         │
                          Y1 ─── XL1/XL2 ─┤
                     (32,768 kHz + 2C)    │
                                         │
                        ┌─── SPI condiviso ───┐
                        │                     │
                 LSM6DSV16XTR            W25Q256JVEIQ
               (CS1 + INT1/INT2)           (CS2)
                                        [SOLO v1]
```

Dominio di tensione: **3,0 V** (REGOUT0 configurato via UICR — vedi doc 02 §3).

Topologia di alimentazione verificata sulla *circuit configuration no. 4* del
datasheet Nordic (VDDH + EXTSUPPLY + DCDCEN0 + DCDCEN1):

- LiPo → `VDH` (VDDH)
- **L1 = 10 µH** tra `DCH` (DCCH) e `VDD`: l'induttore sta sull'uscita di REG0,
  non sull'ingresso. Nordic specifica IDC ≥ 80 mA, ±10%, 0603
- `VDD` (pad 19) è **l'uscita di REG0 a 3,0 V** e alimenta IMU e flash.
  Richiede `EXTSUPPLY` abilitato nell'UICR (vedi doc 02 §3)

> ⚠️ **VEXDIF = 0,3 V.** REG0 non può regolare più vicino di 0,3 V al VDDH.
> Con REGOUT0 = 3,0 V il rail è garantito solo finché la cella sta **sopra
> 3,3 V**; sotto, VDD scende seguendo VDDH − 0,3 V. Vedi doc 02 §3.

### 4.1 Decisioni chiave e motivazioni

| # | Decisione | Motivo |
|---|---|---|
| 1 | **Pedometro in hardware nel sensore + FIFO** | MCU sveglio < 1% del tempo. È ciò che rende possibile una cella da poche decine di mAh. Event-driven, mai polling |
| 2 | **Modulo radio certificato, non chip nudo** | Antenna 2.4 GHz già progettata, adattata e certificata. Elimina una classe di problemi non diagnosticabili senza strumenti RF |
| 3 | **Batteria diretta su VDDH** | L'nRF52840 ha regolatore interno, accetta fino a 5,5 V. Elimina l'LDO esterno |
| 4 | **SPI condiviso, non QSPI dedicato** | Il collo di bottiglia del dump è il BLE (~150 kB/s), non la flash. Libera 4 pin, semplifica il layout, e la flash si rimuove pulitamente in v2 |
| 5 | **ZUPT sull'MCU, non su MLC del sensore** | Con budget da 1 settimana l'ottimizzazione non serve più. In C sull'MCU si debugga con un breakpoint, nella FSM del sensore no |
| 6 | **Niente fuel gauge dedicato** | ADC interno + partitore VDDHDIV5 già integrato. Sufficiente su 1 settimana |
| 7 | **v1 logger, v2 prodotto** | Algoritmo tarato sui propri dati, sviluppato offline in Python. Ciclo di iterazione in secondi anziché ore |
| 8 | **DFU over BLE dal giorno 1** | La capsula è annegata in resina: dopo il potting non esiste accesso via cavo |
| 9 | **Doppio tap come unico "pulsante"** | Rilevamento in hardware nell'IMU. Zero componenti, zero aperture, funziona attraverso la resina |
| 10 | **Capsula separata dal cinturino** | Il cinturino è la parte che si consuma e va iterata più volte. Non deve portarsi via l'elettronica |
| 11 | **Dominio a 3,0 V** (REGOUT0 via UICR) | Il default sarebbe 1,8 V. A 3,0 V restano compatibili flash standard, LED di qualsiasi colore e debugger a 3,3 V fissi. Il guadagno energetico a 1,8 V è marginale |
| 12 | **Induttore REG0 esterno (L1)** | Il modulo E73 espone `DCH` → non è integrato. Senza, REG0 resta in LDO e dissipa il 25% su tutto il consumo della scheda |
| 13 | **Quarzo 32,768 kHz esterno (Y1)** | Il modulo espone `XL1`/`XL2` → non è integrato. Senza, l'RC interno allarga le finestre RX BLE e consuma di più proprio dove ottimizziamo |

---

## 5. Mappatura pin — ricostruita sul pinout Ebyte

**Stato:** ✅ **verificata il 2026-08-19.** Fonti:

- *E73-2G4M08S1C User Manual* v1.9 (Ebyte, 2020-03-30), §3 "Size and pin definition"
  → copia locale in `docs/datasheet/`
- *nRF52840 Product Specification*, tabella pin aQFN73 e §56.4 "Circuit
  configuration no. 4" (VDDH + EXTSUPPLY + DCDCEN0 + DCDCEN1 — la nostra topologia)
- footprint generato con `easyeda2kicad --full --lcsc_id=C356849` (geometria dei pad)

### 5.1 Vincolo scoperto: pin "low frequency I/O only"

Nordic marca una parte dei GPIO come **"Standard drive, low frequency I/O only"**,
dove *low frequency* è definita come **segnale fino a 10 kHz**. Su questi pin non
si può appoggiare un bus SPI.

Tra i pad esposti dall'E73 appartengono a questa classe:

`P0.02` `P0.03` `P0.28` `P0.29` `P0.30` `P0.31` (AIN0-1 e AIN4-7),
`P0.09` `P0.10` (NFC), `P1.02` `P1.04` `P1.06` `P1.10` `P1.11` `P1.13`.

**Non** ne fanno parte `P0.04`/`AIN2` e `P0.05`/`AIN3`: hanno funzione analogica
ma nessuna restrizione in frequenza. `P1.00`, `P1.09` e tutta la fascia
`P0.06`-`P0.08`, `P0.12`-`P0.17`, `P0.20`-`P0.26` sono a piena velocità.

> Su 43 pad, i GPIO davvero utilizzabili per SPI ad alta frequenza sono 13.
> È il vincolo che ha determinato l'assegnazione qui sotto.

### 5.2 Pad del modulo

Fila **E** = fila esterna (pad dispari sul lato corto), **I** = fila interna
(pad pari, sotto il corpo del modulo → escape obbligatoriamente su strato interno).

| Pad | Serigrafia | nRF52840 | Classe | Uso nel progetto |
|---|---|---|---|---|
| 1 | `P1.11` | P1.11 | LF | libero |
| 2 | `P1.10` | P1.10 | LF | libero |
| 3 | `P0.03` | P0.03/AIN1 | LF | libero |
| 4 | `AI4` | P0.28/AIN4 | LF | libero |
| 5 | `GND` | — | power | GND |
| 6 | `P1.13` | P1.13 | LF | libero |
| 7 | `AI0` | P0.02/AIN0 | LF | libero |
| 8 | `AI5` | P0.29/AIN5 | LF | libero |
| 9 | `AI7` | P0.31/AIN7 | LF | ✅ **LED** |
| 10 | `AI6` | P0.30/AIN6 | LF | ✅ **CHG_STAT** |
| 11 | `XL1` | P0.00/XL1 | — | ✅ **Y1** |
| 12 | `P0.26` | P0.26 | full, I | ✅ **SPI MISO** |
| 13 | `XL2` | P0.01/XL2 | — | ✅ **Y1** |
| 14 | `P0.06` | P0.06 | full, I | ✅ **SPI MOSI** |
| 15 | `AI3` | P0.05/AIN3 | full, E | ✅ **IMU_INT1** |
| 16 | `P0.08` | P0.08 | full, I | ✅ **SPI SCK** |
| 17 | `P1.09` | P1.09 | full, E | ✅ **IMU_INT2** |
| 18 | `AI2` | P0.04/AIN2 | full, I | riserva (portare a test pad) |
| 19 | `VDD` * | VDD | power | ✅ **rail 3,0 V** (uscita REG0) |
| 20 | `P12` | P0.12 | full, I | ✅ **CS_FLASH** |
| 21 | `GND` | — | power | GND |
| 22 | `P0.07` | P0.07 | full, I | ✅ **CS_IMU** |
| 23 | `VDH` | VDDH | power | ✅ **LiPo diretta** |
| 24 | `GND` | — | power | GND |
| 25 | `DCH` | DCCH | power | ✅ **L1 10 µH → VDD** |
| 26 | `RST` | P0.18/RESET | reset | test pad |
| 27 | `VBS` | VBUS | power | non collegato |
| 28 | `P15` | P0.15 | full | libero |
| 29 | `D-` | USB D- | — | non collegato |
| 30 | `P17` | P0.17 | full | libero |
| 31 | `D+` | USB D+ | — | non collegato |
| 32 | `P0.20` | P0.20 | full | libero |
| 33 | `P0.13` | P0.13 | full | libero |
| 34 | `P0.22` | P0.22 | full | libero |
| 35 | `P0.24` | P0.24 | full | libero |
| 36 | `P1.00` | P1.00 | full | libero |
| 37 | `SWD` | SWDIO | debug | ✅ **pad SWD** |
| 38 | `P1.02` | P1.02 | LF | libero |
| 39 | `SWC` | SWDCLK | debug | ✅ **pad SWD** |
| 40 | `P1.04` | P1.04 | LF | libero |
| 41 | `NF1` | P0.09/NFC1 | LF + NFC | ❌ non usare |
| 42 | `P1.06` | P1.06 | LF | libero |
| 43 | `NF2` | P0.10/NFC2 | LF + NFC | ❌ non usare |

\* Il simbolo EasyEDA chiama questo pad `VCC`; il manuale Ebyte lo chiama `VDD`.
È lo stesso pad 19.

### 5.3 Geometria dei pad

Dal footprint generato (origine al centro del modulo, 13 × 18 mm):

- **Lato corto "freddo"** (pad 11-25), opposto all'antenna: due file sfalsate,
  dispari sulla fila esterna, pari sulla fila interna (sotto il corpo)
- **Lati lunghi**: pad 1-10 su un lato, pad 26-43 sull'altro, anch'essi sfalsati
- **Antenna**: striscia di ~2,2 mm sul lato corto opposto ai pad 11-25 → è lì
  che va il keepout

### 5.4 Assegnazione funzionale — congelata

| Segnale | nRF52840 | Pad | Note |
|---|---|---|---|
| SPI SCK | `P0.08` | 16 | piena velocità |
| SPI MOSI | `P0.06` | 14 | piena velocità |
| SPI MISO | `P0.26` | 12 | piena velocità |
| CS_IMU | `P0.07` | 22 | pull-up 10k |
| CS_FLASH | `P0.12` | 20 | pull-up 10k — **non montato in v2** |
| IMU_INT1 | `P0.05` | 15 | watermark FIFO |
| IMU_INT2 | `P1.09` | 17 | wake / doppio tap |
| CHG_STAT | `P0.30` | 10 | open-drain, pull-up 100k |
| LED | `P0.31` | 9 | resistore in serie |
| riserva | `P0.04` | 18 | unico pin veloce ancora libero sul lato freddo |

### 5.5 Perché questa assegnazione

1. **Tutto il traffico veloce sul lato corto opposto all'antenna.** SPI, interrupt
   e alimentazione escono dallo stesso lato: le tracce commutanti non passano mai
   vicino all'antenna, e IMU e flash si piazzano tutti in quella zona.
2. **Interrupt sulla fila esterna** (pad 15 e 17): sono gli unici due pin veloci
   della fila esterna del lato freddo, e non richiedono escape sotto il modulo.
3. **CHG_STAT e LED sui pin LF** del lato lungo, quelli più vicini al lato freddo:
   sono segnali lenti, sprecare pin veloci su di loro sarebbe stato un errore.
4. **`P0.04` tenuto libero**: è l'ultima risorsa veloce. Portarlo a un test pad
   costa nulla ora e vale molto se in bring-up serve una linea in più.

### 5.6 Pin vietati

| Pin | Motivo |
|---|---|
| `P0.00` / `P0.01` (pad 11/13) | quarzo 32,768 kHz (Y1) |
| `P0.09` / `P0.10` (pad 41/43) | NFC di default; usabili come GPIO solo via UICR `NFCPINS`, e sono comunque LF |
| `P0.18` (pad 26) | reset |
| tutti i pin **LF** | mai per SCK/MOSI/MISO — vedi §5.1 |

### 5.7 Conseguenze sul layout

- I cinque segnali SPI escono da pad della **fila interna**, sotto il corpo del
  modulo: l'escape va fatto con via verso uno strato interno. Ebyte raccomanda
  esplicitamente di **non** far passare routing digitale veloce sullo strato
  opposto sotto il modulo e di mettere rame ben collegato a massa sotto l'area di
  contatto → **L2 piano di massa continuo sotto il modulo**, segnali su L3.
- I pad `SWD`/`SWC` (37/39) stanno sul lato lungo, dalla parte dell'antenna: le
  tracce verso i test pad vanno portate sul lato freddo restando fuori dalla zona
  di keepout.
- `DCH` (25) è il nodo di commutazione di REG0: L1 va tenuto corto e il loop
  `VDH` → L1 → `VDD` compatto, lontano da `XL1`/`XL2` (pad 11/13).

---

## 6. Budget energetico

Assunzioni: cella **301220** (80 mAh dichiarati, 60 prudenti), derating 85%,
DC/DC attivo, sync oraria, advertising 2 s. L'autonomia scala linearmente con la capacità reale:
0,161 mA × 24 h = **3,9 mAh al giorno**.

| Voce | Corrente |
|---|---|
| Idle (accel LP + pedometro, MCU sleep, flash DPD, leakage) | 26 µA |
| Sessioni giroscopio (ZUPT, ~90 min/giorno) | 123 µA |
| Radio (advertising + connessioni) | 10 µA |
| Varie | 2 µA |
| **Totale** | **~161 µA** |
| **Autonomia** | **~18 giorni** sugli 80 mAh dichiarati, **~13 giorni** sui 60 mAh prudenti |

> ⚠️ Valori tipici da datasheet a 25 °C / 3,0 V. **Da verificare sul silicio
> reale** appena la board è funzionante.

**Fase di taratura (v1):** la flash assorbe ~20 mA in scrittura → circa +200 µA
medi durante il logging, cioè ~361 µA totali. Autonomia in logging **~6-8
giorni**: una settimana di camminate si registra senza toccare il caricabatterie.

---

## 7. Meccanica

| Parametro | Valore |
|---|---|
| PCB | **24 × 41 mm**, 4 strati, spessore 0,8 mm |
| Capsula | **~28 × 45 × 5,1 mm** |
| Cella | LiPo **301220** (3,0 × 12 × 20 mm), **80 mAh dichiarati**, PCM integrato |
| Costruzione | Capsula rigida in resina (potting) + guaina silicone platinico separata |

> ⚠️ **Quote cresciute** rispetto al piano iniziale (26 × 14 mm / 30 × 16 × 5 mm):
> il modulo E73 è 18 × 13 mm, contro i 15,5 × 10,5 mm dell'MDBT50Q previsto.
> Alla caviglia, sotto i pantaloni, resta comodo — ma l'outline va fissato ora.

### Disposizione "corta e larga" — decisa il 2026-08-20

Il vincolo dichiarato è: **capsula bassa, ma non lunga**. 61 mm non sono
indossabili, e il modulo da solo ne occupa 18.

Niente si sovrappone in verticale, ma invece di mettere tutto in fila si sfrutta
la **larghezza**: la cella occupa mezza scheda in larghezza, e nell'altra metà
ci stanno carica e alimentazione.

| Zona | Y | Faccia superiore | Faccia inferiore |
|---|---|---|---|
| **cella** | 0-21 mm | a destra solo rame (pogo, pad di test), a sinistra carica e alimentazione | **cella** 12 × 20, a destra |
| **modulo** | 22-41 mm | modulo a sinistra, striscia componenti a destra (IMU, flash, quarzo) | libera |
| **antenna** | 37,4-41 mm | keepout su tutti e 4 gli strati | keepout |

**Spessore: 0,8 (PCB) + 3,3 (cella con tolleranza) + 2 × 0,5 (resina) = 5,1 mm.**
Scheda 24 × 41 mm, capsula ~28 × 45 × 5,1 mm.

Assemblaggio **su una faccia sola**: sul retro c'è solo la cella, incollata. I due
fili passano in fori passanti e si saldano davanti.

### Il modulo è il pavimento: 3,0 mm

Sotto i 4,8 mm non si scende senza cambiare modulo. Le tre voci:

- **modulo E73: 3,00 ± 0,1 mm** — ✅ confermato sul **disegno meccanico** del
  manuale Ebyte (pag. 6), non solo sul modello 3D. Modulo completo:
  18,0 ± 0,1 × 13,0 ± 0,1 × 3,00 ± 0,1 mm, 43 pad
- PCB 0,8 mm — già il minimo sensato a 4 strati
- pareti di resina 0,5 mm per lato

Tutto il resto (IMU 0,83, flash 0,8, carica ~1,1, bulk 1206 ~1,6) sta comodamente
sotto i 3,0 mm e non tocca il totale, perché vive nella zona B dove la faccia
opposta è vuota.

### Cella: 301220, e perché non una più grande

La 401220 del piano iniziale era spessa 4,0 mm e da sola avrebbe portato la
capsula a 5,8 mm. La 301220 è la stessa pianta, 1 mm più sottile.

**La larghezza della cella è vincolata, non libera.** La cella occupa metà della
larghezza della scheda; l'altra metà serve per carica e alimentazione, che
devono stare vicino ai pad del modulo. Una cella da 20 mm di larghezza (es. la
302025 da 140 mAh) lascerebbe 3 mm: non ci sta niente, e L1 finirebbe a 10 mm
dal pad `DCH` invece che a 4.

| | Capacità | Larghezza | Effetto |
|---|---|---|---|
| **301220** ✅ | 80 mAh dichiarati | 12 mm | resta spazio per l'alimentazione |
| 302025 | ~140 mAh dichiarati | 20 mm | scheda +14 mm oppure alimentazione lontana dal modulo |

80 mAh × 0,85 ÷ 0,161 mA = **~18 giorni**, ben oltre il requisito di §1. La
capacità in più della 302025 non serviva e costava lunghezza.

### Dati della cella acquistata

Fonte: pagina del venditore (AliExpress, modello 301220, ~4,7 €/pz in confezione
da 3). Non è un datasheet, ma dichiara i parametri che servono.

| Parametro | Valore | Conseguenza |
|---|---|---|
| Dimensioni | 3 × 12 × 20 mm | ✅ combacia con la zona cella del layout |
| Capacità | 80 mAh dichiarati | autonomia ~18 giorni |
| **PCM** | **integrato** ✅ | requisito soddisfatto |
| Corrente di carica max | **1C** = 80 mA | i nostri 50 mA sono 0,63C ✅ |
| Carica standard | 0,5C CC fino a 4,25 V, poi CV | il MCP73831 fa esattamente questo |
| Scarica max | 1C | irrilevante: noi tiriamo 0,16 mA |
| Fine scarica | **2,75 V** | ⚠️ vedi sotto |
| Fili | liberi, rosso/nero | ✅ vanno diretti nei due fori di J2 |

> ⚠️ **I 80 mAh sono ottimistici.** 3 × 12 × 20 mm fanno 0,72 cm³, cioè
> 411 Wh/l: sopra quello che ci si aspetta da una cella piccola con PCM
> (250-350). **Contare su 55-70 mAh reali** → 12-15 giorni. Misurare la capacità
> vera alla prima carica completa.

> 🔴 **Il PCM stacca a 2,75 V, ma la flash muore prima.** Con VEXDIF = 0,3 V
> (doc 02 §3.2), a cella 2,75 V il rail vale ~2,45 V, sotto il minimo della
> W25Q256JV (2,7 V). La protezione della cella **non** protegge i dati: il
> firmware deve smettere di scrivere in flash sotto i ~3,2 V di cella, molto
> prima che intervenga il PCM.

> **Perché allungare non dà fastidio.** L'asse lungo della capsula corre **lungo
> la gamba**, dove il profilo è quasi rettilineo: 52 mm sopra il malleolo ci
> stanno. È la *larghezza* che deve avvolgere la circonferenza, e resta a 21 mm.

### Vincoli non negoziabili

1. **Antirotazione.** Il sensore misura su tre assi fissi: hanno significato solo
   se l'orientamento rispetto alla gamba è ripetibile. Serve **incastro con
   chiavetta meccanica**, non attrito.
2. **Keepout antenna.** Sotto l'antenna del modulo: nessun rame su nessuno strato,
   nessuna vite, **e mai la sacca LiPo** (è alluminio, spegne l'antenna).
   Il modulo va a un'estremità, con il lato antenna che sporge oltre il bordo
   della cella. Quell'estremità orientata **verso l'alto** sulla gamba.
3. **Vincolo agli urti.** 10-16 g a ogni tallonata. La cella va bloccata con
   schiuma precompressa prima del potting: nessuna massa libera, nessun
   componente alto.
4. **Cinturino sopra il malleolo**, dove la gamba si allarga: il conico impedisce
   lo scivolamento verso il basso.
5. **Pogo pin sulla faccia esterna**, non contro la pelle (sudore + contatti =
   accoppiamento pessimo). Recessati in una scanalatura per non strisciarli
   sui pantaloni.

### Tenuta stagna

Requisito: **doccia e piscina senza toglierlo**. Il potting previsto per gli urti
risolve anche l'acqua — stessa scelta, doppio beneficio. La pressione non è il
vincolo (una piscina è ~0,2 bar): il vincolo è la **tenuta nel tempo**.

| Punto | Requisito |
|---|---|
| Pogo pin | Unico foro nella capsula. Già sulla faccia esterna |
| Cella LiPo | **Sigillata completamente**, non solo protetta. È il componente che soffre di più l'umidità nel lungo periodo |
| Guaina | Silicone platinico: regge cloro e acqua salata |

**🔴 Regola d'uso da mettere nell'app:** mai in carica se bagnato.
Contatti umidi + corrente = corrosione garantita. In acqua senza tensione
applicata non succede nulla; il danno avviene al momento della ricarica.
Sciacquare con acqua dolce dopo il mare.

> **Perché non si toglie:** rimetterlo con un orientamento diverso rompe la
> ripetibilità dei dati — lo stesso motivo per cui esiste la chiavetta
> antirotazione. Meglio un dispositivo che riconosce il nuoto (doc 03 §5)
> che uno da togliere e rimettere.

### Scartato

**Batteria distribuita nel cinturino** per assottigliare la capsula: richiede un
flex che si flette a ogni passo per mesi. Modo affidabile di introdurre un guasto
intermittente impossibile da diagnosticare.

---

## 8. Comunicazione iPhone

Nessun MFi richiesto: BLE con GATT custom + app propria.

### Due canali separati

| | Sync sommario | Dump grezzo |
|---|---|---|
| Contenuto | Passi/ora, distanza, batteria | Log completo a 416 Hz |
| Frequenza | Ogni ora, pochi secondi | Solo sotto carica, solo v1 |
| Volume | Centinaia di byte | Decine di MB |

Con **2M PHY + Data Length Extension** su iPhone: ~120-170 kB/s reali.

### Vincoli iOS da rispettare in fase di progetto

1. **MTU:** iOS accetta fino a 185 byte di payload nelle notifiche. Usa
   **notifiche, non indicazioni** (le indicazioni aspettano l'ack → throughput
   dimezzato).
2. **Connection interval:** Apple impone minimo 15 ms e multiplo di 15. Parametri
   non conformi vengono rifiutati e resti sui default.
   Sync sommario → intervallo lungo + slave latency alta. Dump → intervallo minimo.
3. **Background:** serve il background mode `bluetooth-central` con **State
   Preservation and Restoration**. In background iOS scansiona **solo per UUID di
   servizio espliciti**, mai wildcard → l'UUID custom va cablato nell'app.
4. **Advertising:** 2 s di default (pochi µA). Finestra veloce solo su evento
   (movimento rilevato, dispositivo sul caricatore).

### HealthKit

Scrittura come `HKQuantityTypeIdentifier.stepCount`.

> ⚠️ Anche l'iPhone scrive i propri passi. Salute **non somma** le sorgenti
> sovrapposte: sceglie in base alla priorità delle sorgenti impostata dall'utente.
> Va gestito: o si accetta la priorità utente, o si tengono i propri dati in un
> contenitore separato usando HealthKit solo per un totale consolidato.
