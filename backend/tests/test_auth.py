async def test_register_returns_token_and_user(client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "secret123", "name": "Alice"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert "password" not in body["user"]


async def test_duplicate_email_conflict(client):
    payload = {"email": "dup@example.com", "password": "secret123", "name": "Dup"}
    assert (await client.post("/api/auth/register", json=payload)).status_code == 201
    r = await client.post("/api/auth/register", json=payload)
    assert r.status_code == 409


async def test_login_ok_and_wrong_password(client):
    await client.post(
        "/api/auth/register",
        json={"email": "bob@example.com", "password": "secret123", "name": "Bob"},
    )
    ok = await client.post(
        "/api/auth/login", json={"email": "bob@example.com", "password": "secret123"}
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = await client.post(
        "/api/auth/login", json={"email": "bob@example.com", "password": "wrong-pass"}
    )
    assert bad.status_code == 401


async def test_register_short_password_rejected(client):
    r = await client.post(
        "/api/auth/register", json={"email": "x@example.com", "password": "short", "name": "X"}
    )
    assert r.status_code == 422
