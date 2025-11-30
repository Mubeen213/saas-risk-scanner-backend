#  Engineering & Architecture Guidelines

This document defines the coding, design, and architectural principles for the **saas-risk-scanner-backend**.
All contributors must follow these standards to maintain quality, consistency, and long-term maintainability.

---

#  **1. Project Architecture Overview**

This project follows a **layered, clean architecture**.
Each folder has a strict purpose and **must not** take responsibilities outside its domain.

```
app/
├── api/              # Controllers (FastAPI routers)
├── constants/        # Enums & static constants
├── core/             # Settings, security, logging
├── dtos/             # Internal data transfer objects (Create/Update only)
├── models/           # Database entity models (Pydantic)
├── repositories/     # Database access layer
├── schemas/          # Pydantic request/response models (API contracts)
├── services/         # Business logic layer
└── utils/            # Shared utilities
```

---

#  **2. Layer Responsibilities**

### **`api/` – Controller Layer**

* Contains FastAPI routes only.
* Performs request validation using **schemas/**.
* Delegates all logic to **services/**.
* Must not contain business rules, SQL, or external API logic.

---

### **`services/` – Business Logic Layer**

* Implements all core workflow/business logic.
* Pure Python — no FastAPI, no HTTP objects, no DB engine access.
* Orchestrates multiple repositories.
* Applies domain rules (risk scoring, policy parsing, etc.).
* Must follow **Single Responsibility Principle (SRP)**.

---

### **`repositories/` – Data Access Layer**

* Contains all database CRUD logic using raw SQL with asyncpg.
* Expose clear interfaces (e.g., `UserRepository`, `OrganizationRepository`).
* Must **not** include business logic or request validation.
* Must return **models/** entities (database representations).
* Accept **dtos/** for create/update operations.

---

### **`schemas/` – Pydantic Schemas (API Layer)**

* Used only for **external API input/output**.
* Never imported by repository or model layers.
* Defines strict types for controllers (Request/Response shapes).

---

### **`dtos/` – Internal Data Transfer Objects**

* Contains only **Create** and **Update** DTOs.
* Used for passing data from services to repositories.
* Lightweight Pydantic models for internal communication.
* Do NOT put database entity representations here (use `models/` instead).

---

### **`models/` – Database Entity Models**

* Pydantic models representing database table rows (1:1 mapping).
* Returned by repositories after database operations.
* Used throughout services and internal layers.
* Keep models simple — no business logic, just data representation.

---

### **`constants/` – Project Constants**

* Enums such as `RiskLevel`, `AppStatus`, `ScanType`.
* Must remain stable and domain-specific.

---

### **`core/` – Project Core**

* Application settings (`pydantic-settings`)
* Logging configuration
* Security utilities
* Database session lifecycle
* Environment configuration

Avoid business rules here.

---

### **`utils/` – Utility Functions**

* Small, pure helper functions.
* Must be stateless and reusable.
* Not domain-specific.

---


### **Dependency Injection (DI) & Wiring**

We use **Strict Constructor Injection** to decouple layers and manage database lifecycles. All wiring logic must reside in `dependencies.py`.

#### **The Dependency Chain**

The application follows a strict hierarchical injection flow:

1.  **DB Connection** is injected into → **Repositories**.
2.  **Repositories** are injected into → **Services**.
3.  **Services** are injected into → **Controllers**.

#### **Implementation Rules**

**1. The Wiring Layer (`dependencies.py`)**

  * This is the **only** place where classes are instantiated.
  * Must define `Depends()` chains to assemble the object graph.
  * Must handle the `async with` database session lifecycle here.

<!-- end list -->

```python
# dependencies.py pattern
def get_user_repo(conn = Depends(get_db_connection)) -> UserRepository:
    return UserRepository(conn)

def get_user_service(repo: UserRepository = Depends(get_user_repo)) -> UserService:
    return UserService(user_repository=repo)
```

**2. Services (`services/`)**

  * Must define dependencies in `__init__`.
  * **Must NOT** use `Depends()` (Services are framework-agnostic).
  * **Must NOT** instantiate repositories manually (e.g., `self.repo = UserRepo()`).


```python
# Correct Service Pattern
class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
```

**3. Controllers (`api/`)**

  * Must never import or instantiate Repositories directly.
  * Must inject the fully assembled Service using `Depends`.
  * Must never handle database connections (`async with` blocks) directly.

```python
# Correct Controller Pattern
@router.post("/users")
async def create_user(
    service: UserService = Depends(get_user_service) # Fully wired
):
    return await service.create(...)
```

**4. Repositories (`repositories/`)**

  * Must accept the database connection/session in `__init__`.
  * Must not create their own connections.

-----

### API Response structures:

#### We must use this consistent api response format for all the endpoints

* Success response structure:
```json
{
  "meta": {
    "request_id": "01F9XYZ...abc",
    "timestamp": "2025-11-20T11:00:00Z"
  },
  "data": {
    "items": [
      /* array of results */
    ],
    "pagination": {
      "page": 2,
      "page_size": 25,
      "total_items": 245,
      "total_pages": 10,
    }
  },
  "error": null
}
```

* Error response structure:
```json
{
  "meta": {
    "request_id": "01F9XYZ...abc",
    "timestamp": "2025-11-20T11:00:00Z"
  },
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed for the request.",
    "target": "request_body",
    "details": [
      {
        "code": "REQUIRED_FIELD",
        "field": "email",
        "message": "Email is required."
      },
      {
        "code": "INVALID_FORMAT",
        "field": "date_of_birth",
        "message": "Date must be in YYYY-MM-DD format."
      }
    ]
  }
}
```

#  **3. Design Principles**

###  **Single Responsibility Principle**

Each file/class/function must have **one reason to change**.
Small, focused units over large multi-purpose functions.

---

###  **Strict Separation of Concerns**

* Controllers don’t run business logic
* Services don’t execute SQL
* Repositories don’t know API schemas
* Models don’t know HTTP or business rules

---

###  **Reusable, Composable Functions**

* Prefer small helper functions over large procedural blocks.
* Avoid duplicated logic — move shared behavior into **utils/** or **services/**.

### OOPS principles
* Use classes to encapsulate related behavior and data.
* Use inheritance and polymorphism where appropriate to promote code reuse and flexibility.
---

###  **Type Safety Everywhere**

* Every function must include type hints.
* Use:

  * `typing` (Optional, Literal, List, Dict, etc.)
  * Pydantic schemas
  * Dataclasses for internal DTOs
  * Do not promote usage of Dict[str, Any] or untyped structures.

No untyped functions.
No `Any` unless absolutely unavoidable.

```python
    async def exchange_code_for_tokens(
        self, provider: OAuthProvider, config: OAuthConfig, code: str
    ) -> OAuthResult:
        tokens = await provider.exchange_code(config, code)
        if tokens is None:
            return OAuthResult(
                success=False,
                error_code=AuthErrorCode.OAUTH_TOKEN_EXCHANGE_FAILED,
            )
        return OAuthResult(success=True, data=tokens)
```
Caller must use it like this: 
```python
    oauth_result: OAuthResult = await self.oauth_service.exchange_code_for_tokens(
        provider, config, code
    )
```        

---

#  **4. Implementation Rules**

### **Controllers (`api/`) must:**

* Validate input with `schemas/`
* Call service methods only
* Return schema-based responses
* Avoid business logic entirely

---

### **Services (`services/`) must:**

* Be framework-agnostic
* Contain reusable business logic
* Accept & return **models/** entities or **dtos/** for mutations
* Never import FastAPI, Request, Response, HTTPException
* Perform complex workflows in small helper methods

---

### **Repositories (`repositories/`) must:**

* Interact with DB connection only (asyncpg)
* Implement CRUD operations
* Return **models/** entities (never raw DB rows or dicts)
* Accept **dtos/** for create/update operations
* Keep queries small and readable

---

### **Models (`models/`) must:**

* Represent database entities as Pydantic models
* Have 1:1 mapping with database tables
* Not contain business logic
* Use `ConfigDict(from_attributes=True)` for ORM-style mapping

---

### **Schemas (`schemas/`) must:**

* Not leak into services or repositories
* Focus on API validation and serialization
* Define Request/Response shapes for controllers

---

### **DTOs (`dtos/`) must:**

* Only contain Create and Update data classes
* Be used for service-to-repository communication
* Not duplicate database entity representations (use models/ for that)

---

#  **5. Code Quality Standards**

### **General Rules**

* No long functions (> 40–50 lines).
* No large files — split by domain.
* No commented-out code in main branches.
* No global mutable state.
* Use meaningful names.
* Do not provide any doc strings, the function and variable names should be self explanatory.

---

### **Logging**

* Use structured logging defined in `core/`.
* Services must log key decision points.
* Avoid printing or ad-hoc logs.

---

### **Error Handling**

* Raise custom exceptions from **services/**.
* Controllers convert them into proper HTTP responses.

---

#  **6. What You Must Not Do**

* Do not place business logic in controllers
* Do not run SQL inside services
* Do not import API schemas inside repositories
* Do not return ORM models directly to clients
* Do not duplicate logic across layers
* Do not mix concerns between folders
* Do not build “god” classes or “mega” functions
* Do not use emojis in logs
* Do not write any tests for the code
* Do not write any summary documents for the code
* Do not write helper funcitons's helper function
* Do not write the funcitons/services which are not needed

---

# Final Note

Follow this guide to ensure the backend remains:

* Clean
* Easy to maintain
* Modular
* Extendable
* Production-ready

This structure is final — **all new code must follow it.**
