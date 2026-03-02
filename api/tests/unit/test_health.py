import pytest


def test_health_route_importable():
    from api.routes.health import router
    assert router is not None


@pytest.mark.unit
async def test_health_response_has_status_key(fake_redis):
    from api.routes.health import HealthResponse
    response = HealthResponse(status="ok", components={"database": "ok", "redis": "ok"})
    assert response.status == "ok"
    assert "database" in response.components
    assert "redis" in response.components
