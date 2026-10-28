import pytest


@pytest.fixture
async def owner_id(client):
    response = await client.post(
        "/users", json={"email": "owner@example.com", "name": "Owner"}
    )
    return response.json()["id"]


async def create_task(client, owner_id, **fields):
    response = await client.post(
        "/tasks", json={"title": "Task", "owner_id": owner_id, **fields}
    )
    assert response.status_code == 201
    return response.json()


async def test_create_task(client, owner_id):
    response = await client.post(
        "/tasks",
        json={"title": "Buy milk", "description": "2 liters", "owner_id": owner_id},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["title"] == "Buy milk"
    assert body["description"] == "2 liters"
    assert body["done"] is False
    assert body["owner_id"] == owner_id


async def test_create_task_unknown_owner(client):
    response = await client.post("/tasks", json={"title": "Orphan", "owner_id": 999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Owner not found"


async def test_list_tasks_filter_done_and_pagination(client, owner_id):
    for i in range(1, 7):
        await create_task(client, owner_id, title=f"Task {i}", done=i % 2 == 0)

    done = await client.get("/tasks", params={"done": True})
    assert done.status_code == 200
    assert [t["id"] for t in done.json()] == [2, 4, 6]
    assert all(t["done"] for t in done.json())

    page = await client.get("/tasks", params={"done": False, "limit": 2, "offset": 1})
    assert page.status_code == 200
    assert [t["id"] for t in page.json()] == [3, 5]

    all_pages = await client.get("/tasks", params={"limit": 4, "offset": 4})
    assert [t["id"] for t in all_pages.json()] == [5, 6]


async def test_patch_updates_only_sent_fields(client, owner_id):
    task = await create_task(
        client, owner_id, title="Original", description="Keep me", done=False
    )

    response = await client.patch(f"/tasks/{task['id']}", json={"done": True})

    assert response.status_code == 200
    body = response.json()
    assert body["done"] is True
    assert body["title"] == "Original"
    assert body["description"] == "Keep me"

    stored = (await client.get(f"/tasks/{task['id']}")).json()
    assert stored == body


async def test_delete_then_get_returns_404(client, owner_id):
    task = await create_task(client, owner_id)

    delete = await client.delete(f"/tasks/{task['id']}")
    assert delete.status_code == 204

    response = await client.get(f"/tasks/{task['id']}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"
