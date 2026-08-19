---
name: nrf52840-firmware
description: Sviluppo firmware nRF52840 per il contapassi da caviglia — architettura a eventi, macchina a stati, gestione IMU LSM6DSV16X via SPI e FIFO, ZUPT, disciplina del consumo, BLE con vincoli iOS, DFU, bring-up. Usa questa skill ogni volta che si scrive, modifica o discute codice firmware, driver, interrupt, sleep, BLE, GATT, HealthKit, DFU, nRF Connect SDK, Zephyr, o quando si parla di consumo, µA, batteria, sensori, FIFO, o della macchina a stati del dispositivo — anche per richieste generiche tipo "scrivi il driver", "aggiungi questa funzione" o "perché consuma troppo".
---

# Firmware nRF52840 — contapassi

Leggi `docs/03-firmware-taratura.md` per la macchina a stati completa e il piano
v1/v2, e `docs/01-design.md` §6 per il budget energetico.

## Il principio che governa tutto

**Il dispositivo è spento quasi sempre.** Ogni decisione discende da qui.

L'MCU è sveglio meno dell'1% del tempo. L'LSM6DSV16X non è un sensore passivo da
interrogare: ha pedometro in hardware e FIFO, quindi accumula da solo e sveglia
l'MCU con un interrupt.

**Architettura a eventi, mai polling loop.** Se una proposta introduce un ciclo
periodico di lettura, è quasi certamente sbagliata: cerca l'interrupt equivalente.

## 🔴 Primo flash: REGOUT0

Al primissimo flash su chip vergine, **scrivi REGOUT0 = 3,0 V nell'UICR**.

Il default dell'nRF52840 alimentato da VDDH è 1,8 V, e a quella tensione la
flash W25Q256JVEIQ (2,7-3,6 V) non risponde. Se lo dimentichi, passi ore a
cercare un problema di saldatura che non esiste.

Il chip arriva vergine da JLC, quindi il primo flash è **sempre via SWD**:
nessun bootloader può installarsi da solo.

## Macchina a stati

| Stato | Accelerometro | Giroscopio | Note |
|---|---|---|---|
| **Idle** | LP + pedometro HW | spento | ~26 µA, stato di default |
| **Cammino** | full rate | **attivo** (ZUPT) | costo dominante |
| **Non deambulatoria** | LP | spento | nuoto, bici, remoergometro |
| **Sync** | LP | spento | picchi TX |
| **Carica** | LP | spento | consumo irrilevante |

Il giroscopio è il costo dominante: ~123 µA sul medio giornaliero. L'unica leva è
entrare in stato Cammino il più tardi possibile e uscirne il prima possibile,
**senza però perdere passi**. Non barattare precisione per autonomia senza dirlo.

**Stato "non deambulatoria"**: ZUPT poggia sull'assunzione che il piede si fermi a
ogni passo. In acqua o in bici non si ferma mai, e con soglie permissive
l'algoritmo integrerebbe accelerazioni senza mai correggere la deriva, producendo
distanze inventate. Transizione: movimento presente ma nessuna fase di appoggio
valida per N secondi.

## Configurazione IMU

- **±16 g** — gli impatti tibiali in corsa superano i 16 g
- **416 Hz** — serve per timbrare bene heel strike e toe off
- **FIFO + watermark su INT1**, eventi asincroni su INT2

Due linee di interrupt e non una: con una sola servirebbe leggere i registri di
stato a ogni interrupt per capire la causa, con una transazione SPI in più ogni
volta e l'MCU svegliato a vuoto.

Il **doppio tap** rilevato in hardware dall'IMU è l'unico "pulsante": la capsula
è sigillata e non ha aperture.

## Scrittura su flash (solo v1)

La W25Q assorbe ~20 mA in scrittura. **Accumula in RAM e svuota a blocchi
grossi** — l'nRF52840 ha 256 kB. Chiamarla a ogni campione distrugge il budget.

Il logging va **gattato sui bout di cammino** rilevati dal pedometro hardware:
a 416 Hz su 6 assi sono ~18 MB/h, e 32 MB coprono meno di due ore continue.

## BLE — vincoli iOS

Questi sono vincoli di piattaforma, non preferenze:

- **MTU**: iOS accetta fino a 185 byte di payload. Usa **notifiche, non
  indicazioni** — le indicazioni aspettano l'ack e dimezzano il throughput
- **Connection interval**: minimo 15 ms e multiplo di 15. Parametri non conformi
  vengono rifiutati e si resta sui default
- **Background**: serve `bluetooth-central` con State Preservation and
  Restoration. In background iOS scansiona **solo per UUID di servizio
  espliciti**, mai wildcard
- **Advertising**: 2 s di default (pochi µA). Finestra veloce solo su evento

**Due canali separati**: sync sommario orario (poche centinaia di byte) e dump
grezzo (decine di MB, solo v1, solo sotto carica). Ottimizzarli insieme li
peggiora entrambi.

**HealthKit**: anche l'iPhone scrive i propri passi, e Salute non somma le
sorgenti sovrapposte — sceglie in base alla priorità impostata dall'utente. Il
conflitto va gestito esplicitamente.

**Sincronizzazione orologio a ogni connessione** se il quarzo Y1 non fosse
montato: l'RC interno deriva.

## DFU over BLE

Non è opzionale e non va rimandato: la capsula v2 è annegata in resina, e dopo il
potting non esiste accesso via cavo. Il bootloader sicuro Nordic va in piedi
prima di qualunque altra funzionalità.

## Ordine di bring-up

Segui questo ordine — ogni passo valida il precedente:

0. REGOUT0 = 3,0 V nell'UICR
1. Alimentazione, MCU vivo, LED lampeggia
2. SWD funzionante, poi DFU over BLE
3. SPI con IMU — leggere WHO_AM_I
4. Quarzo Y1 oscilla ed è selezionato come LFCLK
5. SPI con flash — leggere il JEDEC ID
6. **Misura del consumo reale in sleep** ← gate: se sfora il budget, va capito
   prima di investire nell'algoritmo
7. FIFO + watermark, scrittura a blocchi, dump BLE

## Disciplina sul consumo

Ogni proposta che aggiunge consumo continuo va **quantificata in µA medi**, non
liquidata come trascurabile. Il budget totale è ~161 µA per ~10 giorni: 20 µA in
più sono un giorno perso.

I valori di datasheet sono tipici a 25 °C e 3,0 V. Vanno verificati sul silicio
reale al passo 6.
