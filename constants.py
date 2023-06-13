import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

CHARGED_DICTS_FOLDER = os.environ.get(
    'CHARGED_DICTS_FOLDER', 'charged_dict'
)  # название папки, в которой хранятся словари 'заряженных слов'
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
REDIS_HOST, REDIS_PORT = urlparse(REDIS_URL).hostname, urlparse(REDIS_URL).port
REDIS_STORAGE_TIME = int(os.environ.get('REDIS_STORAGE_TIME', 120))
MAX_ARTICLES_COUNT = int(
    os.environ.get('MAX_ARTICLES_COUNT', 10)
)  # количество одновременно обрабатываемых статей для защиты от DOS-атак
