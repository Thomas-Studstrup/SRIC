# Special Risk Intelligence Center (SRIC)

## Projektoversigt
Dette projekt består af en Python-baseret backend (FastAPI) og en React-baseret frontend. Systemet håndterer chatbaseret interaktion, dokumentanalyse og brugeradministration med dynamiske roller.

---

## Flowbeskrivelse

### 1. Brugerlogin og -registrering
- Brugeren kan oprette en konto og logge ind via frontend.
- Backend håndterer autentificering og udsteder JWT tokens.
- Roller hentes dynamisk fra backend og vises i frontend ved registrering.

### 2. Chatfunktion
- Brugeren kan oprette nye chats og vælge eksisterende chats i sidebar.
- Hver chat indeholder en historik af beskeder mellem bruger og AI-assistent.
- Beskeder sendes til backend, som returnerer svar baseret på dokumenter og tidligere samtaler.

### 3. Dokumenthåndtering og RAG
- Backend indekserer og chunker dokumenter (PDF, DOCX, EML, XLSX).
- Ved spørgsmål bruger backend RAG (Retrieval-Augmented Generation) til at finde relevante dokumenter og generere svar.
- Kilden (filnavn) til svaret vises i frontend.

### 4. Brugerroller
- Roller som "user", "admin", "Client Service", "Business Management" administreres dynamisk.
- Roller styrer adgang til funktioner og data.

### 5. Styling og UI
- Frontend er stylet med Montserrat font og farver inspireret af specialrisk.dk.
- Chat-sidebar og chat-hovedområde er responsivt designet.

---

## Teknologier
- **Backend:** Python, FastAPI, SQLAlchemy, ChromaDB, LangChain
- **Frontend:** React (Vite), CSS
- **Database:** SQLite

---

## Start projektet
1. Installer Python dependencies:
   - Kør task "Install Python Dependencies" eller `pip install -r app/requirements.txt`
2. Initialiser databasen:
   - Kør task "Initialize Database"
3. Start backend:
   - Kør task "Start FastAPI Server"
4. Start frontend:
   - Kør task "Start Frontend Dev Server" eller `npm run dev` i frontend-mappen

---

## Kontakt
For spørgsmål, kontakt Thomas Studstrup Sejr.
