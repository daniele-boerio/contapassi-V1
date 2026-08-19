---
name: kicad-jlcpcb
description: Workflow KiCad 9 verso produzione JLCPCB per il progetto contapassi — scelta e verifica componenti sul catalogo, generazione simboli e footprint con easyeda2kicad, regole di layout, export BOM e CPL, correzione rotazioni, checklist pre-ordine. Usa questa skill ogni volta che si parla di KiCad, schematico, PCB, layout, routing, footprint, simboli, gerber, BOM, CPL, componenti, codici LCSC, JLCPCB, ordini di produzione o assemblaggio PCBA — anche quando la richiesta è generica tipo "aggiungi questo componente", "controlla il progetto" o "prepara i file per l'ordine".
---

# KiCad → JLCPCB

Workflow di produzione per il contapassi. Leggi `docs/02-bom-jlcpcb.md` per la
BOM corrente e i codici LCSC prima di qualunque modifica ai componenti.

## Regola d'ordine: il catalogo viene prima del progetto

Con JLCPCB non si sceglie il componente ideale e poi lo si cerca. Si parte dal
catalogo e si progetta con ciò che è disponibile. **Un componente non verificato
non entra nello schematico.**

Prima di aggiungere qualunque componente nuovo:

1. Cercalo su jlcpcb.com, Parts Library, tab **In stock Parts**
2. Annota: codice LCSC, scorta reale, quantità minima, prezzo
3. Diffida dei prezzi assurdi (es. $0,02 su un modulo BLE): indicano righe a
   catalogo mai realmente stoccate
4. Verifica se è **Basic** o **Extended** — gli Extended hanno un costo fisso di
   caricamento per tipo, che su 5 schede domina il totale

I passivi devono essere **Basic** e **0402**. Consolida i valori: se servono 47k,
51k e 56k in punti non critici, usane uno solo.

## Simboli e footprint

Per i componenti che esistono su LCSC, **non disegnare a mano**. Usa:

```bash
easyeda2kicad --full --lcsc_id=C356849
```

Genera simbolo, footprint e modello 3D. Verifica comunque il risultato contro il
datasheet del produttore — soprattutto il keepout d'antenna, che è l'unica zona
della scheda dove un errore non si recupera con un filo volante.

Le librerie custom vanno in `lib/` e aggiunte come **librerie di progetto**, non
globali, così il progetto resta autoconsistente.

## Parametri di produzione fissati

| Parametro | Valore |
|---|---|
| Dimensioni PCB | ~48 × 17 mm (tre zone: modulo / elettronica / cella — doc 01 §7) |
| Strati | 4 |
| Spessore | 0,8 mm |
| Passivi | 0402 |
| Separazione pannello | V-cut dove la geometria lo consente |
| Ispezione | X-ray obbligatoria (richiesta dal modulo E73) |

Il V-cut è preferito alle mouse bites perché queste lasciano sbavature sul bordo,
e la capsula deve incastrarsi con precisione nella guaina in silicone.

## Vincoli di layout specifici

**Keepout antenna** — sotto l'antenna del modulo E73: nessun rame su nessuno
strato, nessuna via, nessuna vite, e mai la sacca LiPo. Disegna il keepout dentro
il footprint stesso, su tutti gli strati: è l'unico modo di non dimenticarsene
durante il routing.

**Pad SWD** — quattro pad (SWDIO, SWCLK, GND, VDD) ben distanziati, più un punto
di GND ampio per la sonda dell'oscilloscopio. Non comprimerli in un angolo: si
finisce a tenere quattro punte ferme a mano su pad da 0,8 mm.

**Bulk 47 µF** vicino al VDDH del modulo. La cella ha 1-2 Ω di resistenza interna
e i picchi TX del BLE la fanno affondare: senza serbatoio locale si ottengono
brownout casuali durante la sync.

**Clearance dal bordo** — JLC ha una distanza minima dei componenti dal bordo
scheda. Il requisito "modulo che sporge oltre il bordo della batteria" è
meccanico dentro la capsula, non un componente a filo del bordo PCB.

## Export per l'ordine

Il plugin è **kicad-jlcpcb-tools** (Bouni). Assegna i codici LCSC ai footprint
già piazzati sul PCB, poi genera BOM e CPL.

Se non è installato:
`https://raw.githubusercontent.com/Bouni/bouni-kicad-repository/main/repository.json`
da aggiungere in Plugin and Content Manager → Gestisci → ➕.

## 🔴 Rotazioni nel CPL

È l'errore numero uno dei primi ordini PCBA. JLCPCB usa convenzioni di
orientamento che spesso non coincidono con quelle delle librerie KiCad, e il
risultato è un chip saldato ruotato di 90°.

Il plugin ha un **Rotation manager** con le correzioni note, ma non copre tutto.
**Controlla sempre l'anteprima grafica** che JLC mostra prima di confermare
l'ordine, componente per componente, guardando dove sta il pin 1.

## Checklist pre-ordine

Prima di generare i file di produzione, verifica:

- [ ] DRC e ERC puliti
- [ ] Keepout antenna verificato su tutti e 4 gli strati
- [ ] Induttore REG0 presente e collegato a `DCH`
- [ ] Quarzo 32,768 kHz su `XL1`/`XL2` con i condensatori di carico
- [ ] Bulk 47 µF vicino al VDDH
- [ ] Resistore ISET del MCP73831 calcolato per la corrente scelta
- [ ] TVS e protezione inversione sui pogo pin
- [ ] Pull-up su CS_IMU, CS_FLASH, CHG_STAT
- [ ] Pad SWD accessibili e distanziati
- [ ] Modelli 3D verificati contro l'ingombro della capsula
- [ ] Anteprima JLC controllata pin 1 per pin 1

## Differenza v1 / v2

**Stesso layout.** La v2 è la v1 senza la flash W25Q256 (marcata DNP nella BOM).
È il motivo per cui si è scelto SPI condiviso invece di QSPI: la flash si smonta
senza toccare nient'altro. Non introdurre modifiche che rendano i due layout
divergenti.
