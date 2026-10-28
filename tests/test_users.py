async def test_create_user(client):
    response = await client.post(
        "/users", json={"email": "alice@example.com", "name": "Alice"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["email"] == "alice@example.com"
    assert body["name"] == "Alice"
    assert "created_at" in body


async def test_create_user_duplicate_email(client):
    payload = {"email": "alice@example.com", "name": "Alice"}
    await client.post("/users", json=payload)

    response = await client.post("/users", json={**payload, "name": "Another Alice"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


async def test_create_user_invalid_email(client):
    response = await client.post("/users", json={"email": "not-an-email", "name": "Bob"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "email"]
