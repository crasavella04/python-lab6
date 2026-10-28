import pytest


@pytest.mark.parametrize("path", ["/tasks", "/tasks/999"])
async def test_process_time_header(client, path):
    response = await client.get(path)

    assert "X-Process-Time" in response.headers
    assert float(response.headers["X-Process-Time"]) >= 0
