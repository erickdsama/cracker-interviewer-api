# Backend Architecture

This project follows Clean Architecture principles to ensure modularity, testability, and maintainability.

## Directory Structure

- **`routers/`**: The entry points for the API. They handle HTTP requests and responses but contain NO business logic. They delegate to Services.
- **`services/`**: Contain the business logic of the application. They interact with Repositories for data access and other services (like AI, Scraper).
- **`repositories/`**: Handle all database interactions. They abstract the underlying database technology (SQLModel/SQLAlchemy) from the rest of the application.
- **`models.py`**: Defines the data entities and database schema.
- **`core/`**: (Planned) Configuration and common utilities.

## Key Components

### Repositories
- `BaseRepository`: Generic CRUD operations.
- `UserRepository`: User-specific data access.
- `SessionRepository`: Session-specific data access.

### Services
- `AuthService`: Handles authentication (Signup, Login, Google Auth).
- `SessionService`: Handles interview session management, including AI interaction and context gathering.
- `CodeService`: Handles code execution.
- `AIService`: Wrapper for Google Gemini API.
- `ScraperService`: Handles web scraping.
- `ParserService`: Handles resume parsing.

### Routers
- `auth.py`: Authentication endpoints.
- `sessions.py`: Session management endpoints.
- `context.py`: Context gathering endpoints.
- `code.py`: Code execution endpoints.
- `speech.py`: TTS endpoints.

## Dependency Injection
We use FastAPI's dependency injection system (`Depends`) to inject Repositories into Services, and Services into Routers. This allows for easy mocking during testing.
