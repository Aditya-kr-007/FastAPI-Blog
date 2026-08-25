# FastAPI-Blog

Blog API built with FastAPI — a simple example demonstrating creating, reading, updating and deleting blog posts with JWT-based protection on write operations.

## Features
- Create, read (single + paginated list with search), update, and delete blog posts
- JWT token generation and verification for protected endpoints
- SQLAlchemy models and session management
- PostgreSQL-ready (DATABASE_URL in code)

## Stack
- Language: Python
- Framework: FastAPI
- Database: PostgreSQL (SQLAlchemy ORM)
- Auth: python-jose (JWT)
- Notable libraries: fastapi, sqlalchemy, python-jose, psycopg2-binary (for Postgres)

## Project structure
```
.gitattributes       # git attributes
.gitignore
auth.py              # JWT creation & verification (OAuth2PasswordBearer)
database.py          # SQLAlchemy engine, SessionLocal, Base; contains DATABASE_URL
main.py              # FastAPI app, routing, DB dependency, CRUD endpoints
models.py            # SQLAlchemy Blog model
schemas.py           # Pydantic request/response schemas
README.md
```

How it fits together:
- main.py wires FastAPI routes and DB dependency (SessionLocal). models.py defines the Blog table and schemas.py defines input/output shapes. auth.py creates/verifies JWT tokens used by protected endpoints. database.py holds DB connection configuration and Base used by SQLAlchemy.

## Quick start (local)
1. Clone and enter repository
   ```
   git clone https://github.com/Aditya-kr-007/FastAPI-Blog.git
   cd FastAPI-Blog
   ```

2. Create a virtual environment and install dependencies
   ```
   python -m venv .venv
   source .venv/bin/activate     # or .venv\Scripts\activate on Windows
   pip install fastapi uvicorn sqlalchemy python-jose[cryptography] psycopg2-binary python-dotenv
   ```

3. Configure environment (recommended)  
   The repository currently hardcodes DATABASE_URL and SECRET_KEY. Create a `.env` file and update code to read from env vars, or edit database.py and auth.py for quick testing:

   Example .env:
   ```
   DATABASE_URL=postgresql://postgres:password@localhost/blogdb
   SECRET_KEY=replace_with_a_strong_secret
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

4. Run the app
   ```
   uvicorn main:app --reload
   ```
   Open docs at: http://127.0.0.1:8000/docs

## API usage examples

- Obtain token (note: current /login returns a token for a fixed user)
  ```
  curl -X POST http://127.0.0.1:8000/login
  ```
  Response:
  ```
  { "access_token": "<JWT>", "token_type": "bearer" }
  ```

- Create a blog (protected)
  ```
  curl -X POST http://127.0.0.1:8000/blogs \
    -H "Authorization: Bearer <JWT>" \
    -H "Content-Type: application/json" \
    -d '{"title":"Hello","content":"First post"}'
  ```

- List blogs (paginated + search)
  ```
  curl "http://127.0.0.1:8000/blogs?page=1&limit=5&search=Hello"
  ```

- Get single blog
  ```
  curl http://127.0.0.1:8000/blogs/1
  ```

- Update blog (protected)
  ```
  curl -X PUT http://127.0.0.1:8000/blogs/1 \
    -H "Authorization: Bearer <JWT>" \
    -H "Content-Type: application/json" \
    -d '{"title":"Updated","content":"..."}'
  ```

- Delete blog (protected)
  ```
  curl -X DELETE http://127.0.0.1:8000/blogs/1 \
    -H "Authorization: Bearer <JWT>"
  ```

## Notes & recommended improvements
- Security: SECRET_KEY and DB credentials are hard-coded. Move config into environment variables and use Pydantic settings.
- Auth: /login currently returns a token for a static user. Add user/password handling, password hashing (bcrypt), and proper scopes/roles.
- Migrations: Add Alembic for schema migrations instead of create_all in code.
- Tests: Add pytest test suite for endpoints and DB layer.
- Packaging: Add requirements.txt and optionally Dockerfile + docker-compose for easier local setup.
- Input validation: Add stricter Pydantic validation and consider response models on list endpoints.

## Contributing
Contributions welcome — open an issue or submit a PR. Please add tests for new behavior.

## License
No license specified. Add an appropriate LICENSE file if you plan to publish this repo.
