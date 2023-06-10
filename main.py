import asyncio
from collections import namedtuple
from contextlib import asynccontextmanager
import time
from enum import Enum
from os import listdir
from os.path import isfile, join

import aiohttp

import pymorphy2
from aiofile import async_open
from aiohttp import ClientResponseError, ClientConnectorError
import logging
from anyio import create_task_group, run
from async_timeout import timeout

from adapters import SANITIZERS, ArticleNotFound
from text_tools import calculate_jaundice_rate, split_by_words


CHARGED_DICTS_FOLDER = 'charged_dict'
TEST_ARTICLES = [
    'https://inosmi.ru/not/exist.html',  # FETCH_ERROR
    'https://inosmi.ru/20230609/ukraina-263511718.html',
    'https://inosmi.ru/20230528/mozg-263202267.html',
    'https://inosmi.ru/20230609/briks-263527997.html',
    'https://lenta.ru/brief/2021/08/26/afg_terror/',  # PARSING_ERROR
]
TIMEOUT_SEC = 3  # максимальное время ожидания ответа от ресурса/функции

Result = namedtuple('Result', 'status url score words_count')
results: list[Result] = []


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def get_charged_words():

    dict_files = [
        join(CHARGED_DICTS_FOLDER, f)
        for f in listdir(CHARGED_DICTS_FOLDER)
        if isfile(join(CHARGED_DICTS_FOLDER, f)) and f.lower().endswith('.txt')
    ]

    charged_words = []

    for src in dict_files:
        async with async_open(src, 'r') as afp:
            async for line in afp:
                charged_words.append(line.strip())

    return charged_words


@asynccontextmanager
async def get_run_time(*args, **kwds):
    start = time.monotonic()
    try:
        yield
    finally:
        end = time.monotonic()
    logger.info('Анализ закончен за {:.2} сек'.format(end - start))


async def process_article(session, morph, charged_words, url, results, /):

    try:
        async with timeout(TIMEOUT_SEC):
            html = await fetch(session, url)
    except (ClientConnectorError, ClientResponseError):
        results.append(
            Result(ProcessingStatus.FETCH_ERROR.value, url, None, None)
        )
        return
    except asyncio.TimeoutError:
        results.append(Result(ProcessingStatus.TIMEOUT.value, url, None, None))
        return

    try:
        text = SANITIZERS['inosmi_ru'](html, plaintext=True)
    except ArticleNotFound:
        results.append(
            Result(ProcessingStatus.PARSING_ERROR.value, url, None, None)
        )
        return

    try:
        async with get_run_time(), timeout(TIMEOUT_SEC):
            article_words = await split_by_words(
                morph=morph,
                text=text,
            )
    except asyncio.TimeoutError:
        results.append(Result(ProcessingStatus.TIMEOUT.value, url, None, None))
        return

    score = calculate_jaundice_rate(
        article_words=article_words, charged_words=charged_words
    )
    words_count = len(article_words)

    results.append(Result(ProcessingStatus.OK.value, url, score, words_count))


async def main(test_articles: list):

    charged_words = await get_charged_words()
    print(charged_words)

    async with aiohttp.ClientSession() as session:
        morph = pymorphy2.MorphAnalyzer()

        async with create_task_group() as tg:
            for url in test_articles:
                tg.start_soon(
                    process_article,
                    session,
                    morph,
                    charged_words,
                    url,
                    results,
                )

    for result in results:
        print('Статус:', result.status)
        print('URL:', result.url)
        print('Рейтинг:', result.score)
        print('Слов в статье:', result.words_count)


if __name__ == '__main__':

    run(main, TEST_ARTICLES)
