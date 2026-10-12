# Нагрузочное тестирование: baseline vs current

Сравнивает билд до оптимизации (`c3e1a7b`) с текущим на одинаковых данных и одном сценарии Locust.

## Подготовка

```bash
python -m venv .lt-venv && .lt-venv/Scripts/pip install locust
git worktree add ../AITesting-baseline c3e1a7b
cp .env ../AITesting-baseline/.env
```

## Запуск

Стенды поднимаются по очереди, чтобы не делить CPU:

```bash
.lt-venv/Scripts/python loadtest/run.py baseline   # :8000, проект aitesting-baseline
.lt-venv/Scripts/python loadtest/run.py current    # :8001, проект aitesting-loadtest
.lt-venv/Scripts/python loadtest/compare.py        # results/summary.md + summary.json
```

`run.py` поднимает `postgres redis migrate django`, наполняет БД через `seed.py` (если она пустая) и для каждого
профиля запускает 30-секундный прогрев, а затем сам профиль. Во время прогона пишется `docker stats`.
Текущий билд работает в отдельном compose-проекте и томе (`compose.override.yml`), поэтому dev-БД
`aitesting_store_postgres_data` не затрагивается.

| Профиль | Нагрузка |
|---|---|
| `smoke` | 1 пользователь, 20 с |
| `load` | 20 пользователей, 3 мин |
| `stress` | ступени 10 → 25 → 50 → 100 → 200 пользователей по 2 мин |
| `spike` | 5 → 150 пользователей за 10 с, удержание 60 с |

Данные: 105 категорий (3 уровня), 5000 товаров, 300 пользователей (`lt_user0..299` / `loadtest123`),
1215 закрытых заказов, 9087 позиций и 20 скидок.

## Оговорки

- Оба билда работают под `runserver` с `DEBUG=True`, как в их compose. Абсолютные цифры ниже, чем были бы под
  gunicorn, но условия для двух билдов одинаковые.
- `/items/` и `/category/` запрашиваются без `limit`, поэтому ответ идентичен в обоих билдах.
- `/index` в текущем билде отдаёт страницу из 30 товаров вместо всех 5000. Это часть оптимизации, а не
  одинаковая работа.

Удаление стендов: `docker compose -p aitesting-loadtest -f docker-compose.yml -f loadtest/compose.override.yml down -v`,
`docker compose down -v` в `../AITesting-baseline` и `git worktree remove ../AITesting-baseline`.
