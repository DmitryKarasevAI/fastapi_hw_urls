# FASTAPI URL Project
## Инструкция по запуску API:
- Клонировать данный [гитхаб репозиторий](https://github.com/DmitryKarasevAI/fastapi_hw_urls);
- Перейти в папку /fastapi_hw_urls/docker выполнить docker compose up --build (иногда запускается со второй попытки, просто запустить команду ещё раз);
- Также можно посмотреть готовое развёрнутое решение [здесь](http://158.160.136.141:9999/docs#/).

## Инструкция по запуску тестов:
- Нагрузочные тесты будут выполнены автоматически при поднятии docker compose up --build (см. locustfile.py, Dockerfile.locust, docker-compose.yml);
- Unit тесты и функциональные тесты можно запустить командой pytest --cov-config=.coveragerc. Для вывода coverage выполнить coverage run -m pytest tests;
- Для просмотра coverage без запуска можно обратиться по [ссылке](https://github.com/DmitryKarasevAI/fastapi_hw_urls/blob/main/coverage.html).

## Описание API:

Данное API написано на фреймворке FastAPI с использованием базы данных на PostgreSQL и Redis для кэширования эндпоинтов. API содержит в себе: 
- Регистрацию и авторизацию пользователей;
- Возможность добавления/удаления/изменения коротких ссылок для перенаправления с возможностью указания их времени жизни;
- Возможность перехода на исходный сайт по короткой ссылке;
- Возможность смотреть статистику по короткой ссылке (количество переходов, время создания, время протухания, исходная ссылка);
- Возможность смотреть статистику по исходной ссылке (поиск коротких ссылок на данную ссылку, времена их создания, времена их протухания);
- Возможность создания кастомных ссылок при указании custom_alias;
- Возможность создания ссылок с временем протухания;
- Некоторые эндпоинты имеют возможность кэширования (ниже будет описано какие и почему кэшируются другие не кэшируются);
- Некоторые эндпоинты очищают кэш (ниже будет описано какие и почему именно они это делают);
- Реализованные дополнительные функции, которые прописаны в дз:
  - Отображение истории всех истекших ссылок с информацией о них;
  - Создание коротких ссылок для незарегистрированных пользователей.
## Описание БД:
### Описание моделей:
#### Table user (Таблица пользователей сервиса):
- id: UUID (pk) - id пользователя;
- email: String (nullable=False) - email пользователя;
- hashed_password: String (nullable=False) - хэшированный пароль пользователя;
- registered_at: Timestamp (nullable=True) - время регистрации;
- is_active: Bool (nullable=False) - является ли пользователь активным;
- is_superuser: Bool (nullable=False) - является ли пользователь суперюзером;
- is_verified: Bool (nullable=False) - является ли пользователь верифицированным;

#### Table urls (Таблица связей ссылок):
- id: Integer (pk) - id связи full_url-short_url;
- creator_id: UUID (nullable=True) - id создателя связи;
- full_url: String (nullable=False) - оригинальный URL;
- short_url: String (nullable=False) - URL alias;
- creation_time: DateTime (nullable=False) - время создания связи;
- expires_at: DateTime (nullable=True) - время протухания связи;

#### Table queries (Таблица переходов по коротки ссылкам):
- id: Integer (pk) - id перехода по короткой ссылке;
- url_id: Integer (fk=urls.id) - id связи;
- full_url: String - оригинальный URL;
- short_url: String (fk=urls.short_url) - URL alias;
- access_time: DateTime - время перехода;

### Описание схем:
UserRead - стандартная схема BaseUser из библиотеки fastapi_users;
UserCreate - стандартная схема BaseUserCreate из библиотеки fastapi_users;
URLCreate - схема для создания связи:
- full_url: str - оригинальный URL;
- custom_alias: Optional[str] - кастомный URL alias, если не передаётся в модель, тогда ссылка создаётся путём хэширования с солью;
- expires_at: Optional[str] (формат ввода YYYY-MM-DD HH:MM) - время протухания связи, если не передаётся в модель, тогда ссылка не протухает.

## Примеры запросов:
![Общий вид API](https://drive.google.com/uc?export=view&id=12n2De4WnSYZ4XKw9Ph6r00imoC2CVFS5)
Начнём с авторизации. Убедительная просьба авторизоваться через кнопку Authorize справа сверху (иначе fastapi_users почему-то тупит). Регистрация пользователя доступна по ручке POST /auth/register.

![Регистрация нового пользователя](https://drive.google.com/uc?export=view&id=1sNxDPn0hA17QifWcACcHu4Nm_M4StCwI)
![Аутентификация](https://drive.google.com/uc?export=view&id=1pgpShHJ1_kMfpK63eIDlsJ_l-c7E406p)

Далее мы имеем следующие ручки:
- GET /links/check_cache - dev ручка, демонстрирующая работу кэша (time.sleep(3), второй вызов моментальный);
- POST /links/shorten - ручка, которая создаёт связь между full_url и short_url в базе данных;
- GET /links/search - ищет все short_urls по full_url;
- GET /links/{short_url} - редиректит на страницу full_url по short_url;
- DELETE /links/{short_url} - удаляет связь между short_url и соответствующего full_url;
- PUT /links/{short_url} - заменяет short_url в уже существующей связи на new_url;
- GET /links/expired/stats - показывает статистику по всем протухшим ссылкам;
- GET /links/{short_url}/stats - показывает статистику по short_url;

Теперь пройдёмся подробно по работе каждой из ручек:

**POST /links/shorten**

Принимает на вход схему URLCreate, в которой custom_alias и expires_at - опциональны;

Данная ручка не кэшируется, так как её нет смысла выполнять с одинаковыми параметрами;

Данная ручка чистит кэш, так как она изменяет базу данных;

Варианты статусов (status_code):
- 200;
- 400: "Неверный формат URL" - срабатывает при условии, если full_url не является верной ссылкой;
- 400: "Неверный формат expires_at. Ожидается формат YYYY-MM-DD HH:MM." - срабатывает, если атрибут expires_at модели не в указанном формате;
- 400: "Неверный формат кастомного alias. Разрешены символы A-Z, a-z, 0-9, '-' и '_', длина 1-20 символов." - срабатывает, если custom_alias указан и не подходит под указанный формат;
- 400: "Указанный alias уже существует." - срабатывает, если custom_alias указан и совпадает с short_url в другой связи;
- 500: "Произошла непредвиденная ошибка. Попробуйте повторить запрос позже." - если произошла ошибка, не перечисленная выше.

Данная ручка работает как для авторизованных, так и для неавторизованных пользователей (для неавторизованных creator_id равен null).

Демонстрация работы ручки:

Correct url + correct custom alias + correct expired_at 200
![](https://drive.google.com/uc?export=view&id=1PHUlZ8_h_gBIH3dybL6BMJX8rnUJCIPU)

Correct url + correct custom alias + incorrect expired_at 400
![](https://drive.google.com/uc?export=view&id=1QcO9IfQcMaiabpMwMWyCAGZq2iLUJBog)

Correct url + incorrect custom alias + correct expired_at 400
![](https://drive.google.com/uc?export=view&id=1QDai8pZCKaE1Hgwd6s-7XeQEJWiMQTqy)

Correct url + repeated custom alias + correct expired_at 400
![](https://drive.google.com/uc?export=view&id=1q9Z6AESqLolel_8FfxroxO7OOL1FtoMb)

Incorrect url + correct custom alias + correct expired_at 400
![](https://drive.google.com/uc?export=view&id=11fqSDBXkh7YFh0xRlyaNRocquDA7O9Ig)

Correct url + no custom alias + no expired_at 200
![](https://drive.google.com/uc?export=view&id=148C20bSVmPxBIFLfGx-nh-XsDzoZyCd6)

**GET /links/search**

Принимает на вход full_url, по которому выводятся все короткие ссылки на него;

Данная ручка кэшируется, так как данный запрос имеет смысл вызывать с одинаковыми параметрами;

Данная ручка не чистит кэш, иначе она почистит его у себя же;

Варианты статусов (status_code):
- 200;
- 404: "Ссылка не найдена." - если full_url не фигурирует ни в одной из связей.

Данная ручка работает как для авторизованных, так и для неавторизованных пользователей.

Демонстрация работы ручки:

Existing url 200
![](https://drive.google.com/uc?export=view&id=1OkseWcGBqHUkJXnxfufoacoKa9Ql0cx1)

Non-existent url 404
![](https://drive.google.com/uc?export=view&id=1yb1pHQf_MKYJjwRaAF_Nf9xP7Jvd1gC8)

**GET /links/{short_url}**

Принимает на вход short_url, по которому происходит редирект;

Данная ручка кэшируется, так как данный запрос имеет смысл вызывать с одинаковыми параметрами;

Данная ручка не чистит кэш, иначе она почистит его у себя же;

Варианты статусов (status_code):
- 200;
- 404: "Короткий URL не найден." - если short_url не ссылается ни на какой full_url;
- 404: "Ссылка больше недоступна." - если связь short_url - full_url протухла;
- 500: "Произошла непредвиденная ошибка. Попробуйте повторить запрос позже." - если произошла ошибка, не перечисленная выше.

Данная ручка работает как для авторизованных, так и для неавторизованных пользователей.

Демонстрация работы ручки:

Existing + fresh url 200
![](https://drive.google.com/uc?export=view&id=13YaG3uAmEPiJ00LsYFus3CLIxbLnfRWB)

Non-existent url 404
![](https://drive.google.com/uc?export=view&id=1EFgcxr05CC2WDdZUzmWqtoQOm1E0v667)

Existing + old url 404
![](https://drive.google.com/uc?export=view&id=1JYReDvEHn-5zEkuSBmJumvdaSSNfUn9y)

**DELETE /links/{short_url}**

Принимает на вход short_url, связь с которым надо удалить;

Данная ручка не кэшируется, так как данный запрос не имеет смысла вызывать с одинаковыми параметрами;

Данная ручка чистит кэш, так как изменяет базу данных;

Варианты статусов (status_code):
- 200;
- 403: "Чтобы получить доступ, надо залогиниться." - если анонимный пользователь пытается воспользоваться ручкой;
- 404: "Короткий URL не найден." - если short_url не ссылается ни на какой full_url;
- 403: "Нет прав." - если пользователь пытается удалить short_url другого пользователя;
- 500: "Произошла непредвиденная ошибка. Попробуйте повторить запрос позже." - если произошла ошибка, не перечисленная выше.

Данная ручка работает только для авторизованных пользователей.

Демонстрация работы ручки:

Existing url + author 200
![](https://drive.google.com/uc?export=view&id=1Ghxt5pb2YZeeV6rQMq5DzEAXkkbA0Suv)

Existing url + anonym 403
![](https://drive.google.com/uc?export=view&id=1CQowmBKtt2R51Wdm6g0wHRQWVTB4AU8t)

Non-existent url 404
![](https://drive.google.com/uc?export=view&id=1dVomy3HTqwBP-m-gNvGhvietcAa868TD)

Existing url + non-author 403
![](https://drive.google.com/uc?export=view&id=1jYTBEAoTNbj2W0LpFDsnSBYyLgHYRhqy)

**PUT /links/{short_url}**

Принимает на вход short_url и new_url, связь с short_url -> full_url меняется на new_url -> full_url;

Данная ручка не кэшируется, так как данный запрос не имеет смысла вызывать с одинаковыми параметрами;

Данная ручка чистит кэш, так как изменяет базу данных;

Варианты статусов (status_code):
- 200;
- 403: "Чтобы получить доступ, надо залогиниться." - если анонимный пользователь пытается воспользоваться ручкой;
- 404: "Короткий URL не найден." - если short_url не ссылается ни на какой full_url;
- 403: "Нет прав." - если пользователь пытается изменить short_url другого пользователя;
- 400: "Указанный alias уже существует." - срабатывает, если new_url указан и совпадает с short_url в другой связи;
- 500: "Произошла непредвиденная ошибка. Попробуйте повторить запрос позже." - если произошла ошибка, не перечисленная выше.

Данная ручка работает только для авторизованных пользователей.

Демонстрация работы ручки:

Продемонстрирую только успешный вызов, потому что ошибки аналогичны тем, что были уже рассмотрены в других ручках

Existing short_url + correct new_url + author 200
![](https://drive.google.com/uc?export=view&id=17u5LyicjHSIAZe_p4mQP1BjpO0PLkEKI)

**GET /links/expired/stats**

Возвращает статистику по протухшим связям;

Данная ручка кэшируется, так как данный запрос имеет смысл вызывать с одинаковыми параметрами;

Данная ручка не чистит кэш, так как она сама кэшируется;

Варианты статусов (status_code):
- 200;
- 500: "Произошла непредвиденная ошибка. Попробуйте повторить запрос позже." - если произошла ошибка, не перечисленная выше.

Данная ручка работает как для авторизованных, так и для неавторизованных пользователей.

Демонстрация работы ручки:

200
![](https://drive.google.com/uc?export=view&id=1YEYhKKZEQIfE_9NG9shiB2iCsNne2QAW)


**GET /links/{short_url}/stats**

Возвращает статистику по short_url;

Данная ручка кэшируется, так как данный запрос имеет смысл вызывать с одинаковыми параметрами;

Данная ручка не чистит кэш, так как она сама кэшируется;

Варианты статусов (status_code):
- 200;
- 404: "Короткий URL не найден." - если short_url не ссылается ни на какой full_url;
- 500: "Произошла непредвиденная ошибка. Попробуйте повторить запрос позже." - если произошла ошибка, не перечисленная выше.

Данная ручка работает как для авторизованных, так и для неавторизованных пользователей.

Демонстрация работы ручки:

Existing url 200
![](https://drive.google.com/uc?export=view&id=15bwVuVx0jF48bQhNW4QDBpnJZe3GzYnM)

Non-existent url 404
![](https://drive.google.com/uc?export=view&id=1IRyviUWFgXVi3jcvJhV-zihZlSW5q6XI)

## Краткое описание тестов:
### Unit-тесты: 
Так как в моей работе в основном мы работаем с эндпоинтами API, то логичнее всего тестировать их сразу функционально. Таким образом, в Unit-тесты попало всего два теста, которые тестируют единственную функцию, которую можно протестировать Unit-тестом в данной работе - valid_url(url) (см. test_unit.py)
### Функциональное тестирование:
В разделе функционального тестирования мне удалось добиться:
- Процента покрытия тестами 94% (Непокрытые проценты объясняются тем, что в эндпоинтах предусмотрены ошибки с кодом 500, которые просто нельзя протестировать);
- Протестирована вся логика приложения, рассмотрены всевозможные входные данные, всевозможно ошибки/corner кейсы всех эндпоинтов (см. test_api.py);
- Были написаны фикстуры для мокирования реального использования базы данных, кэширования, анонимных и авторизованных пользователей (см. conftest.py)
### Нагрузочное тестирование:
В разделе нагрузочного тестирования проверяется стойкость теста под средними нагрузками:
- Нагрузочные тесты запускаются автоматически при поднятии docker-compose.yml;
- Тесты проверяют сервис на нагрузку и коллизию самых главных эндпоинтов сервиса (см. locustfile.py).

Вид нагрузочного тестирования (0.00% - процент ошибочных запросов на эндпоинты)

![](https://drive.google.com/uc?export=view&id=1yp50r6G62YRkiE1lVmdg9gkWFz8TxBBX)
