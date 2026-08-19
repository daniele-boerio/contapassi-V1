# Contapassi ad alta precisione — contesto di progetto

Dispositivo indossabile **da caviglia** per conteggio passi, distanza (via ZUPT)
e parametri di andatura. BLE verso iPhone, HealthKit. Autonomia ~10 giorni.

Progettato in **KiCad 9.0**, prodotto da **JLCPCB** (PCB + PCBA).

## Documenti di riferimento

I documenti in `docs/` sono la fonte di verità. Leggili prima di proporre
modifiche architetturali:

- `docs/01-design.md` — architettura, decisioni e motivazioni, mappatura pin,
  budget energetico, vincoli meccanici e iOS
- `docs/02-bom-jlcpcb.md` — BOM con codici LCSC, checklist produzione
- `docs/03-firmware-taratura.md` — piano v1/v2, protocollo raccolta dati,
  macchina a stati

## Decisioni congelate — non riaprire senza motivo esplicito

Queste sono state prese dopo analisi. Se una proposta le contraddice, **dillo
apertamente invece di aggirarle silenziosamente**:

| Decisione | Motivo sintetico |
|---|---|
| Posizione: **caviglia** | Unica posizione dove lo ZUPT è possibile (il piede si ferma a ogni passo) |
| **E73-2G4M08S1C** (`C356849`) | Modulo nRF52840 certificato, VDDH esposto, in stock JLC |
| **LiPo diretta su VDDH** | Elimina l'LDO. Richiede L1 su `DCH` |
| **Dominio 3,0 V** (REGOUT0 via UICR) | Il default è 1,8 V e romperebbe la flash |
| **SPI condiviso**, non QSPI | Il collo di bottiglia è il BLE, non la flash. La flash si smonta in v2 |
| **v1 logger → v2 prodotto** | Algoritmo tarato su dati propri, sviluppato offline in Python |
| **ZUPT sull'MCU**, non su MLC | Debuggabile con breakpoint |
| **DFU over BLE dal giorno 1** | La capsula v2 è annegata in resina |

## Vincoli non negoziabili

- **Keepout antenna**: nessun rame su nessuno strato sotto l'antenna del modulo,
  nessuna via, mai la sacca LiPo (è alluminio)
- **Budget energetico ~161 µA medi**: qualunque proposta che aggiunga consumo
  continuo va quantificata, non liquidata come trascurabile
- **Orientamento ripetibile**: il sensore misura su assi fissi. Nessuna modifica
  meccanica che permetta alla capsula di ruotare nella guaina
- **Pad SWD accessibili** prima del potting

## Come lavorare su questo progetto

- Le quantità di consumo si esprimono in µA medi, non in "poco/tanto"
- Prima di aggiungere un componente, verificane la disponibilità su JLCPCB
- Segnala quando una modifica invalida un numero già scritto nei documenti
  (budget, quote, autonomia) invece di lasciare il documento incoerente
- Quando un dato manca, dillo. Non inventare valori di datasheet
