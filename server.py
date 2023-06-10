from aiohttp import web


async def handle(request):
    params = request.rel_url.query
    response = {}
    if urls := params.get('urls'):
        response = {'urls': urls.split(',')}
    return web.json_response(response)


app = web.Application()
app.add_routes([web.get('/', handle)])

if __name__ == '__main__':
    web.run_app(app)
