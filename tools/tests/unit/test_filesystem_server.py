import pytest


@pytest.mark.asyncio
async def test_read_file_raises_not_implemented():
    from tools.servers.filesystem_server import read_file
    with pytest.raises(NotImplementedError):
        await read_file("/tmp/nonexistent")


@pytest.mark.asyncio
async def test_write_file_raises_not_implemented():
    from tools.servers.filesystem_server import write_file
    with pytest.raises(NotImplementedError):
        await write_file("/tmp/test", "content")
