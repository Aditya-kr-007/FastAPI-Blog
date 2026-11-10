"""API integration checks use an isolated, in-memory database."""
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timedelta, timezone

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ADMIN_USERNAME"] = "test-editor"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["SECRET_KEY"] = "test-secret-used-only-in-the-isolated-test-suite"

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from config import SECRET_KEY
from database import Base


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def get_test_db():
        with sessions() as session:
            yield session

    main.app.dependency_overrides[main.get_db] = get_test_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
    engine.dispose()


def authorization(client):
    response = client.post("/login", data={"username": "test-editor", "password": "test-password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_frontend_and_assets(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "The Margin" in response.text
    for path, content_type in [("styles.css", "text/css"), ("app.js", "javascript")]:
        response = client.get(f"/static/{path}")
        assert response.status_code == 200
        assert content_type in response.headers["content-type"]
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200


def test_frontend_script_elements_exist(client):
    class Elements(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = []

        def handle_starttag(self, tag, attrs):
            self.ids.extend(value for name, value in attrs if name == "id")

    parser = Elements()
    parser.feed(client.get("/").text)
    script = (Path(__file__).resolve().parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
    references = set(re.findall(r"\$\('([^']+)'\)", script))
    assert not (references - set(parser.ids))
    assert len(parser.ids) == len(set(parser.ids))


def test_invalid_login(client):
    assert client.post("/login").status_code == 422
    assert client.post("/login", data={"username": "test-editor", "password": "wrong"}).status_code == 401


def test_registration_works_without_admin_password(client, monkeypatch):
    monkeypatch.setattr(main, "ADMIN_PASSWORD", "")
    assert client.post("/login", data={"username": "admin", "password": "anything"}).status_code == 401
    assert client.post("/register", json={"username": "new_writer", "password": "a-long-password"}).status_code == 201


def test_full_post_lifecycle(client):
    headers = authorization(client)
    response = client.post("/blogs", headers=headers, json={"title": "  Hello journal  ", "content": "First paragraph.\n\nAnother thought."})
    assert response.status_code == 200
    post = response.json()
    assert post["title"] == "Hello journal"
    assert client.get(f"/blogs/{post['id']}").json() == post
    response = client.put(f"/blogs/{post['id']}", headers=headers, json={"title": "Updated", "content": "Edited story"})
    assert response.status_code == 200
    assert client.get(f"/blogs/{post['id']}").json()["content"] == "Edited story"
    assert client.delete(f"/blogs/{post['id']}", headers=headers).status_code == 200
    assert client.get(f"/blogs/{post['id']}").status_code == 404
    assert client.get("/blogs").json()["total"] == 0


@pytest.mark.parametrize("method,path", [("post", "/blogs"), ("put", "/blogs/1"), ("delete", "/blogs/1")])
def test_writes_require_authentication(client, method, path):
    kwargs = {"json": {"title": "Story", "content": "Body"}} if method != "delete" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


def test_expired_or_forged_token(client):
    expired = jwt.encode({"sub": "test-editor", "kind": "admin", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, SECRET_KEY, algorithm="HS256")
    for token in [expired, "forged-token"]:
        response = client.post("/blogs", headers={"Authorization": f"Bearer {token}"}, json={"title": "Story", "content": "Body"})
        assert response.status_code == 401


def test_search_and_pagination(client):
    headers = authorization(client)
    for title in ["First note", "Second note", "Other story"]:
        assert client.post("/blogs", headers=headers, json={"title": title, "content": "Story content"}).status_code == 200
    page = client.get("/blogs?limit=2").json()
    assert page["total"] == 3
    assert [post["title"] for post in page["data"]] == ["Other story", "Second note"]
    assert len(client.get("/blogs?page=2&limit=2").json()["data"]) == 1
    assert client.get("/blogs?search=NOTE").json()["total"] == 2
    assert client.get("/blogs?search=missing").json()["data"] == []


def test_validation_and_missing_posts(client):
    headers = authorization(client)
    for title, content in [("   ", "Content"), ("Title", "  "), ("a" * 201, "Content")]:
        assert client.post("/blogs", headers=headers, json={"title": title, "content": content}).status_code == 422
    for query in ["page=0", "limit=0", "limit=101"]:
        assert client.get(f"/blogs?{query}").status_code == 422
    assert client.put("/blogs/999", headers=headers, json={"title": "Title", "content": "Content"}).status_code == 404
    assert client.delete("/blogs/999", headers=headers).status_code == 404


def register_user(client, username="writer_one"):
    response = client.post("/register", json={"username": username, "password": "a-secure-password"})
    assert response.status_code == 201
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]


def test_registration_login_and_profile(client):
    headers, user = register_user(client, "Writer_One")
    assert user["username"] == "writer_one"
    assert user["is_admin"] is False
    assert set(user) == {"id", "username", "is_admin"}
    assert client.get("/me", headers=headers).json() == user
    response = client.post("/login", data={"username": "WRITER_ONE", "password": "a-secure-password"})
    assert response.status_code == 200
    assert response.json()["user"] == user
    assert client.post("/login", data={"username": "writer_one", "password": "wrong-password"}).status_code == 401
    assert client.get("/me").status_code == 401
    dependency = main.app.dependency_overrides[main.get_db]()
    session = next(dependency)
    try:
        stored = session.query(main.models.User).filter_by(username="writer_one").one()
        assert stored.password_hash != "a-secure-password"
        assert stored.password_hash.startswith("pbkdf2_sha256$600000$")
    finally:
        dependency.close()


def test_duplicate_reserved_and_invalid_registration(client):
    register_user(client)
    assert client.post("/register", json={"username": "WRITER_ONE", "password": "other-password"}).status_code == 409
    assert client.post("/register", json={"username": "test-editor", "password": "other-password"}).status_code == 422
    for username, password in [("ab", "long-password"), ("space name", "long-password"), ("valid_name", "short"), ("valid_name", "x" * 129)]:
        assert client.post("/register", json={"username": username, "password": password}).status_code == 422


def test_admin_name_is_reserved(client, monkeypatch):
    monkeypatch.setattr(main, "ADMIN_USERNAME", "Owner")
    assert client.post("/register", json={"username": "OWNER", "password": "long-password"}).status_code == 409


def test_users_can_manage_only_their_own_posts(client):
    first, first_user = register_user(client, "first_writer")
    second, _ = register_user(client, "second_writer")
    admin = authorization(client)
    post = client.post("/blogs", headers=first, json={"title": "My story", "content": "My words"}).json()
    assert post["author"] == "first_writer"
    assert post["owner_id"] == first_user["id"]
    path = f"/blogs/{post['id']}"
    assert client.get(path).status_code == 200
    assert client.get("/blogs").json()["data"][0]["author"] == "first_writer"
    assert client.put(path, headers=second, json={"title": "Stolen", "content": "Changed"}).status_code == 403
    assert client.delete(path, headers=second).status_code == 403
    assert client.get(path).json()["title"] == "My story"
    assert client.put(path, headers=first, json={"title": "My update", "content": "Revised"}).status_code == 200
    assert client.put(path, headers=admin, json={"title": "Moderated", "content": "Revised"}).status_code == 200
    assert client.delete(path, headers=first).status_code == 200
    assert client.get(path).status_code == 404


def test_registered_user_cannot_take_over_legacy_posts(client):
    admin = authorization(client)
    post = client.post("/blogs", headers=admin, json={"title": "Owner story", "content": "Original"}).json()
    headers, _ = register_user(client)
    assert post["owner_id"] is None
    assert client.delete(f"/blogs/{post['id']}", headers=headers).status_code == 403


def test_existing_blog_table_is_preserved():
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE blogs (id INTEGER PRIMARY KEY, title VARCHAR, content TEXT)"))
        connection.execute(text("INSERT INTO blogs (id, title, content) VALUES (1, 'Existing story', 'Keep this content')"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        post = db.get(main.models.Blog, 1)
        assert post is not None
        assert str(post.title) == "Existing story"
        assert str(post.content) == "Keep this content"
        assert post.author == "The Margin"
        assert post.owner_id is None
    engine.dispose()


def test_password_hashes_have_unique_salts():
    from auth import hash_password, check_password
    first = hash_password("same-password")
    second = hash_password("same-password")
    assert first != second
    assert check_password("same-password", first)
    assert not check_password("wrong-password", first)


def test_token_cannot_reference_nonexistent_user(client):
    token = main.create_token({"sub": "99999", "kind": "user"})
    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
