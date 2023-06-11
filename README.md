# Фильтр желтушных новостей

Web-сервер анализа новостей на "желтушность".

Пример использования
```commandline
curl 127.0.0.1:8080/?urls=https://inosmi.ru/20230609/ukraina-263511718.html,https://inosmi.ru/20230528/mozg-263202267.html
```

В параметре urls перечисляются ссылки на новости, которые будут проанализированы.

Пока поддерживается только один новостной сайт - [ИНОСМИ.РУ](https://inosmi.ru/). Для него разработан специальный адаптер, умеющий выделять текст статьи на фоне остальной HTML разметки. Для других новостных сайтов потребуются новые адаптеры, все они будут находиться в каталоге `adapters`. Туда же помещен код для сайта ИНОСМИ.РУ: `adapters/inosmi_ru.py`.

В перспективе можно создать универсальный адаптер, подходящий для всех сайтов, но его разработка будет сложной и потребует дополнительных времени и сил.

# Как установить

Вам понадобится Python версии 3.10 или старше. Для установки пакетов рекомендуется создать виртуальное окружение poetry.

Первым шагом установите пакеты:

```commandline
poetry install
```

Затем активируйте виртуальное окружение
```commandline
poetry shell
```

# Как запустить web-сервер

```commandline
python server.py
```

# Как запустить тесты

Для тестирования используется [pytest](https://docs.pytest.org/en/latest/), тестами покрыты сложные в отладке фрагменты кода: text_tools.py и адаптеры. Команды для запуска тестов:

```commandline
python -m pytest adapters/inosmi_ru.py
```

```commandline
python -m pytest text_tools.py
```

```commandline
python -m pytest server.py
```

# Цели проекта

Код написан в учебных целях. Это урок из курса по веб-разработке — [Девман](https://dvmn.org).
