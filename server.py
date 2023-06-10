from unittest.mock import patch

from aiohttp import web

from main import main, results, TEST_ARTICLES

MAX_ARTICLES_COUNT = 10


async def handle(request):
    params = request.rel_url.query
    response = {}
    if urls := params.get('urls'):
        articles = urls.split(',')
        if len(articles) > MAX_ARTICLES_COUNT:
            message = f'too many urls in request, should be {MAX_ARTICLES_COUNT} or less'
            return web.json_response(data={'error': message}, status=400)

        await main(articles)
        response = [result._asdict() for result in results]

    return web.json_response(response)


app = web.Application()
app.add_routes([web.get('/', handle)])


def get_result_by_url(url: str, response: list[dict]):
    return next(item for item in response if item['url'] == url)


async def test_process_article_fetch_error(aiohttp_client, response):

    assert (
        get_result_by_url(TEST_ARTICLES[0], response)['status']
        == 'FETCH_ERROR'
    )


async def test_process_article_parsing_error(aiohttp_client, response):

    assert (
        get_result_by_url(TEST_ARTICLES[4], response)['status']
        == 'PARSING_ERROR'
    )


@patch('main.TIMEOUT_SEC', 0.1)
async def test_process_article_timeout_error(aiohttp_client, response):

    assert get_result_by_url(TEST_ARTICLES[1], response)['status'] == 'TIMEOUT'


if __name__ == '__main__':
    web.run_app(app)
