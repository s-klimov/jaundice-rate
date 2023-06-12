import os
from unittest.mock import patch

import pymorphy2
from aiocache import Cache
from aiohttp import web
from dotenv import load_dotenv

from main import main, REDIS_URL

load_dotenv()

# количество одновременно обрабатываемых статей для защиты от DOS-атак
MAX_ARTICLES_COUNT = int(os.environ.get('MAX_ARTICLES_COUNT', 10))

cache = Cache.from_url(REDIS_URL)


async def handle(request):
    """
    Обработчик get-запроса, в урле которого д.б. параметр urls с перечислением адресов статей для анализа
    @param request:
    @return:
    """
    params = request.rel_url.query
    response = {}
    if urls := params.get('urls'):
        articles = urls.split(',')
        if len(articles) > MAX_ARTICLES_COUNT:
            message = f'too many urls in request, should be {MAX_ARTICLES_COUNT} or less'
            return web.json_response(data={'error': message}, status=400)

        async with cache:
            results = await main(app['morph'], articles)
        response = [result._asdict() for result in results]

    return web.json_response(response)


app = web.Application()
app.add_routes([web.get('/', handle)])


def get_result_by_url(url: str, response: list[dict]) -> dict:
    """
    Сервисная функция, которая возвращает первый элемент из списка словарей response, ключ url которого (элемента)
    равен заданному.
    @param url: значение ключа url по которому будет поиск в списке
    @param response: список словарей, в котором каждый словарь имеет ключ url (иначе ошибка)
    @return: словарь с найденным ключом url
    """
    return next(item for item in response if item['url'] == url)


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


if __name__ == '__main__':
    app['morph'] = pymorphy2.MorphAnalyzer()
    web.run_app(app)
