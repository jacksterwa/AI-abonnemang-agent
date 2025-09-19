# AI Abonnemang Agent

Ett prototypprojekt för en AI-assistent som håller koll på återkommande abonnemang. Tjänsten läser in transaktioner och mejl, identifierar återkommande kostnader och ger användaren tydliga val för att förnya eller säga upp abonnemang.

## Funktioner
- Registrera banktransaktioner och identifiera månatliga prenumerationer.
- Importera e-postnotiser för att justera förnyelsedatum och flagga prisökningar.
- Håll koll på aktiva och avslutade abonnemang samt sparade pengar.
- API-endpoint för dashboard med översikt över kommande förnyelser.

## Kom igång
1. Installera beroenden:
   ```bash
   pip install -e .[development]
   ```
2. Starta API-servern:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Kör tester:
   ```bash
   pytest
   ```

## API-översikt
- `POST /transactions` – registrerar en transaktion. När ett återkommande mönster hittas returneras abonnemanget.
- `POST /emails` – importerar ett mejl och klassificerar dess innehåll.
- `GET /subscriptions` – listar alla kända abonnemang.
- `POST /subscriptions/{id}/decision` – avsluta eller förnya ett abonnemang.
- `GET /dashboard` – hämtar sammanfattning av kostnader, sparade pengar och kommande förnyelser.

## Nästa steg
- Koppla mot riktiga PSD2-/Open Banking-API:er.
- Lägga till användarhantering och uthållig datalagring (PostgreSQL).
- Förbättrad NLP för att analysera mejl och aviseringar.
- Automatiserade uppsägningar via leverantörsspecifika integrationer.
