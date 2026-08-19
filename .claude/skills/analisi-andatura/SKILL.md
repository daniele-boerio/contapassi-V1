---
name: analisi-andatura
description: Analisi offline in Python dei dati inerziali del contapassi — parsing dei dump binari, stance detection, ZUPT, stima della lunghezza di falcata, metriche di andatura, validazione contro il ground truth raccolto. Usa questa skill ogni volta che si scrive o discute codice Python, notebook, pandas o numpy su dati del sensore, o quando si parla di ZUPT, fasi di appoggio, heel strike, toe off, cadenza, falcata, autocorrelazione, taratura, soglie, o di come validare la precisione di passi e distanza — anche per richieste generiche tipo "analizza questi dati", "perché il conteggio sbaglia" o "tara l'algoritmo".
---

# Analisi offline dell'andatura

Leggi `docs/03-firmware-taratura.md` §3 e §4 per il protocollo di raccolta e la
pipeline completa.

## Perché l'analisi è offline

La v1 è un **logger puro**: registra il grezzo e non calcola nulla. Gli algoritmi
si sviluppano in Python sul PC, dove il ciclo di iterazione è di secondi e si
vedono i grafici. Solo quando sono congelati vengono portati in C sulla v2.

Due ragioni, entrambe importanti da tenere presenti:

- Un algoritmo scritto prima di avere i dati è tarato sull'andatura di
  qualcun altro
- Sul firmware ogni prova richiede compilazione, flash, camminata e scarico

**Non proporre di spostare la messa a punto sul firmware** finché i criteri di
uscita non sono soddisfatti.

## ZUPT — il principio

L'integrazione dell'accelerazione accumula errore quadraticamente: in ~10 s la
stima di posizione è inutilizzabile.

Ma a ogni passo il piede resta fermo a terra per ~0,3-0,5 s. In quella finestra la
velocità reale è nota e vale zero. Quindi: rileva la fase di appoggio, azzera
velocità e correggi la deriva del giroscopio, integra solo la fase di volo
successiva, ripeti. L'errore non si accumula mai oltre una singola falcata.

**Corollario da ricordare**: su tapis roulant a velocità costante lo ZUPT resta
valido. Un nastro a velocità costante è un riferimento inerziale, e nel suo
riferimento il piede è davvero fermo durante l'appoggio. I dati sono identici a
quelli di una camminata all'aperto. Solo i transitori di accelerazione del nastro
vanno scartati.

## Stance detection

Combina più condizioni contemporaneamente su una finestra scorrevole:

- modulo dell'accelerazione vicino a 1 g
- varianza dell'accelerazione sotto soglia
- modulo della velocità angolare sotto soglia

Nessuna delle tre da sola è affidabile. **Le soglie vanno tarate sui dati
dell'utente** — è esattamente il motivo per cui esiste la fase v1. Non usare
valori presi dalla letteratura come definitivi: usali come punto di partenza e
dichiara che vanno rifittati.

## Pipeline

1. Parsing del dump binario → DataFrame
2. Verifica qualità: campioni persi, **saturazioni a ±16 g**, gap temporali
3. Stance detection
4. ZUPT: azzeramento velocità + correzione deriva
5. Integrazione delle fasi di volo → lunghezza falcata
6. Pedometro: validare il conteggio contro i passi contati a mano
7. Metriche di andatura

Il passo 2 non è formalità: un file con saturazioni o gap va scartato, non
analizzato. Segnalalo invece di produrre numeri su dati corrotti.

## Metriche ottenibili da un sensore alla caviglia

- Cadenza (passi/min)
- **Variabilità del tempo di passo (CV)** — la più interessante clinicamente
- Tempo di appoggio / tempo di volo
- Durata del doppio supporto
- Regolarità via **autocorrelazione**: primo picco = regolarità del passo,
  secondo picco = regolarità della falcata

**Non ottenibili** da un solo dispositivo alla caviglia — se vengono richieste,
dillo invece di produrre un numero privo di significato:

- asimmetria destra/sinistra (serve una seconda unità sincronizzata)
- cinematica del tronco (serve la posizione lombare)
- classificazione posturale seduto/in piedi/sdraiato

## Ground truth

**Ogni registrazione deve avere una verità di riferimento annotata.** Un file
senza distanza reale e passi contati a mano non serve a nulla e va scartato.

Il log parallelo tenuto dall'utente contiene:
`data / ora inizio / tipo / distanza reale / passi contati / condizioni`

Il display del tapis roulant è calibrato sui giri del nastro e **non è un
riferimento affidabile** al livello di precisione cercato: per la verità assoluta
sulla distanza serve la pista.

## Criteri di uscita dalla fase v1

L'algoritmo si congela e si porta in C solo quando:

- [ ] Errore sul conteggio passi < 1% su tutte le andature testate
- [ ] Errore sulla distanza < 1% su percorsi noti
- [ ] Zero falsi positivi in auto, treno, da seduto
- [ ] Stabile su almeno 3 sessioni indipendenti **senza ritaratura**

L'ultimo criterio è quello che si è tentati di saltare, ed è quello che distingue
un algoritmo funzionante da uno sovradattato ai dati di taratura.
