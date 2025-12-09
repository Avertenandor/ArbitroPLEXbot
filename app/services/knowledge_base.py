"""Knowledge Base for ARIA AI Assistant."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from loguru import logger

KB_PATH = Path("/app/data/knowledge_base.json")
KB_PATH_LOCAL = Path("data/knowledge_base.json")


def get_kb_path() -> Path:
    if KB_PATH.parent.exists():
        return KB_PATH
    KB_PATH_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    return KB_PATH_LOCAL


DEFAULT_KB: list[dict[str, Any]] = [
    # === ОСНОВАТЕЛЬ И КОМАНДА ===
    {"id": 1, "category": "Основатель",
     "question": "Кто создатель ArbitroPLEX и монеты PLEX?",
     "answer": (
         "Александр Владарев (@VladarevInvestBrok) — создатель экосистемы "
         "монеты PLEX, проектировщик, программист, аналитик. Создал несколько "
         "десятков серьёзных криптопродуктов и несколько видов фиатного бизнеса."
     ),
     "clarification": (
         "Александр известен нетривиальными криптопродуктами: арбитражные "
         "роботы, MEV-роботы, линейка торговых роботов. Также работает над "
         "собственной DEX-биржей."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 2, "category": "Основатель",
     "question": "Что такое FreeTube?",
     "answer": (
         "FreeTube — собственный блокчейн Александра Владарева, который сейчас "
         "разрабатывается и тестируется. Он альфа-совместим с Binance Smart Chain."
     ),
     "clarification": "Это перспективный проект экосистемы PLEX.",
     "added_by": "system", "verified_by_boss": True},

    # === ЭКОСИСТЕМА PLEX ===
    {"id": 10, "category": "Экосистема PLEX",
     "question": "Что такое экосистема Монеты PLEX?",
     "answer": (
         "Экосистема построена на циркуляции утилити-токена PLEX. "
         "Выпущено немногим более 12 миллионов токенов. Мощная ежедневная "
         "циркуляция вызывает системный подъём курса."
     ),
     "clarification": (
         "Часть PLEX, которые приносят пользователи, система продаёт для "
         "поддержания резервов USDT и PLEX для бонусов, выплат и наград."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 11, "category": "Экосистема PLEX",
     "question": "Какие ещё проекты используют PLEX?",
     "answer": (
         "Кроме ArbitroPLEX существует несколько партнёрских проектов, "
         "в которых работает утилити-токен PLEX."
     ),
     "clarification": "Подробности о партнёрских проектах у @VladarevInvestBrok.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 12, "category": "Экосистема PLEX",
     "question": "Почему экономика PLEX устойчива?",
     "answer": (
         "💡 Думай как СТРАТЕГ, а не как обыватель!\n\n"
         "САМОБАЛАНСИРУЮЩАЯСЯ МОДЕЛЬ:\n"
         "1️⃣ За авторизацию и депозиты в систему постоянно поступают токены\n"
         "2️⃣ При росте цены система продаёт часть входящих токенов\n"
         "3️⃣ Трейдеры и роботы тоже продают — цена балансируется\n"
         "4️⃣ Все привыкают к предсказуемым циклам → растёт ликвидность\n\n"
         "Рост цены PLEX компенсируется входящим потоком. "
         "Твои накопления — это АКТИВ, который растёт в цене!"
     ),
     "clarification": (
         "❌ Туннельное мышление: 'PLEX дорожает = мне дороже'\n"
         "✅ Стратегическое: 'PLEX дорожает = мой актив растёт + баланс системы'"
     ),
     "added_by": "system", "verified_by_boss": True},

    # === АТОМАРНЫЙ АРБИТРАЖ ===
    {"id": 20, "category": "Арбитраж",
     "question": "Как работает атомарный арбитраж?",
     "answer": (
         "Мы работаем СТРОГО на PancakeSwap.\n"
         "У каждой монеты есть пулы ликвидности V2 и V3 с разной комиссией.\n"
         "Арбитробот в рамках ОДНОЙ атомарной транзакции:\n"
         "1. Покупает в одном пуле (V2 или V3)\n"
         "2. Продаёт в другом пуле\n"
         "3. Забирает разницу в цене\n"
         "Делаем небольшие деньги, но ОЧЕНЬ часто = набиваем огромные суммы!"
     ),
     "clarification": (
         "НЕ торгуем между разными биржами! "
         "Только разница цен между пулами V2 и V3 на PancakeSwap."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 21, "category": "Арбитраж",
     "question": "Почему нужен PLEX для арбитража?",
     "answer": (
         "Для доступа к боту и чтобы деньги зарабатывали на арбитраже, "
         "нужна Монета PLEX: 10 монет за вход + 10 монет на каждый $1 депозита."
     ),
     "clarification": (
         "Это создаёт постоянную циркуляцию монеты и поддерживает экономику."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 22, "category": "Арбитраж",
     "question": "На каких биржах работает арбитраж?",
     "answer": (
         "Работаем ТОЛЬКО на PancakeSwap!\n"
         "Используем разницу цен между пулами V2 и V3.\n"
         "НЕ торгуем между разными биржами — это другой вид арбитража."
     ),
     "clarification": "Атомарный арбитраж = всё в одной транзакции на одной DEX.",
     "added_by": "system", "verified_by_boss": True},

    # === ТОКЕН PLEX ===
    {"id": 30, "category": "PLEX токен",
     "question": "Что такое PLEX токен?",
     "answer": (
         "PLEX — утилити-токен на BNB Smart Chain (BEP-20). "
         "Всего выпущено ~12 млн токенов. Нужен для входа (10 PLEX) "
         "и для депозитов (10 PLEX за каждый $1)."
     ),
     "clarification": "Это ключ для участия в экосистеме ArbitroPLEX.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 31, "category": "PLEX токен",
     "question": "Адрес контракта PLEX?",
     "answer": "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1 (BSC/BEP-20)",
     "clarification": (
         "ТОЛЬКО сеть BSC! Другие сети = потеря токенов!\n"
         "Пул ликвидности: 0x41d9650faf3341cbf8947fd8063a1fc88dbf1889\n"
         "График: https://www.geckoterminal.com/ru/bsc/pools/0x41d9650faf3341cbf8947fd8063a1fc88dbf1889\n"
         "Купить за USDT: https://pancakeswap.finance/swap?outputCurrency=0xdf179b6cAdBC61FFD86A3D2e55f6d6e083ade6c1&inputCurrency=0x55d398326f99059fF775485246999027B3197955&chain=bsc"
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 32, "category": "PLEX токен",
     "question": "Как стабилизируется курс PLEX?",
     "answer": (
         "Курс PLEX стабилизируется САМОБАЛАНСИРУЮЩЕЙСЯ моделью:\n\n"
         "1️⃣ ВХОДЯЩИЙ ПОТОК — за авторизацию и депозиты в систему "
         "постоянно поступают токены PLEX. Это огромный объём!\n\n"
         "2️⃣ СИСТЕМА — торговый робот следит за курсом и при росте "
         "продаёт часть входящих токенов кусочками.\n\n"
         "3️⃣ ТРЕЙДЕРЫ — их роботы тоже продают при росте.\n\n"
         "4️⃣ ЦИКЛИЧНОСТЬ — все привыкают к предсказуемым колебаниям. "
         "Создаётся тяга на покупку И на продажу → ускоряется циркуляция."
     ),
     "clarification": (
         "Рост цены PLEX компенсируется входящим потоком токенов. "
         "Модель выверена на десятилетия. Думай как стратег, не как обыватель!"
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 33, "category": "PLEX токен",
     "question": "Почему модель 1:10 справедлива?",
     "answer": (
         "Модель 10 PLEX за $1 — это САМОБАЛАНСИРУЮЩАЯСЯ экономика:\n\n"
         "🔄 КОМПЕНСАЦИЯ: Рост цены → в систему входит больше $ стоимости → "
         "система продаёт часть → цена балансируется.\n\n"
         "📈 ТВОИ НАКОПЛЕНИЯ: Держишь PLEX → он растёт в цене → твой актив дорожает.\n\n"
         "🔁 ЦИРКУЛЯЦИЯ: Предсказуемые циклы → трейдеры активны → ликвидность высокая.\n\n"
         "⚖️ СПРАВЕДЛИВОСТЬ: Все участники в равных условиях, правила известны заранее."
     ),
     "clarification": (
         "Не смотри только на расходы (туннельное мышление). "
         "Смотри на ВСУЮ картину: приток → баланс → циркуляция → рост актива."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 34, "category": "PLEX токен",
     "question": "Как добавить PLEX в Trust Wallet?",
     "answer": (
         "1. Настройки > Добавить токен\n"
         "2. Сеть: Smart Chain (BNB)\n"
         "3. Вставить адрес: 0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1\n"
         "4. Сохранить"
     ),
     "clarification": "Выбирай Smart Chain, НЕ Ethereum!",
     "added_by": "system", "verified_by_boss": True},

    {"id": 35, "category": "PLEX токен",
     "question": "Как добавить PLEX в SafePal?",
     "answer": (
         "Активы > + > BSC > Вручную > вставить адрес контракта"
     ),
     "clarification": "Название и символ подтянутся автоматически.",
     "added_by": "system", "verified_by_boss": True},

    # === ДЕПОЗИТЫ ===
    {"id": 40, "category": "Депозиты",
     "question": "Как сделать депозит?",
     "answer": (
         "1. Убедись что есть PLEX (10 за вход + 10 за каждый $1)\n"
         "2. Депозит > выбери сумму\n"
         "3. Отправь USDT на указанный адрес (сеть BSC/BEP-20)\n"
         "4. ОБЯЗАТЕЛЬНО нажми кнопку «Я ОПЛАТИЛ» после отправки!\n"
         "5. Жди подтверждения (1-5 мин)"
     ),
     "clarification": (
         "USDT вносится ОДИН РАЗ как оборотные средства. "
         "А вот PLEX надо вносить КАЖДЫЕ СУТКИ (10 монет за $1 депозита)! "
         "⚠️ Без нажатия «Я ОПЛАТИЛ» депозит не зачислится!"
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 41, "category": "Депозиты",
     "question": "Какие уровни депозитов существуют?",
     "answer": (
         "📊 УРОВНИ ДЕПОЗИТОВ:\n"
         "• Тестовый: $30-$100 (временно, будет закрыт после тестирования)\n"
         "• Уровень 1: $100-$500\n"
         "• Уровень 2: $700-$1200\n"
         "• Уровень 3: $1400-$2200\n"
         "• Уровень 4: $2500-$3500\n"
         "• Уровень 5: $4000-$7000"
     ),
     "clarification": (
         "Каждый пользователь начинает с тестового депозита. "
         "Нельзя открыть уровень без предыдущего. "
         "Один и тот же уровень нельзя открыть дважды."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 42, "category": "Депозиты",
     "question": "Какой минимальный депозит?",
     "answer": (
         "Сейчас (тестовый период): минимум $30.\n"
         "После тестов: минимум $100 (1-й уровень).\n"
         "Тестовый уровень будет закрыт после завершения тестирования."
     ),
     "clarification": "Каждый начинает с тестового депозита, потом переходит на уровень 1.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 43, "category": "Депозиты",
     "question": "Как работает ежедневная оплата PLEX?",
     "answer": (
         "USDT вносится ОДИН РАЗ как оборотные средства.\n"
         "PLEX нужно вносить КАЖДЫЕ СУТКИ:\n"
         "• 10 PLEX за каждый $1 депозита\n"
         "• Например: депозит $100 = 1000 PLEX в сутки\n"
         "⚠️ ВАЖНО: Без оплаты PLEX депозит НЕ участвует в арбитраже!"
     ),
     "clarification": "Это поддерживает экономику токена и обеспечивает работу системы.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 45, "category": "Депозиты",
     "question": "Что будет если пропустить оплату PLEX?",
     "answer": (
         "⚠️ КРИТИЧЕСКИ ВАЖНО понимать последствия!\n\n"
         "При пропуске оплаты PLEX:\n"
         "❌ Пользователь ВЫБРАСЫВАЕТСЯ из системы\n"
         "❌ ПРОГРЕСС депозита СБРАСЫВАЕТСЯ В НОЛЬ\n"
         "❌ Придётся начинать ВСЁ СНАЧАЛА\n"
         "❌ Несколько месяцев потребуется чтобы вернуться на прежний уровень доходности\n\n"
         "USDT-депозит при этом НЕ теряется физически, но:\n"
         "• Вся накопленная статистика обнуляется\n"
         "• Уровень доходности сбрасывается\n"
         "• Нужно заново проходить путь развития депозита"
     ),
     "clarification": (
         "Это НЕ просто 'пауза' — это полный сброс прогресса! "
         "Не пропускай оплату PLEX если не хочешь потерять месяцы работы."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 46, "category": "Депозиты",
     "question": "Депозит 'спит' без PLEX или сбрасывается?",
     "answer": (
         "❌ НЕТ, депозит НЕ 'спит' и не ждёт!\n\n"
         "При пропуске оплаты PLEX:\n"
         "• Пользователь исключается из системы\n"
         "• Весь прогресс депозита ОБНУЛЯЕТСЯ\n"
         "• Для возврата придётся начинать с нуля\n"
         "• Месяцы работы будут потеряны\n\n"
         "Это НЕ как 'машина в гараже без бензина'!\n"
         "Это как машина, которую КОНФИСКУЮТ и потом надо заново копить на новую."
     ),
     "clarification": (
         "Аналогия с 'машиной и бензином' НЕПРАВИЛЬНАЯ! "
         "Правильная аналогия: арендуешь машину — не платишь аренду — машину забирают."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 44, "category": "Депозиты",
     "question": "Депозит не пришёл, что делать?",
     "answer": (
         "1. Проверь hash на bscscan.com\n"
         "2. Убедись что отправил по сети BSC (BEP-20)\n"
         "3. Подожди 15 минут\n"
         "4. Пиши в поддержку с hash"
     ),
     "clarification": "Частая ошибка: ERC-20 или TRC-20 вместо BSC = потеря средств!",
     "added_by": "system", "verified_by_boss": True},

    # === ВЫВОДЫ ===
    {"id": 50, "category": "Выводы",
     "question": "Как вывести деньги?",
     "answer": (
         "Вывод > сумма > адрес USDT (сеть BSC/BEP-20) > подтвердить.\n"
         "• Минимум: $0.50 (50 центов)\n"
         "• Максимум: без ограничений\n"
         "Выводы работают автоматически."
     ),
     "clarification": "ВАЖНО: Указывай адрес ТОЛЬКО в сети BSC (BNB Smart Chain)!",
     "added_by": "system", "verified_by_boss": True},

    {"id": 51, "category": "Выводы",
     "question": "Почему вывод задерживается?",
     "answer": (
         "Система безопасности может приостановить вывод на 24 часа:\n"
         "• При подозрительной активности\n"
         "• Для проверки живым администратором\n"
         "• Выводы < $10 проверяет AI-специалист\n"
         "Это защита от мошенничества."
     ),
     "clarification": "Если вывод задерживается дольше 24ч — обратись в поддержку.",
     "added_by": "system", "verified_by_boss": True},

    # === НЕЗГОРАЕМЫЙ ОСТАТОК PLEX ===
    {"id": 55, "category": "PLEX токен",
     "question": "Что такое незгораемый остаток PLEX?",
     "answer": (
         "Минимальное количество PLEX, которое ВСЕГДА должно быть на кошельке:\n"
         "• Уровень 1: 5,000 PLEX\n"
         "• Уровень 2: 10,000 PLEX\n"
         "• Уровень 3: 15,000 PLEX\n"
         "• Уровень 4: 25,000 PLEX\n"
         "• Уровень 5: 40,000 PLEX\n"
         "Сверх этого — можете использовать свободно."
     ),
     "clarification": "Это гарантийный запас для стабильности системы.",
     "added_by": "system", "verified_by_boss": True},

    # === СЕССИЯ И ТАЙМАУТЫ ===
    {"id": 56, "category": "Система",
     "question": "Сколько длится рабочая сессия?",
     "answer": (
         "Рабочая сессия: 25 минут.\n"
         "При бездействии система сбрасывает сессию.\n"
         "Для продолжения работы:\n"
         "1. Нажать /start\n"
         "2. Авторизоваться заново\n"
         "3. Оплатить 10 PLEX за авторизацию\n\n"
         "Это НЕ баг — это нормальная работа системы!"
     ),
     "clarification": (
         "Каждая авторизация стоит 10 PLEX. "
         "Так работает экономика платформы: плати PLEX = работай в системе."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 56.1, "category": "Система",
     "question": "Почему сессия истекла? Это баг?",
     "answer": (
         "НЕТ, это НЕ баг! Это нормальная работа системы.\n\n"
         "Сессия истекает через 25 минут бездействия.\n"
         "Для продолжения нужно:\n"
         "1. Нажать /start\n"
         "2. Авторизоваться заново\n"
         "3. Оплатить 10 PLEX\n\n"
         "Так устроена экономика — каждая авторизация платная."
     ),
     "clarification": "Не путать с багом! Это часть экономической модели.",
     "added_by": "system", "verified_by_boss": True},

    # === КРОЛИКИ И DEX RABBIT ===
    {"id": 57, "category": "Кролики DEX Rabbit",
     "question": "Что такое кролики и зачем они нужны?",
     "answer": (
         "🐰 DEX Rabbit — партнёрский проект (кроличья ферма).\n"
         "После тестового периода для работы с ArbitroPLEX нужны кролики:\n"
         "• Уровень 1: 1 кролик\n"
         "• Уровень 2: 3 кролика\n"
         "• Уровень 3: 5 кроликов\n"
         "• Уровень 4: 10 кроликов\n"
         "• Уровень 5: 15 кроликов\n"
         "У нас единая база данных — система сразу видит ваших кроликов."
     ),
     "clarification": (
         "Сайт: https://кроличьяферма.site/\n"
         "Telegram: https://t.me/dexrabbit_bot?start=ref_9"
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 58, "category": "Кролики DEX Rabbit",
     "question": "Зачем покупать кроликов?",
     "answer": (
         "Преимущества владения кроликами:\n"
         "1. Кролики производят новых кроликов\n"
         "2. Новые кролики продаются по рыночной цене\n"
         "3. Пока работаешь в арбитроботе — зарабатываешь\n"
         "4. Параллельно зарабатываешь на кроликах\n"
         "5. Кролики нужны КАЖДОМУ участнику = постоянный спрос\n"
         "6. Кролики растут и растут в цене"
     ),
     "clarification": "Это дополнительный источник дохода помимо арбитража!",
     "added_by": "system", "verified_by_boss": True},

    # === СХЕМА НАЧИСЛЕНИЯ ДОХОДА ===
    {"id": 59, "category": "ROI и доход",
     "question": "Как растёт процент дохода по неделям?",
     "answer": (
         "📈 Схема начисления дохода от заработка бота:\n"
         "• 1 неделя: 0.5% в сутки\n"
         "• 2 неделя: 2% в сутки\n"
         "• 3 неделя: 4% в сутки\n"
         "• 4 неделя: 12% в сутки\n"
         "• 5+ неделя: +4% каждую неделю до максимума\n"
         "Проценты указаны ЗА ВЫЧЕТОМ реферальных отчислений."
     ),
     "clarification": (
         "Ты видишь сколько бот заработал (100%), "
         "и получаешь свою долю по схеме выше."
     ),
     "added_by": "system", "verified_by_boss": True},

    # === ROI ===
    {"id": 60, "category": "ROI и доход",
     "question": "Как начисляется ROI?",
     "answer": (
         "ROI начисляется автоматически каждый день на активные депозиты. "
         "Прибыль падает на ваш баланс, НЕ на депозит. "
         "Доходность зависит от недели работы и условий арбитража."
     ),
     "clarification": "Прибыль можно вывести или сделать новый депозит.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 61, "category": "ROI и доход",
     "question": "Есть ли реинвест?",
     "answer": (
         "НЕТ, функции реинвеста не существует! "
         "Каждый депозит — это отдельный уровень с отдельными условиями. "
         "Прибыль начисляется на баланс, а не добавляется к депозиту."
     ),
     "clarification": (
         "Чтобы увеличить рабочую сумму — нужно сделать НОВЫЙ депозит. "
         "Для нового депозита нужны новые PLEX токены."
     ),
     "added_by": "system", "verified_by_boss": True},

    # === ПРАВИЛА PLEX ===
    {"id": 62, "category": "PLEX токен",
     "question": "Можно ли продать или перевести PLEX?",
     "answer": (
         "⛔ НЕЛЬЗЯ! Монеты PLEX нельзя никуда девать с кошелька!\n"
         "• Продал/перевёл PLEX = система отключает от арбитробота\n"
         "• Операционные деньги (USDT) будут возвращены\n"
         "• На кошельке НЕ МОЖЕТ быть PLEX меньше минимума\n"
         "• Сумму депозита менять нельзя"
     ),
     "clarification": (
         "Заработанную прибыль можно вывести. "
         "Остальные суммы продолжают работать."
     ),
     "added_by": "system", "verified_by_boss": True},

    # === РЕФЕРАЛЬНАЯ ПРОГРАММА ===
    {"id": 70, "category": "Реферальная программа",
     "question": "Сколько уровней в реферальной программе?",
     "answer": (
         "В реферальной программе 3 уровня (НЕ 5!):\n"
         "• 1 уровень: 5% от депозитов и дохода прямых рефералов\n"
         "• 2 уровень: 5% от рефералов твоих рефералов\n"
         "• 3 уровень: 5% от рефералов 3-го уровня"
     ),
     "clarification": "Бонусы начисляются автоматически на баланс.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 71, "category": "Реферальная программа",
     "question": "Как работает реферальная программа?",
     "answer": (
         "Ты получаешь 5% от депозитов И от заработка рефералов на 3 уровнях:\n"
         "1. Пригласи друга по своей ссылке\n"
         "2. Когда он делает депозит — ты получаешь 5%\n"
         "3. Когда он зарабатывает ROI — ты тоже получаешь 5%\n"
         "И так на 3 уровня вглубь!"
     ),
     "clarification": "Ссылку найдёшь в разделе Рефералы в главном меню.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 72, "category": "Реферальная программа",
     "question": "Где найти реферальную ссылку?",
     "answer": (
         "Главное меню → 👥 Рефералы → 🔗 Моя ссылка.\n"
         "Копируй и отправляй друзьям!"
     ),
     "clarification": "Ссылка уникальная и привязана к твоему аккаунту.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 73, "category": "Реферальная программа",
     "question": "Есть ли 5 уровней рефералов?",
     "answer": (
         "НЕТ! Только 3 уровня рефералов.\n"
         "Это НЕ 5 уровней! Кто говорит про 5 — ошибается."
     ),
     "clarification": "3 уровня по 5% = до 15% пассивного дохода с команды.",
     "added_by": "system", "verified_by_boss": True},

    # === БОНУСЫ (ТОЛЬКО ДЛЯ АДМИНОВ) ===
    {"id": 80, "category": "Админ: Бонусы",
     "question": "Как начислить бонус пользователю?",
     "answer": (
         "⚠️ ТОЛЬКО ДЛЯ АДМИНОВ!\n\n"
         "Путь: 👑 Админ-панель → 🎁 Бонусы → ➕ Начислить бонус\n\n"
         "1. Введите @username или Telegram ID пользователя\n"
         "2. Укажите сумму бонуса в USDT\n"
         "3. Напишите причину начисления\n"
         "4. Подтвердите начисление"
     ),
     "clarification": (
         "Бонус = виртуальный депозит с ROI Cap 500%. "
         "Права: super_admin, extended_admin, admin могут начислять. "
         "Moderator — только просмотр."
     ),
     "added_by": "system", "verified_by_boss": True, "admin_only": True},

    {"id": 81, "category": "Админ: Бонусы",
     "question": "Что такое бонусный депозит?",
     "answer": (
         "⚠️ ИНФО ДЛЯ АДМИНОВ!\n\n"
         "Бонусный депозит — это виртуальный депозит, который:\n"
         "• Начисляется админом вручную\n"
         "• Участвует в начислении ROI как обычный депозит\n"
         "• Имеет ROI Cap 500% (как обычный депозит)\n"
         "• НЕ требует реальных USDT или PLEX\n\n"
         "Используется для: компенсаций, акций, поощрений."
     ),
     "clarification": "Бонус не увеличивает реальный баланс напрямую.",
     "added_by": "system", "verified_by_boss": True, "admin_only": True},

    {"id": 82, "category": "Админ: Бонусы",
     "question": "Кто может начислять бонусы?",
     "answer": (
         "⚠️ ТОЛЬКО ДЛЯ АДМИНОВ!\n\n"
         "Права на начисление бонусов:\n"
         "• 👑 super_admin (Босс) — полный доступ\n"
         "• ⭐ extended_admin — полный доступ\n"
         "• 👤 admin — полный доступ\n"
         "• 👁 moderator — только просмотр истории"
     ),
     "clarification": "Модераторы не могут начислять, только смотреть.",
     "added_by": "system", "verified_by_boss": True, "admin_only": True},

    {"id": 83, "category": "Админ: Бонусы",
     "question": "Где посмотреть историю бонусов?",
     "answer": (
         "⚠️ ТОЛЬКО ДЛЯ АДМИНОВ!\n\n"
         "Путь: 👑 Админ-панель → 🎁 Бонусы → 📋 История бонусов\n\n"
         "Показывает последние 15 начислений с информацией:\n"
         "• Сумма и получатель\n"
         "• Причина начисления\n"
         "• Кто начислил"
     ),
     "clarification": "Также можно искать бонусы конкретного пользователя.",
     "added_by": "system", "verified_by_boss": True, "admin_only": True},

    # === БОНУСЫ (ДЛЯ ПОЛЬЗОВАТЕЛЕЙ) ===
    {"id": 84, "category": "Бонусы",
     "question": "Что такое бонусный баланс?",
     "answer": (
         "Бонусный баланс — это виртуальный депозит, который начисляет администрация.\n\n"
         "• Участвует в начислении ROI как обычный депозит\n"
         "• Имеет ROI Cap 500%\n"
         "• Не требует покупки PLEX\n"
         "• Отображается отдельной строкой в профиле и балансе"
     ),
     "clarification": "Бонусы начисляются за акции, компенсации, конкурсы.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 85, "category": "Бонусы",
     "question": "Где посмотреть свой бонусный баланс?",
     "answer": (
         "Бонусный баланс отображается в:\n"
         "• 👤 Мой профиль — раздел 🎁 Бонусы\n"
         "• 📊 Баланс — если есть бонусы\n"
         "• 💰 Мои средства — строка 'Бонусный баланс'"
     ),
     "clarification": "Если бонусов нет — раздел не отображается.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 86, "category": "Бонусы",
     "question": "Как получить бонус?",
     "answer": (
         "Бонусы начисляет администрация за:\n"
         "• Участие в акциях и конкурсах\n"
         "• Компенсации при технических проблемах\n"
         "• Особые заслуги и активность\n\n"
         "Самому себе начислить бонус нельзя."
     ),
     "clarification": "Следите за новостями в канале для участия в акциях.",
     "added_by": "system", "verified_by_boss": True},

    # === PLEX АНАЛИТИКА (ТОЛЬКО ДЛЯ АДМИНОВ) ===
    {"id": 90, "category": "Админ: PLEX",
     "question": "Где посмотреть статистику PLEX-платежей?",
     "answer": (
         "⚠️ ТОЛЬКО ДЛЯ АДМИНОВ!\n\n"
         "PLEX-транзакции хранятся в таблице plex_payment_requirements.\n"
         "Для анализа используйте:\n"
         "• Логи сервера (docker logs)\n"
         "• Прямые SQL-запросы к БД\n"
         "• Блокчейн-эксплорер BscScan\n\n"
         "В боте пока нет раздела 'PLEX Analytics'."
     ),
     "clarification": "Это планируется к добавлению.",
     "added_by": "system", "verified_by_boss": True, "admin_only": True},

    {"id": 91, "category": "Админ: PLEX",
     "question": "Как проверить PLEX-баланс пользователя?",
     "answer": (
         "⚠️ ТОЛЬКО ДЛЯ АДМИНОВ!\n\n"
         "Способы проверки PLEX:\n"
         "1. В профиле пользователя (админка → Пользователи → Профиль)\n"
         "2. Через BscScan по адресу кошелька\n"
         "3. Логи plex_balance_monitor в docker logs"
     ),
     "clarification": "Контракт PLEX: 0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1",
     "added_by": "system", "verified_by_boss": True, "admin_only": True},

    {"id": 92, "category": "Админ: PLEX",
     "question": "Где логи платежей за вход (10 PLEX)?",
     "answer": (
         "⚠️ ТОЛЬКО ДЛЯ АДМИНОВ!\n\n"
         "Платежи за вход (10 PLEX) логируются:\n"
         "• В docker logs arbitragebot-bot (поиск 'auth payment')\n"
         "• В таблице users (поле is_verified)\n"
         "• В blockchain (BscScan по адресу)\n\n"
         "Отдельной таблицы входных платежей нет."
     ),
     "clarification": "Вход подтверждается через blockchain верификацию баланса.",
     "added_by": "system", "verified_by_boss": True, "admin_only": True},

    # === АНАЛИТИКА АКТИВНОСТИ (ТОЛЬКО ДЛЯ АДМИНОВ) ===
    {"id": 95, "category": "Админ: Аналитика",
     "question": "Как посмотреть все действия пользователя?",
     "answer": (
         "⚠️ ТОЛЬКО ДЛЯ АДМИНОВ!\n\n"
         "Все действия пользователей логируются в таблице user_activities.\n"
         "Через меня (ARIA) ты можешь запросить:\n"
         "• Воронку регистрации за период\n"
         "• Сколько нажали /start\n"
         "• Сколько ввели кошелёк\n"
         "• Сколько оплатили PLEX\n"
         "• Полную историю действий юзера"
     ),
     "clarification": "Спроси: 'покажи воронку за 24 часа' или 'действия юзера @username'",
     "added_by": "system", "verified_by_boss": True, "admin_only": True},

    {"id": 96, "category": "Админ: Аналитика",
     "question": "Какие действия логируются?",
     "answer": (
         "⚠️ ТОЛЬКО ДЛЯ АДМИНОВ!\n\n"
         "Логируются ВСЕ действия:\n"
         "• /start (обычный и реферальный)\n"
         "• Ввод кошелька, оплата PLEX\n"
         "• Все сообщения и нажатия кнопок\n"
         "• Депозиты, выводы\n"
         "• Обращения в поддержку\n"
         "• Вопросы к AI (ко мне)\n"
         "• Ошибки пользователей"
     ),
     "clarification": "Данные хранятся 30 дней, затем автоочистка.",
     "added_by": "system", "verified_by_boss": True, "admin_only": True},

    {"id": 97, "category": "Админ: Аналитика",
     "question": "Покажи воронку регистрации",
     "answer": (
         "⚠️ ТОЛЬКО ДЛЯ АДМИНОВ!\n\n"
         "Воронка регистрации показывает конверсию:\n"
         "1. Нажали /start → N человек\n"
         "2. Ввели кошелёк → N человек (X%)\n"
         "3. Оплатили PLEX → N человек (X%)\n"
         "4. Сделали депозит → N человек (X%)\n\n"
         "Спроси меня: 'воронка за 24ч' или 'воронка за неделю'"
     ),
     "clarification": "Я покажу данные из таблицы user_activities.",
     "added_by": "system", "verified_by_boss": True, "admin_only": True},

    {"id": 98, "category": "Админ: Аналитика",
     "question": "Кто со мной разговаривал? О чём спрашивали?",
     "answer": (
         "⚠️ ТОЛЬКО ДЛЯ АДМИНОВ!\n\n"
         "Все разговоры со мной логируются!\n"
         "Я могу показать:\n"
         "• Кто и когда со мной общался\n"
         "• Какие вопросы задавали\n"
         "• Краткое содержание ответов\n\n"
         "Спроси: 'покажи разговоры за 24ч' или 'о чём спрашивали?'"
     ),
     "clarification": "Логируются вопросы и ответы всех админов.",
     "added_by": "system", "verified_by_boss": True, "admin_only": True},
]


class KnowledgeBase:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        kb_path = get_kb_path()
        try:
            if kb_path.exists():
                with open(kb_path, encoding="utf-8") as f:
                    self.entries = json.load(f)
            else:
                self.entries = DEFAULT_KB.copy()
                self.save()
        except Exception as e:
            logger.error(f"KB load error: {e}")
            self.entries = DEFAULT_KB.copy()

    def save(self) -> None:
        try:
            kb_path = get_kb_path()
            kb_path.parent.mkdir(parents=True, exist_ok=True)
            with open(kb_path, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"KB save error: {e}")

    def get_next_id(self) -> int:
        return max((e.get("id", 0) for e in self.entries), default=0) + 1

    def add_entry(self, question: str, answer: str, category: str = "Общее",
                  clarification: str = "", added_by: str = "admin") -> dict:
        entry = {
            "id": self.get_next_id(), "category": category,
            "question": question, "answer": answer,
            "clarification": clarification, "added_by": added_by,
            "added_at": datetime.now(UTC).isoformat(),
            "verified_by_boss": False
        }
        self.entries.append(entry)
        self.save()
        return entry

    def update_entry(self, entry_id: int, **kwargs) -> dict | None:
        for entry in self.entries:
            if entry.get("id") == entry_id:
                for k, v in kwargs.items():
                    if v is not None and k in entry:
                        entry[k] = v
                entry["verified_by_boss"] = False
                self.save()
                return entry
        return None

    def verify_entry(self, entry_id: int) -> bool:
        for entry in self.entries:
            if entry.get("id") == entry_id:
                entry["verified_by_boss"] = True
                self.save()
                return True
        return False

    def delete_entry(self, entry_id: int) -> bool:
        for i, e in enumerate(self.entries):
            if e.get("id") == entry_id:
                del self.entries[i]
                self.save()
                return True
        return False

    def search(self, query: str) -> list[dict]:
        q = query.lower()
        return [e for e in self.entries if q in str(e).lower()]

    def get_categories(self) -> list[str]:
        return sorted(set(e.get("category", "") for e in self.entries))

    def get_unverified(self) -> list[dict]:
        return [e for e in self.entries if not e.get("verified_by_boss")]

    def format_for_ai(self) -> str:
        lines = ["=== БАЗА ЗНАНИЙ ===", "Источник: @VladarevInvestBrok", ""]
        for cat in self.get_categories():
            lines.append(f"[{cat}]")
            for e in self.entries:
                if e.get("category") == cat:
                    v = "+" if e.get("verified_by_boss") else "?"
                    lines.append(f"{v} В: {e['question']}")
                    lines.append(f"  О: {e['answer']}")
                    if c := e.get("clarification"):
                        lines.append(f"  ! {c}")
            lines.append("")
        return "\n".join(lines)

    def add_learned_entry(
        self,
        question: str,
        answer: str,
        category: str = "Из диалогов",
        source_user: str = "unknown",
        needs_verification: bool = True,
    ) -> dict:
        """Add entry learned from conversation with admin/boss."""
        entry = {
            "id": self.get_next_id(),
            "category": category,
            "question": question,
            "answer": answer,
            "clarification": f"Извлечено из диалога с @{source_user}",
            "added_by": "ARIA",
            "added_at": datetime.now(UTC).isoformat(),
            "verified_by_boss": not needs_verification,
            "learned_from_dialog": True,
            "source_user": source_user,
        }
        self.entries.append(entry)
        self.save()
        logger.info(f"ARIA learned: {question[:50]}... from @{source_user}")
        return entry

    def get_learned_entries(self) -> list[dict]:
        """Get entries that were learned from dialogs."""
        return [e for e in self.entries if e.get("learned_from_dialog")]

    def get_pending_verification(self) -> list[dict]:
        """Get entries pending boss verification."""
        return [
            e for e in self.entries
            if e.get("learned_from_dialog") and not e.get("verified_by_boss")
        ]


_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
