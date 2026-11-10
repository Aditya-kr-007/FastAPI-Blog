# The MarginRoom — Blog Application 

A responsive JavaScript frontend connected to the FastAPI blog API. FastAPI serves the UI and API together, so only one server is needed. No Node installation or frontend build is required.

## Features

- Responsive journal with illustrated story cards and a full-story reader
- Title search, newest-first ordering, and pagination
- Registration and sign-in using usernames and passwords, with expiring JWT sessions
- Each writer manages their own stories; the configured owner can manage all stories
- Create, edit, and delete stories; deletion requires confirmation
- Word counts, estimated reading times, loading states, error messages, and empty states
- Accessible forms, keyboard-friendly dialogs, and reduced-motion support
- SQLite for local development; PostgreSQL supported through DATABASE_URL

## Run locally (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and choose your own `ADMIN_PASSWORD` and random `SECRET_KEY`. Generate a secret with:

```powershell
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Start the app:

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open **http://127.0.0.1:8000**. Click **Create account**, or **Sign in, then Create an account** on mobile. Choose a username (3-30 letters, numbers, or underscores) and a password (8-128 characters), then confirm your password. Registration signs you in automatically. Click **Write a story** to publish. Read one of your own stories to access Edit and Delete.

The owner can still sign in with the credentials from `.env` and manage all posts, including posts created before registration was added. New users cannot register the owner username. Usernames are stored in lowercase and sign-in is case-insensitive.

Posts and accounts are stored in `blog.db` by default and survive server restarts. On startup, the app adds `users` and `blog_authors` tables without altering or deleting the existing `blogs` table. Existing posts retain their content and remain managed by the owner.

On macOS/Linux, use `.venv/bin/python` in place of `.venv\Scripts\python.exe`.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Local `blog.db` SQLite file | SQLAlchemy database URL |
| `ADMIN_USERNAME` | `admin` | Editor username |
| `ADMIN_PASSWORD` | Unset | Enables the owner account; registration works without it |
| `SECRET_KEY` | Random per process | Set a stable random key to preserve sessions across restarts |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT lifetime |

To keep using an existing PostgreSQL database, set `DATABASE_URL=postgresql://postgres:your-password@localhost/blogdb` in `.env` before starting. Existing blog tables are compatible; no posts are copied or deleted. URL-encode special characters in database credentials. Without this setting, the app uses a separate SQLite database.

The frontend sends requests to the same origin; CORS configuration is unnecessary. Google Fonts enhances typography when available, with local font fallbacks. Story content is rendered as plain text, preserving paragraphs and avoiding executable HTML.

## Project structure

```text
frontend/
  index.html         Page, reader, registration, sign-in, and editor dialogs
  styles.css         Responsive visual design
  app.js             API requests, session handling, and UI interactions
main.py              FastAPI routes and frontend serving
config.py            Environment configuration
models.py            Blog, user, and post ownership database models
schemas.py           Request validation and response schemas
auth.py              Password hashing and JWT creation/verification
database.py          SQLAlchemy engine and sessions
tests/test_app.py    Isolated API integration tests
.env.example         Configuration template
requirements.txt     Runtime dependencies
requirements-dev.txt Test dependencies
```

## API

Interactive docs: **http://127.0.0.1:8000/docs**.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | JavaScript frontend |
| GET | `/health` | API health response |
| POST | `/register` | Create an account with JSON `username` and `password`; returns a session |
| GET | `/me` | Current authenticated user |
| POST | `/login` | Sign in with form-encoded `username` and `password` |
| GET | `/blogs?page=1&limit=6&search=` | List and search posts |
| GET | `/blogs/{id}` | Read a post |
| POST | `/blogs` | Create a post (Bearer token required) |
| PUT | `/blogs/{id}` | Update your post (owner can manage all; Bearer token required) |
| DELETE | `/blogs/{id}` | Delete your post (owner can manage all; Bearer token required) |

POST and PUT accept JSON with `title` and `content`. Titles must contain 1–200 characters; content must contain 1–100,000 characters after trimming whitespace. Page must be at least 1 and limit must be between 1 and 100.

Compatibility changes: `/` now serves the frontend (the old API status is at `/health`), `/login` now requires real credentials instead of issuing a token to anyone, and post lists are newest first.

## Checks

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
node --check frontend/app.js
```

Tests use an isolated in-memory database and test credentials, without modifying your blog data.

Registered passwords use a random per-user salt and PBKDF2-HMAC-SHA256 with 600,000 iterations, following [OWASP password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). Password hashes are never returned by the API.

For public deployment, configure HTTPS and login/registration rate limiting, manage secrets through your host, and use database migrations for future schema changes. Email verification and password recovery are not included.
