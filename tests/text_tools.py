import os

import pymorphy2
from aiofile import async_open

from text_tools import split_by_words, calculate_jaundice_rate


async def test_split_by_words():
    # Экземпляры MorphAnalyzer занимают 10-15Мб RAM т.к. загружают в память много данных
    # Старайтесь организовать свой код так, чтоб создавать экземпляр MorphAnalyzer заранее и в единственном числе
    morph = pymorphy2.MorphAnalyzer()

    assert await split_by_words(
        morph, '«Удивительно, но это стало началом!»'
    ) == ['удивительно', 'это', 'стать', 'начало']

    src = os.path.join(
        'test_data', 'gogol_nikolay_taras_bulba_-_bookscafenet.txt'
    )
    check_words = ['николай', 'тарас', 'гоголь']
    async with async_open(src, 'r') as afp:
        words = await split_by_words(morph, await afp.read())
    assert all(word in words for word in check_words)


def test_calculate_jaundice_rate():
    assert -0.01 < calculate_jaundice_rate([], []) < 0.01
    assert (
        33.0
        < calculate_jaundice_rate(
            ['все', 'аутсайдер', 'побег'], ['аутсайдер', 'банкротство']
        )
        < 34.0
    )
