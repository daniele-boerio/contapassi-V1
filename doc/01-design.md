# Contapassi ad alta precisione — Documento di design

**Versione doc:** 1.0
**Stato:** requisiti congelati, schematico da iniziare
**Target produzione:** KiCad 10.0.5 → JLCPCB (PCB + PCBA)

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
  pogo (+) ──▶ TVS + prot. inversione ──▶ MCP73831 ──▶ LiPo 401220 (~55 mAh, con PCM)
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

### 4.1 Decisioni chiave e motivazioni

| # | Decisione | Motivo |
|---|---|---|
| 1 | **Pedometro in hardware nel sensore + FIFO** | MCU sveglio < 1% del tempo. È ciò che rende possibile 55 mAh per una settimana. Event-driven, mai polling |
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

## 5. Mappatura pin — DA COSTRUIRE

> 🔴 **Questa tabella è ancora quella dell'ISP1807: NON è valida.**
> Modulo definitivo: **Ebyte E73-2G4M08S1C** (`C356849`).
> Va ricostruita sul pinout del datasheet Ebyte prima dello schematico.
> È l'ultimo blocco prima di poter disegnare.

### Pad già identificati sul simbolo E73

| Pad | Funzione | Uso nel progetto |
|---|---|---|
| `VDH` | VDDH, ingresso alta tensione | ✅ **LiPo diretta** |
| `DCH` | DCCH, induttore DC/DC di REG0 | ✅ **L1 (~10 µH)** |
| `XL1` / `XL2` | quarzo bassa frequenza | ✅ **Y1 32,768 kHz + 2C** |
| `VCC` | VDD, dominio logico | 3,0 V dopo REGOUT0 |
| `VBS` | VBUS (ingresso USB) | non usato |
| `SWD` / `SWC` | SWDIO / SWCLK | ✅ **pad di programmazione** |
| `RST` | reset | pad di test |
| `D+` / `D-` | USB | non usati |
| `NF1` / `NF2` | NFC (P0.09/P0.10) | ❌ evitare |

### Assegnazione funzionale target

Da mappare sui GPIO effettivamente esposti dall'E73:

| Segnale | Dir | Note |
|---|---|---|
| SPI SCK | out | condiviso |
| SPI MOSI | out | condiviso |
| SPI MISO | in | condiviso |
| CS_IMU | out | pull-up 10k |
| CS_FLASH | out | pull-up 10k — **non montato in v2** |
| IMU_INT1 | in | watermark FIFO |
| IMU_INT2 | in | wake / doppio tap |
| CHG_STAT | in | open-drain, pull-up 100k |
| LED | out | resistore in serie |

### Pin vietati

| Pin | Motivo |
|---|---|
| P0.00 / P0.01 | usati dal quarzo 32,768 kHz (Y1) |
| P0.09 / P0.10 | NFC di default (`NF1`/`NF2`). Usabili come GPIO solo via config UICR; prima di quella si comportano in modo inatteso |
| P0.18 | reset |

### Perché due linee di interrupt e non una

- **INT1** = watermark FIFO ("ho N campioni pronti")
- **INT2** = eventi asincroni (movimento rilevato, doppio tap)

Con una linea sola servirebbe leggere i registri di stato a ogni interrupt per
capire la causa: una transazione SPI in più ogni volta e MCU svegliato a vuoto.

### Da verificare sul datasheet Ebyte

- [ ] Quali GPIO sono realmente esposti sui pad, e con quale numerazione
- [ ] Valore dell'induttore REG0 raccomandato (incrocia col datasheet Nordic)
- [ ] Quote e forma del keepout d'antenna
- [ ] Conferma delle sigle lette dal simbolo EasyEDA

---

## 6. Budget energetico

Assunzioni: cella 55 mAh, derating 85%, DC/DC attivo, sync oraria, advertising 2 s.

| Voce | Corrente |
|---|---|
| Idle (accel LP + pedometro, MCU sleep, flash DPD, leakage) | 26 µA |
| Sessioni giroscopio (ZUPT, ~90 min/giorno) | 123 µA |
| Radio (advertising + connessioni) | 10 µA |
| Varie | 2 µA |
| **Totale** | **~161 µA** |
| **Autonomia** | **~10 giorni** |

> ⚠️ Valori tipici da datasheet a 25 °C / 3,0 V. **Da verificare sul silicio
> reale** appena la board è funzionante.

**Fase di taratura (v1):** la flash assorbe ~20 mA in scrittura → circa +200 µA
medi durante il logging. Autonomia 2-4 giorni. È temporaneo, si ricarica la sera.

---

## 7. Meccanica

| Parametro | Valore |
|---|---|
| PCB | **~32 × 18 mm**, 4 strati, spessore 0,8 mm |
| Capsula | **~36 × 22 × 5,5 mm** |
| Cella | LiPo 401220, ~55 mAh, **con PCM integrato** |
| Costruzione | Capsula rigida in resina (potting) + guaina silicone platinico separata |

> ⚠️ **Quote cresciute** rispetto al piano iniziale (26 × 14 mm / 30 × 16 × 5 mm):
> il modulo E73 è 18 × 13 mm, contro i 15,5 × 10,5 mm dell'MDBT50Q previsto.
> Alla caviglia, sotto i pantaloni, resta comodo — ma l'outline va fissato ora.

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
