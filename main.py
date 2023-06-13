import asyncio
import logging
from collections import namedtuple
from contextlib import asynccontextmanager
import time
from enum import Enum
from os import listdir
from os.path import isfile, join

import aiohttp

import pymorphy2
from aiocache import cached, Cache
from aiocache.serializers import PickleSerializer
from aiofile import async_open
from aiohttp import ClientResponseError, ClientConnectorError
from aiologger import Logger
from anyio import create_task_group, run
from async_timeout import timeout

from adapters import SANITIZERS, ArticleNotFound
from constants import (
    CHARGED_DICTS_FOLDER,
    REDIS_STORAGE_TIME,
    REDIS_PORT,
    REDIS_HOST,
)
from text_tools import calculate_jaundice_rate, split_by_words


TEST_ARTICLES = [
    'https://inosmi.ru/not/exist.html',  # FETCH_ERROR
    'https://inosmi.ru/20230609/ukraina-263511718.html',
    'https://inosmi.ru/20230528/mozg-263202267.html',
    'https://inosmi.ru/20230609/briks-263527997.html',
    'https://lenta.ru/brief/2021/08/26/afg_terror/',  # PARSING_ERROR
]
TIMEOUT_SEC = 3  # максимальное время ожидания ответа от ресурса/функции

Result = namedtuple('Result', 'status url score words_count')


logger = Logger.with_default_handlers(level=logging.INFO)


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def get_charged_words() -> list[str]:
    """Получает из директории CHARGED_DICTS_FOLDER список 'заряженных' слов и возвращает его."""

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
    """Контекстный менеджер, вычисляющий время выполнения фрагмента кода."""
    start = time.monotonic()
    try:
        yield
    finally:
        end = time.monotonic()
    await logger.info('Анализ закончен за {:.2} сек'.format(end - start))


async def process_article(
    session: aiohttp.ClientSession,
    morph: pymorphy2.MorphAnalyzer,
    charged_words: list[str],
    url: str,
    results: list[Result],
    /,
):
    """
    Анализирует статью на 'желутшность'. Результат сохраняется в списке results
    @param session: соединения
    @param morph: библиотека pymorphy2 для работы с текстом
    @param charged_words: список 'заряженных' слов
    @param url: адрес статьи
    @param results: список, в который сохраняется результат анализа статьи
    @return:
    """
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


@cached(
    ttl=REDIS_STORAGE_TIME,
    cache=Cache.REDIS,
    key_builder=lambda *args, **kw: 'key',
    serializer=PickleSerializer(),
    port=REDIS_PORT,
    endpoint=REDIS_HOST,
    namespace='main',
)
async def main(
    morph: pymorphy2.MorphAnalyzer, test_articles: list[str]
) -> list[Result]:
    """
    Принимает на вход список статей и возвращает список результатов их обработки
    @param morph: библиотека pymorphy2 для работы с текстом
    @param test_articles: список адресов статей
    @return:
    """
    results: list[Result] = []

    charged_words = await get_charged_words()
    await logger.debug(charged_words)

    async with aiohttp.ClientSession() as session:

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

    [await logger.info(result._asdict()) for result in results]

    return results


if __name__ == '__main__':
    morph = pymorphy2.MorphAnalyzer()
    run(main, morph, TEST_ARTICLES)
