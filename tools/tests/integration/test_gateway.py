import pytest


@pytest.mark.asyncio
async def test_gateway_lists_tools(filesystem_client):
    tools = await filesystem_client.list_tools()
    names = [t.name for t in tools]
    assert "read_file" in names
    assert "write_file" in names
