import asyncio

import pytest

from main import TEST_ARTICLES
from server import app


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.SelectorEventLoop()
    yield loop
    loop.close()


@pytest.fixture
async def response(aiohttp_client):
    """Фикстура ответа тестируемого сервиса"""

    client = await aiohttp_client(app)
    resp = await client.get('/?urls=' + ','.join(TEST_ARTICLES))
    assert resp.status == 200
    resp = await resp.json()
    assert len(resp) == len(TEST_ARTICLES)

    yield resp
