import pymorphy2
from aiocache import Cache
from aiohttp import web

from main import main
from constants import REDIS_URL, MAX_ARTICLES_COUNT


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


cache = Cache.from_url(REDIS_URL)

app = web.Application()
app.add_routes([web.get('/', handle)])

if __name__ == '__main__':
    app['morph'] = pymorphy2.MorphAnalyzer()

    web.run_app(app)
