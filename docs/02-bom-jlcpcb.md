# BOM e checklist JLCPCB

**Stato:** componenti verificati sul catalogo JLCPCB. ✅ = confermato in stock.
**Buona notizia trasversale:** tutte le righe hanno **Min: 1**. Nessun minimo
d'ordine forzato — il rischio di costo temuto non si è materializzato.

---

## 1. Tooling

| Cosa | Nota |
|---|---|
| KiCad | **9.0** — restare qui, non aggiornare a metà progetto |
| Plugin | **kicad-jlcpcb-tools** (Bouni) — repo custom, vedi §6 |
| Conversione parti | **easyeda2kicad** — genera simbolo/footprint/3D da codice LCSC |

---

## 2. BOM confermata

| Rif | Componente | LCSC | Package | Stock | Prezzo |
|---|---|---|---|---|---|
| U1 | **E73-2G4M08S1C** (Ebyte, nRF52840) | `C356849` | SMD 18×13 mm | 2437 ✅ | $8,14 |
| U2 | **LSM6DSV16XTR** (ST, IMU 6 assi) | `C5267406` | LGA-14 (2,5×3 mm) | ✅ | ~$2,88 |
| U3 | **W25Q256JVEIQ** (Winbond, 32 MB) | `C97522` | WSON-8-EP (6×8) | 16763 ✅ | €3,76 |
| U4 | **MCP73831T-2ATI/OT** (Microchip) | `C14879` | SOT-23-5 | 1957 ✅ | €0,96 |
| L1 | **MLZ1608M100WT000** (Murata, 10 µH, Isat 90 mA) | `C76798` | 0603 | 61743 ✅ | ~$0,02 |
| Y1 | **Q13FC13500004** (Epson, 32,768 kHz, CL 12,5 pF) | `C32346` | SMD3215-2P | 557062 ✅ **Basic** | ~$0,10 |
| C1, C2 | **18 pF ±5% C0G** (carico di Y1) | `C1549` | 0402 | 1306168 ✅ **Basic** | ~$0,002 |
| C_bulk | **47 µF 10 V** (serbatoio VDDH) | `C96123` | 1206 | 1054417 ✅ **Basic** | ~$0,03 |
| Q1 | **AO3401A** (P-MOSFET, blocco inversione) | `C15127` | SOT-23 | 545691 ✅ **Basic** | ~$0,03 |
| D1 | **PESD5V0S1BA** (TVS bidirezionale 5 V) | `C2827694` | SOD-323 | 1011482 ✅ | ~$0,01 |
| D2 | **LED rosso** | `C2286` | 0603 | 6043727 ✅ **Basic** | ~$0,004 |
| C4, C5, C10 | 4,7 µF 16 V X5R | `C19666` | 0603 | ✅ **Basic** | — |
| C6-C9 | 100 nF 16 V X7R | `C1525` | 0402 | ✅ **Basic** | — |
| R1-R4 | 10 kΩ (pull-up CS_IMU, CS_FLASH, WP#, HOLD#) | `C25744` | 0402 | ✅ **Basic** | — |
| R5, R8 | 100 kΩ (pull-up CHG_STAT, gate di Q1) | `C25741` | 0402 | ✅ **Basic** | — |
| R6 | 20 kΩ (ISET = 50 mA) | `C25765` | 0402 | ✅ **Basic** | — |
| R7 | 1 kΩ (serie LED) | `C11702` | 0402 | ✅ **Basic** | — |
| J1 | **piazzole di contatto** per il cavo magnetico — nessun componente | — | `PogoPads_2P_P5.0mm` | — | — |
| J2 | **piazzole di saldatura** per i fili della cella | — | `CellPads_2P_P4.0mm` | — | — |
| TP1-TP6 | pad di test (SWDIO, SWCLK, GND, +3V0, RESET, P0.04) | — | 1,5 × 1,5 mm | — | — |

**Righe Extended: 6** (U1, U2, U3, U4, L1, D1). Tutto il resto è Basic.

### 🔴 Piazzole invece di pogo pin — cambio rispetto al doc 01 §7

Il doc 01 prevede **pogo pin montati sul dispositivo**. I footprint disegnati
fanno l'opposto: sul dispositivo ci sono **piazzole piatte dorate**, e le molle
stanno sul cavo di ricarica.

**Perché:** un pogo pin è un pistone che si muove. Per montarlo servono un foro
nella capsula e una tenuta attorno a una parte mobile — cioè l'unico punto in cui
la resina non può sigillare niente, sul dispositivo che deve stare in piscina.
Con le piazzole la capsula non ha **nessuna apertura**: la resina si ferma a filo
del rame, e il rame è già dorato se si ordina la finitura **ENIG**.

Costo del cambio: il cavo di ricarica dev'essere del tipo "magnetico con puntali",
non un semplice cavo con contatti piatti.

- [ ] **Decisione da confermare.** Se preferisci i pogo pin sul dispositivo,
      il footprint va rifatto (30 minuti) e il doc 01 §7 resta com'è
- [ ] Il **passo di 5,0 mm** delle piazzole è un valore di partenza: va misurato
      sul cavo magnetico effettivamente acquistato, poi cambiato in
      `hardware/tools/gen_footprints.py` (una riga)
- [ ] Ordinare il PCB con finitura **ENIG**, non HASL: le piazzole di contatto
      sono strisciate mille volte e l'oro non si ossida

### Insieme da non montare in v2

La v2 toglie la flash e quello che serve solo a lei: **U3, R2, R3, R4, C9**.
Stesso layout, cinque righe marcate DNP. Nient'altro cambia.

### Stato dello schematico

Prima stesura generata da `hardware/tools/gen_schematic.py` e verificata:

- **ERC pulito, 0 violazioni** (`kicad-cli sch erc --severity-all`)
- 37 componenti, 26 reti, netlist controllata rete per rete
- I pin non usati del modulo hanno un **no-connect esplicito**, non sono
  semplicemente lasciati vuoti

> ⚠️ È uno schematico **"a netlist"**: i collegamenti sono etichette sui pin, non
> fili tirati a mano. È corretto ma non è leggibile come un disegno fatto bene.
> Va riordinato in Eeschema — e da quel momento **non rilanciare il generatore**,
> che riscrive il file da zero.

I tipi elettrici dei pin (`power_in`, `tri_state`, …) sono assegnati da
`hardware/tools/fix_pin_types.py`: easyeda2kicad li marca tutti `unspecified`, e
con quelli l'ERC non serve a niente. **Va rilanciato dopo ogni rigenerazione di
un simbolo con easyeda2kicad.**

### Stato del layout

Contorno, piazzamento, keepout e piani di massa generati da
`hardware/tools/gen_pcb.py` e verificati con `kicad-cli pcb drc`:

- **0 errori.** Restano 7 avvisi `silk_over_copper` (serigrafia dei contorni
  componente che tocca i pad): cosmetici, JLC taglia la serigrafia sui pad
- **80 collegamenti da instradare**: è tutto il lavoro che manca
- Keepout antenna su **tutti e 4 gli strati**, tutta la larghezza, da Y 37,4
- Piani di massa su `In1.Cu` e `B.Cu`
- Sigle dei componenti su `F.Fab`, non in serigrafia: a 24 × 41 mm le scritte
  si sovrapporrebbero ai componenti

Il piazzamento non è instradato: le piste vanno tirate in pcbnew. Da quel
momento **non rilanciare `gen_pcb.py`**, che riscrive il file da zero.

### Note sui componenti

**U1 — E73-2G4M08S1C.** Sostituisce l'MDBT50Q-1MV2 (non disponibile).
Stesso chip nRF52840, modulo certificato con antenna integrata.

- ✅ **VDDH esposto** (pad `VDH` nel simbolo) → la scelta "LiPo diretta su VDDH"
  resta valida, nessun LDO da reintrodurre
- 🔴 **`DCH` esposto** → l'induttore di REG0 **non è integrato**, va aggiunto (L1)
- 🔴 **`XL1`/`XL2` esposti** → il quarzo 32,768 kHz **non è integrato** (Y1)
- ⚠️ **18 × 13 mm** → il PCB deve crescere (vedi doc 01 §7)
- ⚠️ **X-ray Inspection: Required** → costo aggiuntivo sull'ordine, **e il
  montaggio manuale del solo modulo non è più un'opzione**: ha pad sotto il
  corpo, non solo castellati

> Sigle lette dal simbolo EasyEDA: **confermare tutto sul datasheet Ebyte**
> (link "Download" nella pagina JLCPCB del componente).

**U2 — LSM6DSV16XTR** → `C5267406`, verificato nel catalogo PCBA di JLCPCB
(Extended, LGA-14 2,5×3 mm, MSL 1). "TR" = Tape & Reel, è solo il confezionamento.

> Esiste anche la riga `C42388605` ("LSM6DSV16X", New Arrivals, X-ray richiesta).
> È lo stesso chip: **usare `C5267406`**, e ricontrollare la scorta il giorno
> dell'ordine — la pagina JLC non espone lo stock senza login.

**U3 — W25Q256JVEIQ.** Variante 2,7-3,6 V, compatibile con il dominio a 3,0 V
scelto in §3. Solo v1.

> ⚠️ Se un giorno passassi al dominio a 1,8 V, questa parte **non funziona**.
> La variante corretta sarebbe `C2940048` (W25Q256JWEIQ, 1,7-1,95 V).

**U4 — MCP73831T-2ATI/OT.** Il "2" indica i 4,20 V corretti per LiPo.

- [ ] Aprire il PDF e verificare nella tabella di ordinazione che l'uscita STAT
      di questa variante sia leggibile da GPIO
- [ ] Alternativa se non lo è: `C424093` (`-2ACI/OT`, 2874 pz)
- [x] **Corrente di carica: verificata.** La 301220 scelta dichiara **carica
      max 1C = 80 mA**. I 50 mA di `R6 = 20 kΩ` sono **0,63C**: sotto il massimo
      e sopra i ~50 mA oltre i quali l'MCP73831 lavora con buona precisione.
      Ricarica completa in ~2 ore. Nessun cambio di componente

**L1 — induttore REG0.** Senza, REG0 resta in modalità LDO: scendere da 4,0 V a
3,0 V dissiperebbe il **25% su tutto il consumo della scheda**. Un componente
0603 vale il 25% di autonomia.

✅ **Valore confermato**: *nRF52840 PS*, §56.4 "Circuit configuration no. 4",
tabella 157 (designator L4): **10 µH, chip inductor, IDC min = 80 mA, ±10%,
0603**. Va **tra `DCH` (DCCH) e `VDD`**, cioè sull'uscita di REG0.

🔴 **Trappola: qui il componente Basic non si può usare.** L'unico 10 µH 0603
Basic in catalogo è `C1035` (Sunlord SDFL1608S100KTF) ed è un induttore *di
segnale*: **corrente nominale 3 mA**, DCR 1,85 Ω. Su un convertitore che deve
passare decine di mA satura e basta. Il campo "10 µH 0603" da solo non dice nulla:
va letta la corrente.

| LCSC | Modello | Tolleranza | Isat | I nom. | DCR | Lib |
|---|---|---|---|---|---|---|
| `C1035` | SDFL1608S100KTF | ±10% | — | **3 mA** ❌ | 1,85 Ω | Basic |
| **`C76798`** | **MLZ1608M100WT000** (Murata) | ±20% | **90 mA** ✅ | 250 mA | 1,05 Ω | Extended |
| `C87216` | LBMF1608T100K | ±10% | *non dichiarato* | 80 mA | 0,36 Ω | Extended |
| `C92970` | BRL1608T100M | ±20% | 170 mA | 170 mA | 2 Ω | Extended |

**Scelto `C76798`**: è l'unico che dichiara esplicitamente una **Isat (90 mA)
sopra gli 80 mA richiesti** da Nordic, con 61k pezzi a magazzino. La tolleranza
±20% non è un problema su un induttore di buck — Nordic stessa usa ±20% su L2
nella stessa tabella. `C87216` avrebbe la tolleranza giusta e un DCR migliore,
ma non pubblica la corrente di saturazione: è quella che conta.

**Y1 — quarzo 32,768 kHz.** Non strettamente obbligatorio, ma consigliato: senza,
l'RC interno richiede ricalibrazioni periodiche e **allarga le finestre di
ricezione BLE**, cioè consuma di più proprio dove stiamo ottimizzando. Costa
~2 µA e dà un orologio che non deriva tra una sync e l'altra.

✅ **Specifica confermata**. Il reference design Nordic (tabella 157, X2 + C16/C17)
usa un cristallo **CL 9 pF con due condensatori da 12 pF**; la tabella di specifica
LFXO (§17.4.3) ammette **CL fino a 12,5 pF**, C0 ≤ 2 pF, ESR ≤ 100 kΩ.

**Scelto `C32346`** (Epson Q13FC13500004, 32,768 kHz, ±20 ppm, **CL 12,5 pF**):
è l'unico 3215 **Basic** in catalogo, con 557k pezzi. Nessun costo di caricamento.

Condensatori di carico: dal reference design Nordic (9 pF con 12 pF) si ricava
una capacità parassita di **~3 pF** per ramo, quindi

`C = 2 × (CL − C_parassita) = 2 × (12,5 − 3) = 19 pF` → **18 pF (`C1549`, Basic)**

- [ ] Il valore parassita 3 pF è dedotto dal reference Nordic, non misurato:
      dipende dal layout. Con 18 pF l'errore residuo vale pochi ppm, e il BLE
      ne tollera ±250 → non è un rischio, ma va ricontrollato se un giorno
      servisse precisione d'orologio migliore
- Alternativa "copia esatta del reference": `C99010` (Epson CL 9 pF, Extended,
  45k pezzi) + 2 × `C1547` (12 pF). Costa una riga Extended in più e fa
  partire l'oscillatore un filo prima. Non vale la spesa

### Componenti NON assemblati da JLC (montaggio manuale)

- **Cella LiPo 301220**, 3,0 × 12 × 20 mm, 80 mAh dichiarati, **PCM integrato**,
  fili liberi. Confezione da 3 a ~10,4 € + spedizione (AliExpress, consegna
  ~2 mesi). La prima montata di solito si sacrifica: 3 pezzi sono il numero giusto
- Nessun pogo pin: sul dispositivo ci sono solo piazzole (vedi sopra)

---

## 3. 🔴 Decisione: dominio a 3,0 V

L'nRF52840 alimentato da VDDH ha REGOUT0 che **di default esce a 1,8 V**, e
questo definisce la tensione di tutta la scheda.

**Scelta: 3,0 V**, impostata scrivendo REGOUT0 nell'UICR al primo flash.

| | 3,0 V (scelto) | 1,8 V (default) |
|---|---|---|
| Flash | `C97522` standard | servirebbe `C2940048` |
| IMU | ✅ (1,71-3,6 V) | ✅ |
| LED | ✅ qualsiasi colore | ⚠️ solo rosso, a fatica |
| Programmatore | anche 3,3 V fissi | **VTref obbligatorio** |
| Consumo | leggermente superiore | leggermente inferiore |

Il guadagno energetico a 1,8 V è marginale rispetto al budget; la compatibilità
semplifica flash, LED e debugger.

**Conseguenza:** il vincolo sul programmatore si rilassa — un debugger economico
a 3,3 V fissi funziona. Il VTref resta preferibile ma non è bloccante.

### 3.1 Due registri UICR, non uno

| Registro | Offset | Valore | Nota |
|---|---|---|---|
| `REGOUT0` | 0x304 | `4` = 3,0 V | il default (`7`) è 1,8 V → **va scritto** |
| `EXTSUPPLY` | 0x300 | `1` = Enabled | consente di alimentare IMU e flash dal pad `VDD` |

`EXTSUPPLY` risulta già abilitato su UICR vergine (cancellata = tutti 1), ma va
**verificato dopo ogni `nrfjprog --eraseall`**: con `EXTSUPPLY = 0` dal pad `VDD`
non si può prelevare corrente, e IMU e flash restano senza alimentazione.

### 3.2 🔴 VEXDIF: il rail a 3,0 V non è garantito per tutta la scarica

*nRF52840 PS*, §16.10.1: **VEXDIF = 0,3 V minimo** — REG0 non può produrre una
tensione più vicina di 0,3 V al VDDH.

| VDDH (cella) | VDD (rail) | Stato |
|---|---|---|
| 4,2 → 3,3 V | 3,0 V | regolato |
| < 3,3 V | ≈ VDDH − 0,3 V | **il rail scende con la cella** |
| 3,0 V | ≈ 2,7 V | limite inferiore della flash W25Q256J**V** |

Non è bloccante — sotto i 3,3 V il degrado è graduale e tutto continua a
funzionare (IMU da 1,71 V, radio da 2,5 V su VDDH) — ma va saputo:

- La flash arriva **esattamente** al suo minimo (2,7 V) quando la cella è a 3,0 V.
  In v1, che scrive in flash, conviene fermare il logging sotto ~3,2 V di cella
- L'app deve mostrare "batteria scarica" intorno a 3,3 V, non a 3,0 V
- Altra voce da misurare in bring-up: `IEX,OFF` limita a **1 mA** la corrente
  prelevabile dal pad `VDD` in System OFF → flash in deep power-down obbligatoria

---

## 4. Basic vs Extended

JLCPCB divide i componenti in due categorie. I **Basic** sono già caricati sulle
macchine. Gli **Extended** richiedono caricamento manuale con **costo fisso per
tipo di componente**, indipendente dalla quantità.

Su un lotto da 5 pezzi questo domina il costo totale.

- Modulo, IMU e flash sono inevitabilmente Extended — sono loro il progetto
- [ ] **Tutti i passivi devono essere Basic**
- [ ] **Consolidare i valori**: se servono 47k, 51k e 56k in punti non critici,
      usarne uno solo per tutti e tre

---

## 5. Parametri di produzione

| Parametro | Scelta | Motivo |
|---|---|---|
| Dimensioni | **24 × 41 mm** | Disposizione corta e larga — vedi doc 01 §7 |
| Strati | 4 | — |
| Spessore | **0,8 mm** | Standard, stesso prezzo di 1,6. Guadagna ~1 mm nella capsula |
| Passivi | 0402 | Basic Parts + spazio |
| Assemblaggio | provare su una faccia sola | Il doppio lato costa di più e allunga i tempi |
| Separazione | **V-cut** dove la geometria lo consente | Le mouse bites lasciano sbavature, e la capsula deve incastrarsi con precisione |
| Ispezione | **X-ray obbligatoria** (richiesta dal modulo) | Costo aggiuntivo da mettere a preventivo |

---

## 6. Installazione plugin Bouni

Non è nel repository ufficiale KiCad. Va aggiunto a mano:

1. Plugin and Content Manager → **Gestisci...**
2. **➕** → incolla l'URL:
   `https://raw.githubusercontent.com/Bouni/bouni-kicad-repository/main/repository.json`
3. Nome: `Bouni` → salva
4. Seleziona il nuovo repository dalla tendina in alto
5. Installa **KiCad JLCPCB tools** → **Applica i cambiamenti**

> Se il repository non compare nella tendina, chiudi e riapri il Plugin Manager.

**Nota d'uso:** il plugin assegna i codici LCSC ai *footprint già piazzati sul
PCB*. Per la semplice verifica di disponibilità il sito jlcpcb.com è più rapido.

**Fabrication Toolkit** (bennymeg, nel repo ufficiale) è un'alternativa valida per
generare gerber/BOM/CPL, ma non cerca il catalogo da dentro KiCad.

---

## 7. Trappole note

### 🔴 Rotazioni nel file CPL

Errore numero uno dei primi ordini PCBA. JLCPCB usa convenzioni di orientamento
che spesso **non coincidono** con quelle delle librerie KiCad → componenti saldati
ruotati di 90°. Il plugin ha un **Rotation manager** con le correzioni note.

- [ ] **Controllare sempre l'anteprima grafica** che JLC mostra prima di confermare
- [ ] Verificare componente per componente dove sta il pin 1

### 🔴 Footprint del modulo radio

Usa **easyeda2kicad** con il codice `C356849` invece di disegnarlo a mano: genera
simbolo, footprint e modello 3D.

- [ ] **Verificare comunque il risultato contro il datasheet Ebyte**, in
      particolare il keepout d'antenna. È l'unica zona della scheda dove un
      errore non si recupera con un filo volante

### 🟡 Clearance dal bordo e pannellizzazione

JLC ha una distanza minima dei componenti dal bordo scheda. Il modulo che
"sporge oltre il bordo della batteria" è un requisito **meccanico dentro la
capsula**, non un componente a filo del bordo PCB.

- [ ] Verificare la regola di clearance prima di fissare l'outline
- [ ] Decidere V-cut vs mouse bites **prima** del layout

---

## 8. Ordine dei lavori

1. [x] Verificare i componenti sul catalogo JLCPCB
2. [x] Annotare il codice LCSC dell'LSM6DSV16XTR → `C5267406`
3. [x] Scaricare il datasheet Ebyte E73-2G4M08S1C → `docs/datasheet/`
4. [x] **Rifare la mappatura pin** (doc 01 §5) sul pinout Ebyte
5. [x] L1, Y1 e condensatori di carico scelti sul catalogo JLCPCB (§2)
6. [x] **Cella scelta e verificata: 301220**, 80 mAh, PCM integrato, carica
       max 1C (doc 01 §7)
7. [x] Generare simbolo e footprint con easyeda2kicad → `hardware/lib/`
8. [x] Schematico — prima stesura generata, ERC pulito; **da riordinare a mano**
9. [ ] Layout — [x] contorno, piazzamento, keepout e piani di massa generati;
       resta l'instradamento
10. [ ] Export BOM + CPL con il plugin
11. [ ] Controllo anteprima JLC pin per pin

---

## 9. Checklist pre-ordine

- [ ] DRC pulito
- [ ] ERC pulito
- [ ] Keepout antenna verificato su tutti e 4 gli strati (nessun rame, nessuna via)
- [ ] Induttore REG0 da 10 µH tra `DCH` e `VDD` (non tra `DCH` e `VDH`)
- [ ] Quarzo 32,768 kHz su `XL1`/`XL2` con i condensatori di carico
- [ ] Bulk 47 µF (`C96123`, 1206 10 V) vicino al VDDH del modulo
      *(il 47 µF 0805 da 6,3 V `C16780` perde molta più capacità per DC bias a 4,2 V)*
      *(la cella ha 1-2 Ω di resistenza interna; i picchi TX BLE la fanno affondare
      → brownout casuali durante la sync)*
- [ ] Resistore ISET calcolato per la corrente scelta
- [ ] TVS e protezione inversione sui pogo pin
      *(contatti esposti = ingresso preferito delle ESD; i pogo magnetici verranno
      attaccati al buio, storti, mille volte)*
- [ ] Pull-up su CS_IMU e CS_FLASH
- [ ] Pull-up su CHG_STAT
- [ ] Nessun segnale SPI su un pin "low frequency I/O only" (doc 01 §5.1)
- [ ] **4 pad SWD ben distanziati + punto di GND ampio**, accessibili prima del potting
- [ ] Modelli 3D verificati contro l'ingombro della capsula
- [ ] Anteprima JLC controllata pin 1 per pin 1
