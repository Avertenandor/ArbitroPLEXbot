# 🤖 ArbitroPLEXbot - Руководство для разработки в Cursor

> **Версия:** 1.0  
> **Дата:** 2025-12-03  
> **Статус:** Production Ready

---

## 📋 О проекте

**ArbitroPLEXbot** - это Telegram-бот для крипто-фиатной экосистемы на базе монеты PLEX с высокодоходными торговыми роботами.

### Основные функции:
- 🔐 **Pay-to-Use авторизация** - вход в систему через оплату 10 PLEX
- 💰 **Система депозитов** - работа с USDT депозитами пользователей
- 📊 **Уровни доступа** - 5 уровней в зависимости от баланса PLEX
- 👥 **Реферальная программа** - многоуровневая система вознаграждений
- 🔗 **On-chain верификация** - проверка балансов через BSC blockchain
- 👨‍💼 **Админ-панель** - полноценная система управления пользователями

---

## 🏗️ Архитектура проекта

```
arbitragebot/
├── app/                    # Бизнес-логика и сервисы
│   ├── models/             # SQLAlchemy модели (БД)
│   ├── repositories/       # Слой доступа к данным
│   ├── services/           # Бизнес-сервисы
│   ├── tasks/              # Фоновые задачи
│   └── utils/              # Утилиты
│
├── bot/                    # Telegram Bot (aiogram 3.x)
│   ├── handlers/           # Обработчики команд и сообщений
│   ├── keyboards/          # Клавиатуры (Reply/Inline)
│   ├── middlewares/        # Middleware (auth, session, logging)
│   ├── states/             # FSM состояния
│   ├── i18n/               # Переводы (RU/EN)
│   └── main.py             # Точка входа бота
│
├── jobs/                   # Планировщик задач (APScheduler)
│   ├── tasks/              # Периодические задачи
│   ├── scheduler.py        # Планировщик
│   └── worker.py           # Worker для задач
│
├── alembic/                # Миграции БД
├── scripts/                # Вспомогательные скрипты
├── tests/                  # Тесты
└── docker-compose.python.yml  # Docker Compose (ИСПОЛЬЗУЙ ЭТОТ!)
```

---

## 🔧 Технический стек

| Компонент | Технология | Версия |
|-----------|------------|--------|
| **Язык** | Python | 3.11+ |
| **Bot Framework** | aiogram | 3.x |
| **БД** | PostgreSQL | 15 |
| **Кэш/FSM** | Redis | 7 |
| **ORM** | SQLAlchemy | 2.x (async) |
| **Миграции** | Alembic | - |
| **Blockchain** | Web3.py | - |
| **Задачи** | APScheduler | - |
| **Логирование** | loguru | - |

---

## 🚀 Быстрый старт

### 1. Локальная разработка

```bash
# Установить зависимости
pip install -r requirements.txt

# Создать .env файл
cp .env.example .env

# Заполнить .env переменными (см. SERVER_INFO.md)

# Запустить PostgreSQL и Redis (Docker)
docker compose -f docker-compose.python.yml up -d postgres redis

# Применить миграции
alembic upgrade head

# Запустить бота
python bot/main.py
```

### 2. Деплой на продакшен

```bash
# Локально: закоммитить изменения
git add .
git commit -m "описание изменений"
git push

# На сервере: подключиться через gcloud
gcloud compute ssh instance-20251107-043512 \
  --zone=europe-north1-a \
  --project=telegram-bot-444304 \
  --command="cd /opt/arbitragebot && sudo git pull && sudo docker compose -f docker-compose.python.yml up -d --build"

# Проверить логи
gcloud compute ssh instance-20251107-043512 \
  --zone=europe-north1-a \
  --project=telegram-bot-444304 \
  --command="sudo docker compose -f /opt/arbitragebot/docker-compose.python.yml logs bot --tail=50"
```

---

## ⚠️ КРИТИЧНЫЕ ПРАВИЛА

### 🔴 БЕЗОПАСНОСТЬ

1. **НИКОГДА не коммитить:**
   - `.env` файлы
   - `SERVER_INFO.md` (локально ТОЛЬКО!)
   - Приватные ключи
   - API токены
   - Пароли

2. **Секреты хранить в:**
   - `.env` (локально)
   - Docker secrets (на сервере)
   - Переменные окружения

3. **Проверка перед коммитом:**
   ```bash
   # Убедиться что .gitignore включает:
   git check-ignore .env
   git check-ignore SERVER_INFO.md
   ```

### 🔴 DOCKER COMPOSE

**⚠️ ВАЖНО:** Используй **ТОЛЬКО** `docker-compose.python.yml`!

```bash
# ✅ ПРАВИЛЬНО
docker compose -f docker-compose.python.yml up -d --build

# ❌ НЕПРАВИЛЬНО
docker compose up -d  # Использует Node.js Dockerfile!
```

### 🔴 КОДИРОВКА

**Все строки с кириллицей ТОЛЬКО через i18n систему!**

```python
# ❌ ПЛОХО - хардкод кириллицы
await message.answer("Привет!")

# ✅ ХОРОШО - через i18n
from bot.i18n.translations import _
await message.answer(_('welcome.greeting'))
```

**Добавление новых переводов:**

1. Открой `bot/i18n/translations.py`
2. Добавь ключ в `RU_TRANSLATIONS` и `EN_TRANSLATIONS`
3. Используй `_('section.key', param1=value1)`

### 🔴 МИГРАЦИИ БД

**После изменения моделей - ВСЕГДА создавай миграцию!**

```bash
# Создать автомиграцию
alembic revision --autogenerate -m "описание изменений"

# Проверить сгенерированный файл
cat alembic/versions/XXXX_название.py

# Применить локально для теста
alembic upgrade head

# Откатить если нужно
alembic downgrade -1
```

---

## 📝 Стандарты кода

### 1. Типизация обязательна

```python
# ✅ ХОРОШО
async def get_user(user_id: int) -> User | None:
    """Get user by ID."""
    return await user_repo.get_by_id(user_id)

# ❌ ПЛОХО
async def get_user(user_id):
    return await user_repo.get_by_id(user_id)
```

### 2. Докстроки для публичных функций

```python
async def calculate_daily_plex(deposit_amount: Decimal) -> Decimal:
    """
    Calculate daily PLEX requirement for deposit.
    
    Args:
        deposit_amount: Deposit amount in USDT
        
    Returns:
        Required PLEX per day (10 PLEX per 1 USDT)
        
    Raises:
        ValueError: If deposit_amount is negative
    """
    if deposit_amount < 0:
        raise ValueError("Deposit amount must be positive")
    return deposit_amount * Decimal("10")
```

### 3. Логирование через loguru

```python
from loguru import logger

# Используй уровни правильно
logger.debug("Детальная информация для отладки")
logger.info("Обычная информация о работе")
logger.warning("Предупреждение о потенциальной проблеме")
logger.error("Ошибка, но программа работает")
logger.critical("Критическая ошибка, требует вмешательства")
```

### 4. PLEX токен - 9 decimals!

```python
# ✅ ПРАВИЛЬНО
PLEX_DECIMALS = 9
plex_balance = amount_wei / (10 ** PLEX_DECIMALS)

# ❌ НЕПРАВИЛЬНО
plex_balance = amount_wei / (10 ** 18)  # Это для USDT!
```

---

## 🔍 Частые задачи

### Добавление нового хендлера

1. Создай функцию в `bot/handlers/твой_модуль.py`:

```python
from aiogram import Router, F
from aiogram.types import Message
from bot.i18n.translations import _

router = Router()

@router.message(F.text == "🎯 Кнопка")
async def handle_button(message: Message, **data):
    """Handle button press."""
    await message.answer(_('response.text'))
```

2. Зарегистрируй router в `bot/handlers/__init__.py`:

```python
from . import твой_модуль

def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(твой_модуль.router)
```

### Добавление FSM состояния

1. Определи состояния в `bot/states/твой_модуль.py`:

```python
from aiogram.fsm.state import State, StatesGroup

class MyStates(StatesGroup):
    waiting_input = State()
    processing = State()
```

2. Используй в хендлере:

```python
from aiogram.fsm.context import FSMContext
from bot.states.твой_модуль import MyStates

@router.message(F.text == "Начать")
async def start_process(message: Message, state: FSMContext):
    await state.set_state(MyStates.waiting_input)
    await message.answer("Введите данные:")

@router.message(MyStates.waiting_input)
async def process_input(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Готово!")
```

### Работа с БД

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository

async def example(session: AsyncSession, user_id: int):
    user_repo = UserRepository(session)
    
    # Получить пользователя
    user = await user_repo.get_by_telegram_id(user_id)
    
    # Создать пользователя
    new_user = await user_repo.create({
        "telegram_id": user_id,
        "username": "example"
    })
    
    # Обновить
    await user_repo.update(user.id, {"is_active": True})
    
    # Не забыть commit!
    await session.commit()
```

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# Конкретный файл
pytest tests/test_wallet_verification.py

# С покрытием
pytest --cov=app --cov=bot tests/

# Только быстрые тесты
pytest -m "not slow"
```

### Написание теста

```python
import pytest
from app.services.wallet_verification_service import WalletVerificationService

@pytest.mark.asyncio
async def test_verify_wallet_sufficient_balance(mock_blockchain):
    """Test wallet verification with sufficient PLEX balance."""
    # Arrange
    service = WalletVerificationService(mock_blockchain)
    wallet = "0x123..."
    
    # Act
    result = await service.verify_wallet(wallet)
    
    # Assert
    assert result.is_verified
    assert result.plex_balance >= 5000
```

---

## 🐛 Отладка

### Проверка логов на сервере

```bash
# Последние 100 строк
gcloud compute ssh instance-20251107-043512 \
  --zone=europe-north1-a \
  --project=telegram-bot-444304 \
  --command="sudo docker compose -f /opt/arbitragebot/docker-compose.python.yml logs bot --tail=100"

# Следить в реальном времени
gcloud compute ssh instance-20251107-043512 \
  --zone=europe-north1-a \
  --project=telegram-bot-444304 \
  --command="sudo docker compose -f /opt/arbitragebot/docker-compose.python.yml logs bot -f"

# Логи конкретного сервиса
# bot / worker / scheduler / postgres / redis
```

### Подключение к БД на сервере

```bash
# Через Docker
gcloud compute ssh instance-20251107-043512 \
  --zone=europe-north1-a \
  --project=telegram-bot-444304 \
  --command="sudo docker exec -it arbitragebot-postgres psql -U bot -d bot"

# Примеры SQL
SELECT COUNT(*) FROM users;
SELECT * FROM users WHERE telegram_id = 1040687384;
SELECT * FROM deposits WHERE user_id = 1 ORDER BY created_at DESC LIMIT 10;
```

### Проверка Redis

```bash
gcloud compute ssh instance-20251107-043512 \
  --zone=europe-north1-a \
  --project=telegram-bot-444304 \
  --command="sudo docker exec -it arbitragebot-redis redis-cli"

# В redis-cli:
KEYS *                    # Все ключи
GET fsm:1040687384:state  # FSM состояние пользователя
TTL key_name              # Time to live
```

---

## 📊 Мониторинг

### Health Check

Бот предоставляет HTTP endpoint для проверки здоровья:

```bash
# На сервере
curl http://35.228.48.9:8080/health

# Ответ:
{
  "status": "healthy",
  "uptime": 123.45,
  "bot_id": 8506414714,
  "bot_username": "ArbitroPLEXbot"
}
```

### Метрики системы

```bash
# Использование диска
gcloud compute ssh instance-20251107-043512 \
  --zone=europe-north1-a \
  --project=telegram-bot-444304 \
  --command="df -h /"

# Память
gcloud compute ssh instance-20251107-043512 \
  --zone=europe-north1-a \
  --project=telegram-bot-444304 \
  --command="free -h"

# Docker stats
gcloud compute ssh instance-20251107-043512 \
  --zone=europe-north1-a \
  --project=telegram-bot-444304 \
  --command="sudo docker stats --no-stream"
```

---

## 🔄 Процесс разработки

### Workflow для новой фичи

1. **Создать ветку (опционально)**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Разработка**
   - Изменить код
   - Добавить/обновить тесты
   - Обновить i18n если нужно
   - Создать миграцию если нужно

3. **Тестирование локально**
   ```bash
   pytest
   python bot/main.py  # Ручная проверка
   ```

4. **Коммит**
   ```bash
   git add .
   git commit -m "feat: описание фичи"
   ```

5. **Деплой на прод**
   ```bash
   git push
   # Выполнить команду деплоя (см. выше)
   ```

6. **Проверка на проде**
   - Проверить логи
   - Проверить в Telegram
   - Мониторить ошибки

---

## 🎯 Чек-лист перед коммитом

- [ ] Код соответствует стандартам (типизация, докстроки)
- [ ] Нет хардкода кириллицы (только через i18n)
- [ ] Тесты написаны и проходят
- [ ] Миграции созданы (если изменялись модели)
- [ ] `.env` не в индексе Git
- [ ] `SERVER_INFO.md` не изменён
- [ ] Нет секретов в коде
- [ ] Логи информативные (используется loguru правильно)
- [ ] PLEX decimals = 9 (не 18!)

---

## 📚 Полезные ссылки

| Ресурс | Описание |
|--------|----------|
| [SERVER_INFO.md](./SERVER_INFO.md) | **Данные сервера (ЛОКАЛЬНО!)** |
| [aiogram docs](https://docs.aiogram.dev/) | Документация aiogram 3.x |
| [SQLAlchemy docs](https://docs.sqlalchemy.org/) | SQLAlchemy 2.0 |
| [Web3.py docs](https://web3py.readthedocs.io/) | Web3.py для BSC |
| [BSCScan API](https://docs.bscscan.com/) | BSC Explorer API |
| [Loguru docs](https://loguru.readthedocs.io/) | Библиотека логирования |

---

## 🆘 Частые проблемы

### "UNHANDLED MESSAGE" в логах

**Причина:** Нет обработчика для кнопки/команды.

**Решение:**
1. Найти текст кнопки в `bot/keyboards/reply.py`
2. Создать обработчик с `@router.message(F.text == "текст кнопки")`
3. Проверить что роутер зарегистрирован

### Кракозябры в сообщениях

**Причина:** Хардкод кириллицы вместо i18n.

**Решение:**
1. Открыть `bot/i18n/translations.py`
2. Добавить ключ перевода
3. Использовать `_('section.key')` вместо хардкода

### Миграция не применяется

**Причина:** Alembic не видит изменения моделей.

**Решение:**
1. Проверить что модель импортирована в `app/models/__init__.py`
2. Пересоздать миграцию: `alembic revision --autogenerate -m "..."`
3. Проверить файл миграции вручную
4. Применить: `alembic upgrade head`

### Docker контейнер не стартует

**Причина:** Используется неправильный docker-compose файл.

**Решение:**
```bash
# ВСЕГДА используй docker-compose.python.yml
docker compose -f docker-compose.python.yml up -d --build
```

---

## 🎓 Архитектурные решения

### Почему aiogram 3.x?

- Современный async/await подход
- FSM из коробки
- Middleware система
- Typed annotations
- Активная поддержка

### Почему SQLAlchemy 2.x async?

- Нативная поддержка async/await
- Type hints для моделей (Mapped[...])
- Улучшенная производительность
- Совместимость с asyncpg

### Почему Redis для FSM?

- Быстрый доступ к состояниям
- TTL из коробки
- Персистентность опциональна
- Масштабируемость

### Почему Docker Compose?

- Изолированные сервисы
- Воспроизводимость окружения
- Простота деплоя
- Health checks встроенные

---

## 💡 Советы для Cursor AI

### При работе с проектом помни:

1. **Всегда читай `SERVER_INFO.md`** перед работой с сервером
2. **Используй `docker-compose.python.yml`**, не обычный docker-compose.yml
3. **PLEX токен = 9 decimals**, USDT = 18 decimals
4. **Кириллица только через i18n** - `bot/i18n/translations.py`
5. **После изменения моделей** - создавай миграции
6. **Секреты в `.env`** - никогда в код
7. **Деплой** - через `gcloud compute ssh` + `git pull` + `docker compose up --build`

### Контекст проекта:

- **Домен:** Криптовалюты, DeFi, Telegram боты
- **Blockchain:** BSC (Binance Smart Chain)
- **Токены:** PLEX (9 decimals), USDT (18 decimals)
- **Бизнес-модель:** Pay-to-Use, реферальная программа, депозиты
- **Пользователи:** Криптоинвесторы, трейдеры
- **Админы:** Многоуровневая система (super_admin, senior_admin, support)

---

**Версия:** 1.0  
**Последнее обновление:** 2025-12-03  
**Автор:** Claude Sonnet 4.5 (Cursor AI)

**Проект готов к разработке! 🚀**

