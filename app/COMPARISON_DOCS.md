# Sammenligning Funktionalitet

## Oversigt
Det udviklede sammenligning system kan håndtere forskellige typer af sammenligninger primært rettet mod forsikringsområdet.

## Funktioner

### 1. Betingelser Sammenligning (`terms_comparison`)
- **Formål**: Sammenlign betingelser mellem forskellige forsikringsselskaber eller produkter
- **Eksempel**: "Sammenlign betingelser mellem Tryg og Topdanmark for rejseforsikring"
- **Output**: Struktureret sammenligning med hovedforskelle, fordele/ulemper og anbefalinger

### 2. Spørgeskema Vurdering (`questionnaire_assessment`)
- **Formål**: Vurder om spørgeskemaer lever op til krav og hvilke betingelser de passer til
- **Eksempel**: "Vurder om dette spørgeskema lever op til kravene for rejseforsikring"
- **Output**: Hvilke krav opfyldes, mangler, passende produkter og forbedringer

### 3. Police Sammenligning (`policy_comparison`)
- **Formål**: Sammenlign forsikringspolicer
- **Eksempel**: "Sammenlign forskellige forsikringspolicer for rejse"
- **Output**: Dækning, præmier, selvrisiko, fordele/ulemper og målgruppe

### 4. Selskab Sammenligning (`company_comparison`)
- **Formål**: Sammenlign forsikringsselskaber
- **Eksempel**: "Sammenlign Tryg og Topdanmark som forsikringsselskaber"
- **Output**: Produktportefølje, priser, kundeservice, finansiel styrke og omdømme

### 5. Generel Sammenligning (`general_comparison`)
- **Formål**: Håndter andre typer sammenligninger
- **Eksempel**: "Hvad er forskellen på rejseafbestillingsforsikring?"
- **Output**: Struktureret sammenligning med forskelle, ligheder og anbefalinger

## Automatisk Klassificering

Systemet bruger avanceret klassificering til at identificere sammenligning requests:

### Sammenligning Nøgleord:
- sammenlign, forskel, difference, compare, versus, vs
- kontra, mod, bedre, værre, bedst, værst
- fordel, ulempe, forskellig, ligner, ligheder
- alternativer, valg, hvilken er bedst, anbefal

### Analyse Nøgleord:
- analys, vurder, evaluate, assess, undersøg
- gennemgang, analysis, evaluation, rapport

### Mønster Detektion:
- "mellem X og Y"
- "X vs Y" 
- "X kontra Y"
- Flere selskaber nævnt (automatisk sammenligning)

## API Brug

### Endpoint: `/ask`
**Method**: POST
**Content-Type**: application/json

**Request Body**:
```json
{
  "message": "Sammenlign betingelser mellem Tryg og Topdanmark"
}
```

**Response Format**:
```json
{
  "type": "compare",
  "subtype": "terms_comparison",
  "question": "Sammenlign betingelser mellem Tryg og Topdanmark",
  "result": "Detaljeret sammenligning...",
  "sources_count": 5,
  "context_preview": "Kontekst preview..."
}
```

## Test Eksempler

1. **Betingelser**: "Sammenlign betingelser mellem Tryg og Topdanmark for rejseforsikring"
2. **Generel**: "Hvad er forskellen på rejseafbestillingsforsikring?"
3. **Selskaber**: "Sammenlign Tryg og Topdanmark som forsikringsselskaber"
4. **Spørgeskema**: "Vurder om dette spørgeskema lever op til kravene"
5. **Policer**: "Sammenlign forskellige forsikringspolicer for rejse"

## Debugging

Systemet inkluderer omfattende logging:
- 🔶 compare_service: Sammenligning service logs
- 🟤 compare_controller: Controller logs
- 🟣 ask_classifier: Klassificering logs

## Fejlhåndtering

- Graceful degradation hvis ingen relevante dokumenter findes
- Type-safe håndtering af vector store resultater
- Detaljeret fejlrapportering med context information

## Udvidelsesmuligheder

Systemet er designet til let udvidelse:
- Nye sammenligning typer kan tilføjes som nye private funktioner
- Klassificering kan udvides med nye nøgleord eller mønstre
- Prompt engineering kan tilpasses til specifikke use cases
