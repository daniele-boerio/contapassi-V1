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
| U2 | **LSM6DSV16XTR** (ST, IMU 6 assi) | *da annotare* | LGA-14 | ✅ | — |
| U3 | **W25Q256JVEIQ** (Winbond, 32 MB) | `C97522` | WSON-8-EP (6×8) | 16763 ✅ | €3,76 |
| U4 | **MCP73831T-2ATI/OT** (Microchip) | `C14879` | SOT-23-5 | 1957 ✅ | €0,96 |
| L1 | **Induttore REG0** ~10 µH | *da scegliere* | 0603 | — | — |
| Y1 | **Quarzo 32,768 kHz** | *da scegliere* | 3215 | — | — |
| — | Passivi **0402**, TVS, LED | — | — | Basic | — |

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

**U2 — LSM6DSV16XTR.** "TR" = Tape & Reel, è solo il confezionamento.
Chip identico a LSM6DSV16X. Annota il codice LCSC quando lo confermi.

**U3 — W25Q256JVEIQ.** Variante 2,7-3,6 V, compatibile con il dominio a 3,0 V
scelto in §3. Solo v1.

> ⚠️ Se un giorno passassi al dominio a 1,8 V, questa parte **non funziona**.
> La variante corretta sarebbe `C2940048` (W25Q256JWEIQ, 1,7-1,95 V).

**U4 — MCP73831T-2ATI/OT.** Il "2" indica i 4,20 V corretti per LiPo.

- [ ] Aprire il PDF e verificare nella tabella di ordinazione che l'uscita STAT
      di questa variante sia leggibile da GPIO
- [ ] Alternativa se non lo è: `C424093` (`-2ACI/OT`, 2874 pz)
- [ ] **Corrente di carica:** l'MCP73831 sotto ~50 mA esce dall'intervallo di
      buona precisione. Su cella da 55 mAh, 50 mA ≈ 0,9C. **Verificare sul
      datasheet della cella** che accetti 1C — se dichiara max 0,5C serve
      un altro chip

**L1 — induttore REG0.** Senza, REG0 resta in modalità LDO: scendere da 4,0 V a
3,0 V dissiperebbe il **25% su tutto il consumo della scheda**. Un componente
0603 vale il 25% di autonomia. Valore da confermare sul datasheet Nordic
nRF52840, sezione alimentazione ad alta tensione.

**Y1 — quarzo 32,768 kHz.** Non strettamente obbligatorio, ma consigliato: senza,
l'RC interno richiede ricalibrazioni periodiche e **allarga le finestre di
ricezione BLE**, cioè consuma di più proprio dove stiamo ottimizzando. Costa
~2 µA e dà un orologio che non deriva tra una sync e l'altra.
Servono anche i due condensatori di carico.

### Componenti NON assemblati da JLC (montaggio manuale)

- Cella LiPo
- Pogo pin magnetici (dorati)

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
| Dimensioni | **~32 × 18 mm** | Cresciuto per accogliere il modulo 18×13 |
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
2. [ ] Annotare il codice LCSC dell'LSM6DSV16XTR
3. [ ] Scaricare il datasheet Ebyte E73-2G4M08S1C
4. [ ] **Rifare la mappatura pin** (doc 01 §5) sul pinout Ebyte
5. [ ] Scegliere valore induttore L1 e quarzo Y1 + condensatori di carico
6. [ ] Verificare il rate di carica ammesso dalla cella
7. [ ] Generare simbolo e footprint con easyeda2kicad
8. [ ] Schematico
9. [ ] Layout
10. [ ] Export BOM + CPL con il plugin
11. [ ] Controllo anteprima JLC pin per pin

---

## 9. Checklist pre-ordine

- [ ] DRC pulito
- [ ] ERC pulito
- [ ] Keepout antenna verificato su tutti e 4 gli strati (nessun rame, nessuna via)
- [ ] Induttore REG0 presente e collegato a `DCH`
- [ ] Quarzo 32,768 kHz su `XL1`/`XL2` con i condensatori di carico
- [ ] Bulk 47 µF presente vicino al VDDH del modulo
      *(la cella ha 1-2 Ω di resistenza interna; i picchi TX BLE la fanno affondare
      → brownout casuali durante la sync)*
- [ ] Resistore ISET calcolato per la corrente scelta
- [ ] TVS e protezione inversione sui pogo pin
      *(contatti esposti = ingresso preferito delle ESD; i pogo magnetici verranno
      attaccati al buio, storti, mille volte)*
- [ ] Pull-up su CS_IMU e CS_FLASH
- [ ] Pull-up su CHG_STAT
- [ ] **4 pad SWD ben distanziati + punto di GND ampio**, accessibili prima del potting
- [ ] Modelli 3D verificati contro l'ingombro della capsula
- [ ] Anteprima JLC controllata pin 1 per pin 1
