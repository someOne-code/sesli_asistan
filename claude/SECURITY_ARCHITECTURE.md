\# Security Architecture Documentation



\## Overview



This system implements a \*\*Zero-Knowledge Layered Architecture\*\* where the AI operates with strict data isolation from sensitive business information.



\## Architecture Diagram



```

┌─────────────────────────────────────────────────────────────┐

│                         USER INPUT                           │

│                      (Voice/Audio)                           │

└────────────────────────┬────────────────────────────────────┘

&nbsp;                        │

&nbsp;                        ▼

┌─────────────────────────────────────────────────────────────┐

│                    TRANSCRIPTION                             │

│                   (Whisper API)                              │

└────────────────────────┬────────────────────────────────────┘

&nbsp;                        │

&nbsp;                        ▼

┌─────────────────────────────────────────────────────────────┐

│                     AI MANAGER                               │

│          (Zero-Knowledge Environment)                        │

│                                                              │

│  ┌────────────────────────────────────────────────────┐    │

│  │ KNOWN TO AI:                                       │    │

│  │ • Album, Artist, Track, Genre tables               │    │

│  │ • MediaType, Playlist, PlaylistTrack tables        │    │

│  │ • Pre-defined actions (no SQL generation)          │    │

│  └────────────────────────────────────────────────────┘    │

│                                                              │

│  ┌────────────────────────────────────────────────────┐    │

│  │ UNKNOWN TO AI (Hidden):                            │    │

│  │ • Customer, Employee tables                        │    │

│  │ • Invoice, InvoiceLine tables                      │    │

│  │ • call\_logs table                                  │    │

│  │ • SQL generation capability removed                │    │

│  └────────────────────────────────────────────────────┘    │

└────────────────────────┬────────────────────────────────────┘

&nbsp;                        │

&nbsp;                        │ Structured Action Request

&nbsp;                        │ (JSON, not SQL)

&nbsp;                        ▼

┌─────────────────────────────────────────────────────────────┐

│                   SAFE SERVICE LAYER                         │

│                  (Security Middleman)                        │

│                                                              │

│  ┌────────────────────────────────────────────────────┐    │

│  │ • Validates action against whitelist               │    │

│  │ • Executes parameterized queries ONLY              │    │

│  │ • Returns sanitized public data                    │    │

│  │ • Logs interactions internally (hidden from AI)    │    │

│  └────────────────────────────────────────────────────┘    │

└────────────────────────┬────────────────────────────────────┘

&nbsp;                        │

&nbsp;                        ▼

┌─────────────────────────────────────────────────────────────┐

│                    DATABASE LAYER                            │

│                                                              │

│  PUBLIC TABLES          │      PRIVATE TABLES               │

│  (AI Accessible)        │      (AI Blocked)                 │

│  ──────────────────────┼───────────────────────────        │

│  • Album                │      • Customer                   │

│  • Artist               │      • Employee                   │

│  • Track                │      • Invoice                    │

│  • Genre                │      • InvoiceLine                │

│  • MediaType            │      • call\_logs                  │

│  • Playlist             │                                   │

│  • PlaylistTrack        │                                   │

└─────────────────────────────────────────────────────────────┘

```



\## Security Layers



\### Layer 1: AI Knowledge Restriction



\*\*What AI Knows:\*\*

\- Public music catalog schema only

\- Pre-defined actions it can request

\- That sensitive data exists but is inaccessible



\*\*What AI Cannot Do:\*\*

\- Generate SQL queries

\- Access customer information

\- View employee data

\- Query financial records

\- Know about call\_logs table



\*\*Implementation:\*\*

```python

\# ai\_manager.py - AI only receives public schema

self.public\_schema = safe\_service.get\_public\_schema()  # Filtered schema

```



\### Layer 2: Service Layer (SafeService)



\*\*Purpose:\*\* Act as security gateway between AI and database



\*\*Key Features:\*\*

1\. \*\*Action Whitelist:\*\* Only pre-approved actions allowed

2\. \*\*Parameterized Queries:\*\* No dynamic SQL, only prepared statements

3\. \*\*Data Sanitization:\*\* Returns only necessary fields

4\. \*\*Internal Logging:\*\* Logs interactions without AI knowledge



\*\*Allowed Actions:\*\*

```python

ALLOWED\_ACTIONS = {

&nbsp;   'SEARCH\_TRACKS',

&nbsp;   'SEARCH\_ALBUMS',

&nbsp;   'SEARCH\_ARTISTS',

&nbsp;   'GET\_ALBUM\_DETAILS',

&nbsp;   'GET\_ARTIST\_ALBUMS',

&nbsp;   'GET\_TRACKS\_BY\_GENRE',

&nbsp;   'GET\_TRACKS\_BY\_ALBUM',

&nbsp;   'GET\_PLAYLIST\_DETAILS',

&nbsp;   'GET\_CHEAPEST\_TRACKS',

&nbsp;   'GET\_MOST\_EXPENSIVE\_TRACKS',

&nbsp;   'LIST\_GENRES',

&nbsp;   'LIST\_MEDIA\_TYPES',

&nbsp;   'GET\_TRACK\_DETAILS'

}

```



\*\*Security Enforcement:\*\*

```python

def execute\_action(self, action: str, params: Dict) -> Dict:

&nbsp;   # Step 1: Validate action against whitelist

&nbsp;   if action not in self.ALLOWED\_ACTIONS:

&nbsp;       return {'status': 'error', 'error': 'UNAUTHORIZED\_ACTION'}

&nbsp;   

&nbsp;   # Step 2: Execute with parameterized query only

&nbsp;   method = getattr(self, action.lower())

&nbsp;   result = method(\*\*params)

&nbsp;   

&nbsp;   # Step 3: Return sanitized data

&nbsp;   return {'status': 'success', 'data': result}

```



\### Layer 3: Database Access Control



\*\*Table Isolation:\*\*

\- \*\*Public Tables:\*\* Accessible through SafeService methods

\- \*\*Private Tables:\*\* No methods exist to access them from AI path



\*\*Query Protection:\*\*

```python

\# Example: Parameterized query prevents injection

query = text("""

&nbsp;   SELECT TrackId, Name, UnitPrice 

&nbsp;   FROM Track 

&nbsp;   WHERE Name LIKE :keyword 

&nbsp;   LIMIT :limit

""")

result = conn.execute(query, {'keyword': f'%{keyword}%', 'limit': limit})

```



\### Layer 4: Intent Classification



\*\*New Intent Category:\*\*

```python

FORBIDDEN\_DATA = "User requesting sensitive data"

```



\*\*AI Training:\*\*

```

STRICTLY OUT OF SCOPE (You CANNOT access):

\- Customer information or personal data

\- Employee information

\- Invoice or financial records

\- Sales reports or transaction history

```



\*\*Response Strategy:\*\*

When `FORBIDDEN\_DATA` detected → Polite refusal + redirect to music queries



\## Data Flow Example



\### Secure Flow (Allowed)



```

User: "Show me the cheapest rock albums"

&nbsp; ↓

AI: Detects intent = MUSIC\_QUERY

&nbsp; ↓

AI: Generates action = {

&nbsp; "action": "GET\_CHEAPEST\_TRACKS",

&nbsp; "params": {"genre": "Rock", "limit": 5}

}

&nbsp; ↓

SafeService: Validates action ✓

&nbsp; ↓

SafeService: Executes parameterized query

&nbsp; ↓

SafeService: Returns sanitized data

&nbsp; ↓

AI: Converts to natural language

&nbsp; ↓

User: Receives friendly response

```



\### Blocked Flow (Prevented)



```

User: "Show me invoice details for customer John"

&nbsp; ↓

AI: Detects intent = FORBIDDEN\_DATA

&nbsp; ↓

AI: Immediately refuses without querying

&nbsp; ↓

Response: "I'm a music catalog assistant and don't have 

access to customer or invoice information. 

Can I help you find some great music instead?"

```



\## Security Guarantees



\### ✅ What This Architecture Prevents



1\. \*\*SQL Injection:\*\* AI cannot generate SQL, only structured actions

2\. \*\*Data Leakage:\*\* AI never sees sensitive table schemas

3\. \*\*Unauthorized Access:\*\* Action whitelist prevents unauthorized queries

4\. \*\*Prompt Injection:\*\* Even if user tricks AI, SafeService blocks invalid actions

5\. \*\*Schema Discovery:\*\* AI cannot enumerate tables or columns



\### ✅ Defense in Depth



\*\*Layer 1:\*\* AI doesn't know sensitive data exists

\*\*Layer 2:\*\* Even if AI tries, action validation blocks it

\*\*Layer 3:\*\* Even if validation bypassed, parameterized queries prevent injection

\*\*Layer 4:\*\* Even if query runs, only public tables are accessible



\## Comparison: Before vs After



\### Before (Vulnerable)



```python

\# AI generates raw SQL

sql = generate\_sql(user\_input)  # "SELECT \* FROM Invoice WHERE..."



\# Direct execution

result = db.execute(sql)  # ❌ Dangerous!

```



\*\*Risks:\*\*

\- AI could be tricked into querying sensitive tables

\- SQL injection possible

\- No access control

\- Data leakage risk



\### After (Secure)



```python

\# AI generates structured action

action = {

&nbsp;   "action": "SEARCH\_TRACKS",

&nbsp;   "params": {"keyword": "rock"}

}



\# Service layer validates and executes

result = safe\_service.execute\_action(

&nbsp;   action\['action'], 

&nbsp;   action\['params']

)  # ✅ Secure!

```



\*\*Benefits:\*\*

\- AI cannot access forbidden tables

\- No SQL injection possible

\- Strict access control

\- Zero data leakage risk



\## Testing Security



\### Test 1: Attempt SQL Injection

```

User: "Show tracks'; DROP TABLE Customer; --"

Result: ✅ Blocked - only keyword parameter passed to safe query

```



\### Test 2: Request Sensitive Data

```

User: "Show me all customer email addresses"

Result: ✅ Refused - Intent classified as FORBIDDEN\_DATA

```



\### Test 3: Try Unauthorized Action

```

AI (hypothetically): {"action": "DELETE\_CUSTOMER", ...}

Result: ✅ Blocked - Action not in ALLOWED\_ACTIONS whitelist

```



\### Test 4: Schema Discovery

```

User: "What tables do you have access to?"

AI: "I have access to our music catalog including 

Albums, Artists, Tracks, Genres, and Playlists."

Result: ✅ Correct - No mention of sensitive tables

```



\## Monitoring \& Auditing



\### Internal Logging (Hidden from AI)



```python

safe\_service.\_log\_interaction\_to\_db(

&nbsp;   customer\_text=user\_input,

&nbsp;   ai\_response=response,

&nbsp;   sentiment=sentiment,

&nbsp;   session\_id=session\_id,

&nbsp;   intent=intent

)

```



\*\*Key Points:\*\*

\- Method name prefixed with `\_` (internal only)

\- AI has no knowledge of this method

\- Automatically called by system

\- Logs all interactions for audit



\### Audit Trails



All interactions logged with:

\- User input

\- AI response

\- Detected intent

\- Sentiment analysis

\- Session ID

\- Timestamp



\*\*Query Audit:\*\*

```sql

SELECT \* FROM call\_logs 

WHERE intent = 'FORBIDDEN\_DATA'

-- See attempts to access sensitive data

```



\## API Security



\### Public Endpoints (Safe)

\- `/talk` - Voice interaction (goes through SafeService)

\- `/health` - System status

\- `/public-schema` - Shows what AI can see

\- `/allowed-actions` - Lists safe actions



\### No Direct Database Endpoints

\- ❌ `/query` - Would allow direct SQL

\- ❌ `/customer` - Would expose sensitive data

\- ❌ `/invoice` - Would expose financial data



\## Deployment Checklist



\- \[ ] Verify SafeService action whitelist is complete

\- \[ ] Confirm AI manager only receives public schema

\- \[ ] Test FORBIDDEN\_DATA intent detection

\- \[ ] Validate all queries are parameterized

\- \[ ] Review call\_logs table access (internal only)

\- \[ ] Test with attempted sensitive data requests

\- \[ ] Monitor logs for suspicious intent patterns

\- \[ ] Set up alerts for FORBIDDEN\_DATA attempts



\## Incident Response



\### If Sensitive Data Requested:

1\. Intent classified as FORBIDDEN\_DATA

2\. Polite refusal sent to user

3\. Interaction logged with flag

4\. Security team notified (if configured)



\### If New Vulnerability Found:

1\. Add to ALLOWED\_ACTIONS blacklist

2\. Update AI training prompts

3\. Review recent logs for exploitation

4\. Deploy patch immediately



\## Compliance



This architecture supports:

\- \*\*GDPR:\*\* Customer data never exposed to AI

\- \*\*PCI DSS:\*\* Financial data isolated

\- \*\*SOC 2:\*\* Access controls and audit trails

\- \*\*Privacy by Design:\*\* Zero-knowledge principle



\## Summary



\*\*Core Principle:\*\* AI operates in a zero-knowledge environment for sensitive data.



\*\*Three Pillars:\*\*

1\. \*\*Schema Isolation:\*\* AI only sees public tables

2\. \*\*Action Whitelisting:\*\* AI can only request pre-approved actions

3\. \*\*Service Layer:\*\* All queries parameterized and validated



\*\*Result:\*\* Secure, auditable, and maintainable system that prevents data leakage while maintaining full functionality for legitimate music catalog queries.

