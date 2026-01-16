# Architecture Documentation

## Overview

This integration platform implements a **multi-integration sync system** using Domain-Driven Design (DDD), Hexagonal Architecture, and Temporal for orchestration.

The system is designed to be:
- **Reliable**: Automatic retries and failure recovery
- **Resumable**: Cursor-based sync state tracking
- **Idempotent**: UPSERT-based operations prevent duplicates
- **Multi-tenant**: Supports multiple connected accounts
- **Multi-integration**: Easily extensible to new vendors
- **Fault-tolerant**: Graceful degradation and error handling

## Local Setup

1. **Environment Setup:**
   Copy `.env.example` to `.env` and configure your QuickBooks credentials:
   ```bash
   cp .env.example .env
   ```

2. **Start the environment:**
   ```bash
   docker compose up --build 
   ```

3. **Database Access:**
   Connect to the database using pgAdmin or a similar tool. Credentials can be found in `docker-compose.yml`.

4. **Connect Integration:**
   Make a `POST` request to `http://localhost:8000/auth/quickbooks/connect` with the following JSON body:
   ```json
   {
       "authorization_code": "your_sandbox_auth_cod",
       "realm_id": "your_sanbox_real_id"
   }
   ```
5. **Monitoring on temporal-ui**
    By visiting `http://localhost:8080/namespaces/default/workflows`



## Architectural Patterns

### 1. Domain-Driven Design (DDD)

The domain layer contains pure business logic with **zero infrastructure dependencies**.

**Aggregates:**
- `IntegrationAccount` - Root aggregate representing a connected external account
- `SyncCursor` - Entity tracking incremental sync progress
- `RawExternalObject` - Entity storing unmodified vendor payloads

**Invariants:**
- `(integration_type, external_account_id)` must be unique
- Cursors are monotonic (never move backward)
- Cursors advance only after successful persistence

**Domain Services:**
- `CredentialPolicy` - Manages credential expiration and refresh rules

### 2. Hexagonal Architecture (Ports & Adapters)

The system follows strict layer separation:

```
┌─────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                 │
│              OAuth, Integration Management              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Temporal Layer                         │
│              Workflows, Activities, Worker              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              Application Layer (Use Cases)              │
│         SyncExternalObjects, RunIntegrationSync         │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│          Domain Layer (Pure Business Logic)             │
│      Entities, Value Objects, Repository Ports          │
└─────────────────────────────────────────────────────────┘
                            ↑
┌─────────────────────────────────────────────────────────┐
│            Infrastructure Layer (Adapters)              │
│    Database Repos, QuickBooks ACL, OAuth Client         │
└─────────────────────────────────────────────────────────┘
```

**Ports (Interfaces):**
- `IntegrationAccountRepository`
- `SyncCursorRepository`
- `RawExternalObjectRepository`

**Adapters (Implementations):**
- `SQLAlchemyIntegrationAccountRepository`
- `SQLAlchemySyncCursorRepository`
- `SQLAlchemyRawExternalObjectRepository`

### 3. Anti-Corruption Layer (ACL)

Each integration is isolated in its own ACL to prevent vendor-specific concepts from leaking into the core domain.

**QuickBooks ACL:**
- `QuickBooksOAuthClient` - OAuth 2.0 flow
- `QuickBooksAPIClient` - API queries and pagination
- `QuickBooksCustomer`, `QuickBooksInvoice` - DTOs (never leave ACL)

**Responsibilities:**
- Hide vendor API specifics
- Normalize pagination
- Handle vendor quirks
- Return plain Python objects

### 4. Temporal Saga Pattern

Temporal orchestrates long-running sync workflows with automatic retries and recovery.

**Workflow:**
- One workflow instance per `IntegrationAccount`
- Runs indefinitely with `continue_as_new()`
- No business logic, only orchestration

**Activities:**
- `run_integration_sync` - Execute sync for all object types
- Idempotent and retriable
- Retry policies with exponential backoff

**Benefits:**
- Automatic failure recovery
- Workflow history and debugging
- Durable execution across restarts

### 5. Repository Pattern

All data access goes through repository interfaces defined in the domain layer.

**UPSERT-based persistence:**
```python
# PostgreSQL INSERT ... ON CONFLICT
stmt = insert(Model).values(...).on_conflict_do_update(
    constraint='uq_composite_key',
    set_={...}
)
```

**Benefits:**
- Idempotent operations
- No duplicate data
- Safe for retries

## Data Flow

### OAuth Flow

The system currently uses a manual OAuth connection flow to simplify development and testing.

```
QuickBooks OAuth Playground / Developer Portal
  ↓
Obtain Authorization Code & Realm ID
  ↓
User → POST /auth/quickbooks/connect
{
  "authorization_code": "...",
  "realm_id": "..."
}
  ↓
System exchanges code for tokens
  ↓
Save IntegrationAccount
  ↓
Start Temporal Workflow
```

### Sync Flow

```
Temporal Workflow (every 5 minutes)
  ↓
Check if credentials need refresh
  ↓
For each object type (Customer, Invoice):
  ↓
  Get current cursor position
  ↓
  Query QuickBooks API (WHERE LastUpdatedTime > cursor)
  ↓
  Convert to RawExternalObject entities
  ↓
  UPSERT to database
  ↓
  Advance cursor to latest timestamp
  ↓
Continue as new workflow
```

## Failure Recovery

### Scenario 1: Database Failure Mid-Sync

**What happens:**
1. Activity fails during object persistence
2. Temporal retries activity with exponential backoff
3. Cursor hasn't advanced (still at old position)
4. Retry fetches same objects from QuickBooks
5. UPSERT updates existing records (no duplicates)
6. Cursor advances after successful persistence

**Result:** No data loss, no duplicates

### Scenario 2: Token Expiration

**What happens:**
1. Activity attempts sync with expired token
2. QuickBooks API returns 401 Unauthorized
3. Activity fails and retries
4. Before next sync, workflow checks credentials
5. Credentials refreshed automatically
6. Next activity uses new token

**Result:** Automatic recovery, sync continues

### Scenario 3: Worker Restart

**What happens:**
1. Temporal worker crashes mid-workflow
2. Workflow state persisted in Temporal server
3. New worker starts
4. Temporal resumes workflow from last checkpoint
5. Activity re-executed (idempotent)

**Result:** Seamless recovery

## Extensibility

### Adding a New Integration (e.g., Xero)

**1. Add enum value:**
```python
class IntegrationType(str, Enum):
    QUICKBOOKS = "quickbooks"
    XERO = "xero"  # New
```

**2. Create ACL:**
```
infrastructure/integrations/xero/
├── __init__.py
├── oauth.py       # XeroOAuthClient
├── client.py      # XeroAPIClient
└── models.py      # XeroCustomer, XeroInvoice
```

**3. Update application service:**
```python
class RunIntegrationSyncService:
    XERO_OBJECT_TYPES = [ObjectType.CUSTOMER, ObjectType.INVOICE]
    
    async def _sync_object_type(self, account, object_type):
        if account.integration_type == IntegrationType.XERO:
            api_client = XeroAPIClient(...)
            # ...
```

## Monitoring

### Temporal UI
- View workflow execution history
- See activity retries and failures
- Debug workflow state

### Health Endpoints
- `/health` - Basic health check
- `/health/db` - Database connectivity
- `/health/temporal` - Temporal connectivity

### Sync Status API
- Get request on `/integrations` - List all integration accounts
- Get request on `/integrations/{account_uuid}` - View integration account details
- Get request on `/integrations/{account_uuid}/status` - View cursor positions
- See last sync time, records synced, errors


