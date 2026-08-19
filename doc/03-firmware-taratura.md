# Firmware e protocollo di taratura

**Principio guida:** prima si esplorano i dati in un notebook, poi si porta in
produzione. Scrivere l'algoritmo prima di avere i propri dati significa tararlo
sull'andatura di qualcun altro.

---

## 1. Le due versioni

| | **v1 — Logger** | **v2 — Prodotto** |
|---|---|---|
| Hardware | Con flash W25Q256JVEIQ | Flash non montata (DNP) |
| Firmware | Solo acquisizione e scrittura | Algoritmo in C a bordo |
| Algoritmi | Nessuno | ZUPT, pedometro, metriche |
| Elaborazione | Offline in Python sul PC | Real-time sul dispositivo |
| Autonomia | 2-4 giorni | ~10 giorni |
| Scopo | Raccogliere dataset personale | Uso quotidiano |

**Vantaggio del logger:** ciclo di iterazione in secondi anziché ore, con grafici.
Sul firmware ogni prova richiede compilazione, flash, camminata, scarico.

---

## 2. Firmware v1 (logger)

### Funzioni minime

- Configurazione IMU: **±16 g, 416 Hz, 6 assi**
  *(gli impatti tibiali in corsa superano i 16 g; 416 Hz serve per timbrare bene
  heel strike e toe off)*
- FIFO del sensore + interrupt watermark su INT1
- Buffer in RAM, **scrittura su flash a blocchi grossi**
- Pedometro hardware attivo in parallelo (per il gating)
- DFU over BLE
- Dump della flash via BLE quando sul caricatore

### ⚠️ Regola non negoziabile: scrittura a blocchi

La W25Q assorbe ~20 mA in scrittura. Chiamarla a ogni campione distrugge il budget
energetico. L'nRF52840 ha 256 kB di RAM: accumulare lì e svuotare a blocchi.

### ⚠️ Il logging deve essere gattato

Data rate: 6 assi × 16 bit × 416 Hz ≈ **5,0 kB/s → 18 MB/h**.

Su 32 MB → solo ~1,8 h di registrazione continua.

**Soluzione:** attivare il logging solo sui bout di cammino rilevati dal pedometro
hardware. Si scende a ~27 MB/giorno di dati effettivamente utili, e non si portano
a casa 15 ore di rumore da stare seduto.

### Formato dei dati

Includere sempre nel record:

- Timestamp (o contatore campioni + timestamp di blocco)
- 3 assi accelerometro
- 3 assi giroscopio
- Marker di inizio/fine sessione
- Temperatura (utile per valutare la deriva del giroscopio)

---

## 3. Protocollo di raccolta dati

### Sessione base — pista di atletica (400 m)

Registrare **5 andature**, ciascuna su distanza nota, contando i passi a mano:

| # | Andatura | Distanza | Note |
|---|---|---|---|
| 1 | Camminata molto lenta | 200 m | Il caso peggiore per i contapassi |
| 2 | Camminata normale | 400 m | — |
| 3 | Camminata veloce | 400 m | — |
| 4 | Corsa leggera | 400 m | — |
| 5 | Corsa sostenuta | 200 m | Verifica saturazione a ±16 g |

Per ognuna annotare: **distanza reale, passi contati a mano, tempo**.

### Sessione complementare — tapis roulant

Non sostituisce la pista, la integra. Il tapis dà **velocità impostabile,
ripetibile e controllata**; la pista dà la **verità assoluta sulla distanza**
(il display del tapis è calibrato sui giri del nastro, non è un riferimento
affidabile al livello di precisione cercato).

> **Perché i dati sono validi:** un nastro a velocità costante è un sistema di
> riferimento inerziale. Nel riferimento del nastro il piede è *davvero* fermo
> durante l'appoggio → **lo ZUPT resta valido** e le misure inerziali sono
> identiche a quelle di una camminata all'aperto alla stessa andatura.
> Nessuna gestione speciale nel firmware.

Sweep sistematico, 5 minuti per velocità:

| Velocità | Nota |
|---|---|
| 3 km/h | Camminata lenta |
| 4 km/h | Camminata normale |
| 5 km/h | Camminata veloce |
| 6 km/h | Transizione cammino/corsa |
| 8 km/h | Corsa leggera |
| 10 km/h | Corsa — verifica saturazione ±16 g |

Ripetere a pendenza 0% e 5% per valutare l'effetto sulla lunghezza di falcata.

**Limiti da tenere presenti:**

- **Transitori:** durante accelerazione/decelerazione del nastro il riferimento
  non è più inerziale → errore per qualche secondo. Scartare quelle finestre
- **Slittamento del nastro** sotto carico: piccolo errore, ma è del tapis
- **Pendenza:** misuri distanza percorsa, non dislivello (resti alla stessa quota).
  Corretto così — contare i piani richiederebbe il barometro, tolto passando
  alla caviglia

### Sessioni aggiuntive (casi difficili)

- Scale in salita e in discesa (conteggio gradini noto)
- Cammino in pendenza
- Cammino con carrello della spesa / passeggino
- Passi strascicati, cammino in casa a passi corti
- Alzarsi e fare 3-4 passi (i primi passi sono il caso peggiore)
- Falsi positivi: stare seduto muovendo la gamba, guidare, andare in bici
- Trasporto passivo: auto, treno, ascensore

### Regola di validazione

**Ogni registrazione deve avere una verità di riferimento annotata.** Un file senza
ground truth non serve a nulla e va scartato.

Tenere un log parallelo (foglio o note) con:
`data / ora inizio / tipo / distanza reale / passi contati / condizioni`

---

## 4. Sviluppo offline in Python

### Pipeline

1. **Parsing** del dump binario → DataFrame
2. **Verifica qualità**: campioni persi, saturazioni, gap temporali
3. **Stance detection** — rilevare le fasi di appoggio
4. **ZUPT** — azzeramento velocità + correzione deriva
5. **Integrazione** delle fasi di volo → lunghezza falcata
6. **Pedometro** — validare il conteggio contro i passi contati a mano
7. **Metriche di andatura** — cadenza, tempo appoggio/volo, variabilità

### Stance detection — approccio

Combinare più condizioni contemporaneamente su una finestra scorrevole:

- Modulo dell'accelerazione vicino a 1 g
- Varianza dell'accelerazione sotto soglia
- Modulo della velocità angolare sotto soglia

Nessuna delle tre da sola è affidabile. Le soglie vanno **tarate sui propri dati**,
ed è esattamente il motivo per cui esiste la fase v1.

### Metriche di andatura ottenibili

- **Cadenza** (passi/min)
- **Variabilità del tempo di passo** (CV) — la più interessante clinicamente
- **Tempo di appoggio / tempo di volo**
- **Durata del doppio supporto**
- **Regolarità** via autocorrelazione: primo picco = regolarità del passo,
  secondo picco = regolarità della falcata

> ❌ Non ottenibili da un solo dispositivo alla caviglia: asimmetria destra/sinistra,
> cinematica del tronco, postura.

### Criterio di uscita dalla fase v1

- [ ] Errore sul conteggio passi < 1% su tutte le andature testate
- [ ] Errore sulla distanza < 1% su percorsi noti
- [ ] Zero falsi positivi in auto/treno/seduto
- [ ] Algoritmo stabile su almeno 3 sessioni indipendenti senza ritaratura

---

## 5. Firmware v2 (prodotto)

### Struttura a eventi

```
MCU in sleep profondo
  │
  ├── INT1 (watermark FIFO) ──▶ svuota FIFO ──▶ elabora ──▶ sleep
  │
  ├── INT2 (movimento) ──────▶ attiva giroscopio, entra in modo cammino
  │
  ├── INT2 (doppio tap) ─────▶ azione utente (es. LED stato batteria)
  │
  ├── Timer 1 h ─────────────▶ advertising rapido, sync BLE, sleep
  │
  └── CHG_STAT ──────────────▶ modo carica: advertising rapido, dump disponibile
```

### Macchina a stati principale

| Stato | Accelerometro | Giroscopio | Consumo |
|---|---|---|---|
| **Idle** | LP + pedometro HW | spento | ~26 µA |
| **Cammino** | full rate | **attivo** (ZUPT) | ~alto |
| **Non deambulatoria** | LP | **spento** | basso |
| **Sync** | LP | spento | picchi TX |
| **Carica** | LP | spento | irrilevante |

Transizione Idle → Cammino: su rilevamento movimento sostenuto.
Transizione Cammino → Idle: dopo N secondi senza passi.
Transizione Cammino → Non deambulatoria: movimento presente ma **nessuna fase di
appoggio valida per N secondi consecutivi**.

**Il giroscopio è il costo dominante.** L'unica leva è entrare in stato Cammino
il più tardi possibile e uscirne il prima possibile — senza però perdere passi.

### 🔴 Stato "attività non deambulatoria"

**Il problema.** Lo ZUPT poggia su un'unica assunzione: che a ogni passo il piede
sia fermo. Nel nuoto, in bici e al remoergometro il piede **non si ferma mai**.
Con soglie permissive l'algoritmo integrerebbe accelerazioni senza mai correggere
la deriva → **distanze completamente inventate**. Non un errore piccolo: rumore.

Il conteggio passi invece è poco a rischio: il pedometro cerca l'impatto del
tallone, che in acqua non esiste.

**La firma inerziale del nuoto è ben distinguibile:**

| Grandezza | Cammino | Nuoto |
|---|---|---|
| Picchi di accelerazione | 10-16 g (tallonata) | 1-2 g |
| Fasi di quiete | Presenti a ogni passo | Assenti |
| Profilo | Impulsivo | Continuo, sinusoidale |
| Orientamento gravità | Stabile | Capovolto nel dorso |

**Comportamento in questo stato:**

- ZUPT sospeso
- Conteggio passi sospeso
- Giroscopio spento → **consumi meno che in stato Cammino**
- Periodo marcato nei dati come "attività non deambulatoria"

Costo implementativo: un ramo in più nella logica di transizione. Protegge anche
da bici e remoergometro, che hanno lo stesso identico problema.

> **Da aggiungere alle sessioni di raccolta (§3):** nuoto, bici, remoergometro.
> Servono per tarare le soglie di questa transizione.

### Dati mantenuti a bordo

- Passi per ora (buffer circolare, almeno 7 giorni)
- Distanza per ora
- Metriche di andatura aggregate per sessione
- Tensione batteria

Il buffer da 7 giorni serve a non perdere dati se l'iPhone non si connette.

### Servizio BLE

GATT custom. Caratteristiche minime:

| Caratteristica | Tipo | Contenuto |
|---|---|---|
| Sommario corrente | read/notify | Passi oggi, distanza, batteria |
| Storico | notify | Buffer orario, trasferito a blocchi |
| Stato dispositivo | read | Firmware, uptime, stato carica |
| Controllo | write | Reset contatori, sincronizza orologio |
| Dump grezzo | notify | Solo v1, solo sotto carica |

> ⚠️ **Sincronizzazione orologio a ogni connessione.** Se il modulo non ha il
> quarzo a 32,768 kHz, l'RC interno deriva sensibilmente. L'app deve riallineare
> l'orologio del dispositivo a ogni sync.

---

## 6. Ordine di implementazione consigliato

0. [ ] **Scrivere REGOUT0 = 3,0 V nell'UICR.** Va fatto al primissimo flash:
       il default dell'nRF52840 su VDDH è 1,8 V, e a quella tensione la flash
       W25Q256JVEIQ (2,7-3,6 V) non funziona
1. [ ] Bring-up: alimentazione, MCU vivo, LED lampeggia
2. [ ] SWD funzionante, **poi** DFU over BLE (prima del potting!)
3. [ ] Comunicazione SPI con IMU — leggere il registro WHO_AM_I
3b. [ ] Verificare che il quarzo Y1 a 32,768 kHz oscilli e sia selezionato come
        sorgente LFCLK (non l'RC interno)
4. [ ] Comunicazione SPI con flash — leggere il JEDEC ID
5. [ ] Misura del consumo reale in sleep → confronto col budget
6. [ ] FIFO + interrupt watermark
7. [ ] Scrittura su flash a blocchi
8. [ ] Dump via BLE
9. [ ] **→ Fase di raccolta dati (§3)**
10. [ ] **→ Sviluppo offline (§4)**
11. [ ] Porting dell'algoritmo congelato in C
12. [ ] App iOS + HealthKit
13. [ ] v2: rimozione flash, nuovo layout, potting

> Il punto 5 è un gate: se il consumo reale è molto sopra il budget, va capito
> **prima** di investire nell'algoritmo.
