# Практическая работа №4 — Python и Go через gRPC и mTLS

Чугунов К. Н., ЭФБО-11-24.

Один контракт `proto/api.proto` генерирует Python-клиент и Go-сервер DiceService.
Django обращается к Go напрямую по mTLS (`127.0.0.1:8443`) и к nginx по mTLS
(`127.0.0.1:9448`); nginx передаёт запрос локальному h2c-серверу (`127.0.0.1:50051`).
CA, серверный и клиентский сертификаты генерируются CFSSL. Закрытые ключи создаются
локально при запуске и не входят ни в Git, ни в контекст сборки.

## Воспроизводимый запуск в Ubuntu 24.04

На хосте нужен запущенный Docker с Linux-контейнерами. Из каталога проекта:

```sh
docker compose up -d --build
docker compose exec lab python -m scripts.integration_test
docker compose logs lab
```

Откройте `http://localhost:18004/` и нажмите «Бросить кости». Второй независимый
Django-клиент работает по `http://localhost:18005/`. Маршруты `/grpc` и `/nginx`
выполняют соответствующий RPC и выводят выпавшее число. Порты 8443, 9448 и 50051
не опубликованы на хосте. Ubuntu с процессами сервера, nginx и обоих клиентов
работает внутри лабораторного контейнера.

Проверки выполняются реально, а результаты сохраняются в `evidence/integration.json`.
Они включают по 100 параллельных вызовов двух путей, запрет запросов без клиентского
сертификата и с чужим сертификатом, оба web-клиента и отправку формы с CSRF.
Логи лежат в `logs/`; остановка: `docker compose down`.

## Установка непосредственно на Ubuntu 24.04

```sh
sudo apt update
sudo apt install python3-venv golang-go protobuf-compiler nginx golang-cfssl
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export PATH="$PATH:$(go env GOPATH)/bin"
go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.36.5
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.5.1
sh scripts/generate.sh
go test -race ./...
mkdir -p bin
go build -o bin/dice-server ./server
sh scripts/certs.sh
sh scripts/start.sh
```

`scripts/start.sh` запускает два клиента командами `python manage.py runserver
0.0.0.0:8000 --noreload` и `python manage.py runserver 0.0.0.0:8001 --noreload`.
Тесты запускаются из другой оболочки: `. .venv/bin/activate && python -m
scripts.integration_test`. Для native-запуска открываются `http://localhost:8000/`
и `http://localhost:8001/`. Runserver используется только для учебной лаборатории.

## Исправления неточностей методички

- Порт nginx унифицирован: 9448 и в конфигурации, и в Python-клиенте.
- `/grpc` и `/nginx` связаны со своими обработчиками вместо общей страницы.
- Шаблон находится в `client/templates`, а не в установленном пакете Django.
- Генератор случайных чисел безопасен при параллельных RPC.
- Сгенерированный Python-импорт исправляется на относительный скриптом генерации.
- Код обработки ошибок возвращает HTTP 503, а не обращается к незаданной переменной.
- Несколько клиентов запускаются позиционным аргументом `runserver`, без несуществующего `-p`.
- H2C разрешён только на loopback: nginx и Go находятся в одной среде Ubuntu.

## Официальная документация

- https://grpc.io/docs/guides/auth/
- https://nginx.org/en/docs/http/ngx_http_grpc_module.html
- https://docs.djangoproject.com/en/5.2/ref/django-admin/#runserver
- https://github.com/cloudflare/cfssl
