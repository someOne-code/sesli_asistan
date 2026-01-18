# Melody System Architecture: Universal Retrieval

## High-Level Overview
Refactoring from tightly-coupled intent logic to a loose-coupled **Retrieval-Augmented Generation (RAG)** architecture.

```mermaid
graph TD
    User((User)) -->|"Voice Input"| AI_Service[AI Adapter]
    AI_Service -->|"Extract Query"| Service[Assistant Service]
    Service -->|"search_products()"| Repo[Infrastructure Layer]
    
    subgraph "Infrastructure (Universal Retrieval)"
        Repo -->|"SQL JOINs"| DB[(hedef.db)]
        DB -->|"Raw Rows"| Repo
        Repo -->|"Map to Domain"| Domain[Product Objects]
    end
    
    Domain -->|"List[Product]"| Service
    Service -->|"Context Injection"| AI_Service
    AI_Service -->|"Natural Language Response"| User
```

## Key Components

### 1. Domain Object (`Product`)
The universal language of the system.
- **Independence:** Does not know about SQL or Tables.
- **Fields:** `id`, `name`, `price`, `description` (Rich text).

### 2. Universal Repository (`SqliteRepository`)
The only component that knows SQL.
- **Single Entry Point:** `search_products(query: str, limit: int = 5)`.
- **Logic:**
  - Performs complex JOINs (Track + Album + Artist + Genre).
  - Filters validation (Security).
  - **Token Safety:** Enforces HARD LIMIT of 5 items.
  - **Mapping:** Maps DB result to Product.

### 3. Melody Logic (Service + AI)
- **Service:** radically simplified. "Get data, Pass to AI".
- **AI (Melody):**
  - **Input:** User Query + List of Products.
  - **Decision:** "User asked for price? I see price in Product object. I will say it."
  - **Constraint:** NO ORDERS.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User (Voice)
    participant S as AssistantService
    participant R as Repository
    participant M as Melody (AI)

    U->>S: "Iron Maiden albümleri ne kadar?"
    S->>R: search_products("Iron Maiden")
    R->>R: SQL: JOIN Track, Album, Artist...
    R-->>S: [Product(Name="Fear of the Dark", Price=9.99...)...]
    S->>M: Generate Response(Context=Products)
    M->>M: Check Policy: INFO ONLY
    M-->>U: "Fear of the Dark albümümüz var, fiyatı 9.99 dolar."
```

## Core Engineering Principles (The Manifesto)
This project is built on strict adherence to the following pillars. Any future changes MUST comply with these rules:

### 1. Agile & Test-First (TDD)
- **Test First:** We write failing tests *before* writing implementation code.
- **Red-Green-Refactor:** Make it fail, make it work, then make it clean.
- **Verification:** Security, Business, and Integration tests run automatically. We trust the test suite more than manual checks.

### 2. Lazy Coupling (Gevşek Bağlılık)
- **Principle:** High-level modules (AI, Service) should NOT depend on low-level implementation details (SQL, Tables).
- **Implementation:** 
    - The `Service` layer never asks "Get me Track table". 
    - It only asks "Search for 'Metallica'". 
    - The `Repository` is a black box that returns generic `Product` objects.
- **Benefit:** Replacing SQLite with MongoDB requires **zero** changes to the Service or AI layer.

### 3. Layered Architecture
- **Strict Separation:**
    - `Domain` (Product): Knows nothing about DB or AI.
    - `Infrastructure` (Repository, Groq): Knows external systems (SQL, API).
    - `Service` (AssistantService): Orchestrates logic, depends on Interfaces.
    - `Presentation` (FastAPI): Just handles HTTP/WebSockets.
- **Rule:** A lower layer never depends on a higher layer.
