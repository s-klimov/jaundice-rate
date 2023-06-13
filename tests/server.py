from unittest.mock import patch

import pytest
import redis

from main import REDIS_HOST, REDIS_PORT


@pytest.fixture(autouse=True)
def run_around_tests():

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    r.flushdb()  # очищаем кэш Redis перед выполнением теста

    yield


async def test_process_article_fetch_error(aiohttp_client, response):
    """Тест запроса несуществующей страницы на сайте inosmi.ru."""

    assert (
        get_result_by_url('https://inosmi.ru/not/exist.html', response)[
            'status'
        ]
        == 'FETCH_ERROR'
    )


async def test_process_article_parsing_error(aiohttp_client, response):
    """Тест запроса статьи с сайта, отличного от inosmi.ru."""

    assert (
        get_result_by_url(
            'https://lenta.ru/brief/2021/08/26/afg_terror/', response
        )['status']
        == 'PARSING_ERROR'
    )


@patch('main.TIMEOUT_SEC', 0.1)
async def test_process_article_timeout_error(aiohttp_client, response):
    """Тест запроса статьи при условии недопустимого временного интервала для запроса и анализа статьи."""

    assert (
        get_result_by_url(
            'https://inosmi.ru/20230609/ukraina-263511718.html', response
        )['status']
        == 'TIMEOUT'
    )


def get_result_by_url(url: str, response: list[dict]) -> dict:
    """
    Сервисная функция, которая возвращает первый элемент из списка словарей response, ключ url которого (элемента)
    равен заданному.
    @param url: значение ключа url по которому будет поиск в списке
    @param response: список словарей, в котором каждый словарь имеет ключ url (иначе ошибка)
    @return: словарь с найденным ключом url
    """
    return next(item for item in response if item['url'] == url)
