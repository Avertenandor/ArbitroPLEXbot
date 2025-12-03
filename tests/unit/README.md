# Unit Tests for Critical Financial Functions

Comprehensive unit tests для критических финансовых функций ArbitroPLEXbot.

## Структура тестов

### 1. test_validation.py - Тесты валидации
**Покрытие:** Валидация BSC адресов, USDT сумм, transaction hash, Telegram username, sanitization

**Ключевые тесты:**
- **BSC Address Validation**
  - ✅ Пустой адрес (invalid)
  - ✅ Короткий адрес (invalid)
  - ✅ Адрес без 0x префикса (invalid)
  - ✅ Валидный формат адреса
  - ✅ Невалидные hex символы
  - ✅ Слишком длинный адрес
  - ✅ Параметризованные тесты валидных адресов

**Edge Cases:**
- Null/None значения
- Неправильный тип данных
- Граничные значения длины
- Специальные символы
- Burn адрес (0x000...000)
- Max адрес (0xFFF...FFF)

---

### 2. test_encryption.py - Тесты шифрования
**Покрытие:** Encryption/Decryption, Key generation, Error handling

**Ключевые тесты:**
- **Encryption Service**
  - ✅ Encrypt/Decrypt roundtrip - данные корректно шифруются и расшифровываются
  - ✅ Different outputs - один и тот же текст дает разные ciphertext (из-за random IV)
  - ✅ Both decrypt - оба варианта шифрования расшифровываются в оригинал
  - ✅ Empty string - пустая строка корректно шифруется
  - ✅ Unicode - Unicode символы (Cyrillic, Chinese, Emoji) корректно обрабатываются
  - ✅ Invalid data - невалидные данные возвращают None вместо exception

**Edge Cases:**
- Пустые строки
- Unicode/Emoji
- Невалидные encrypted data
- Отсутствие ключа (disabled mode)
- Разные ключи (должно вернуть None)

**Security:**
- Использует Fernet (symmetric encryption)
- Random IV для каждого шифрования
- Base64 encoding результатов

---

### 3. test_reward_calculation.py - Тесты расчёта наград
**Покрытие:** Reward calculation, ROI cap, ROI progress, x5 rule

**Ключевые тесты:**

#### A. Reward Amount Calculation
- ✅ **Базовый расчёт:** (1000 * 1.117 * 1) / 100 = 11.17
- ✅ **Множественные дни:** Корректный расчёт для нескольких дней
- ✅ **Zero rate:** Ставка 0% возвращает 0
- ✅ **Zero amount:** Депозит 0 возвращает 0
- ✅ **Negative values:** Отрицательные значения возвращают 0
- ✅ **High rate:** Большие ставки (10%) корректно обрабатываются
- ✅ **Low rate:** Малые ставки (0.01%) корректно обрабатываются
- ✅ **Precision:** Decimal precision сохраняется

#### B. ROI Cap Calculation
- ✅ **500% cap:** 1000 * 500% = 5000
- ✅ **100% cap:** 1000 * 100% = 1000
- ✅ **Zero multiplier:** Корректная обработка
- ✅ **Large amounts:** Большие суммы обрабатываются корректно
- ✅ **Decimal amounts:** 1000.50 * 500% = 5002.50

#### C. Remaining ROI Calculation
- ✅ **No payments:** Остаток = ROI cap
- ✅ **Partial payment:** Остаток = cap - paid (50% оплачено = 50% остаток)
- ✅ **Almost complete:** Остаток = 1 USDT
- ✅ **Complete:** Остаток = 0
- ✅ **Exceeded:** Не может быть отрицательным (min 0)
- ✅ **Override:** total_earned parameter работает корректно

#### D. ROI Cap Reached Detection
- ✅ **Not reached:** 50% оплачено -> False
- ✅ **Exactly reached:** 100% оплачено -> True
- ✅ **Exceeded:** 120% оплачено -> True
- ✅ **Just under:** 99.99% оплачено -> False

#### E. Cap Reward to Remaining ROI
- ✅ **Within limit:** Награда в пределах лимита не изменяется
- ✅ **Exceeds limit:** Награда обрезается до remaining ROI
- ✅ **Exactly fills:** Награда точно заполняет cap
- ✅ **Cap reached:** Если cap достигнут, возвращает 0
- ✅ **Very small remaining:** Малый остаток обрабатывается корректно

#### F. ROI Progress Calculation
- ✅ **0% progress:** roi_paid = 0
- ✅ **50% progress:** roi_paid = 2500 из 5000
- ✅ **100% progress:** roi_paid = 5000
- ✅ **Over 100%:** Должно cap на 100%
- ✅ **Decimal precision:** 2345.67 / 5000 = 46.9134%

#### G. Withdrawal x5 Rule
**Правило:** (total_withdrawn + request) <= (total_deposited * 5)

- ✅ **Within limit:** Первый вывод в пределах лимита
- ✅ **Exactly at limit:** Вывод точно до лимита x5
- ✅ **Exceeds limit:** Вывод превышает x5 -> False
- ✅ **Just over:** Вывод на 1 USDT больше лимита -> False
- ✅ **No deposits:** Без депозитов выводы запрещены
- ✅ **Multiple withdrawals:** Сумма многих выводов проверяется
- ✅ **Decimal deposits:** 100.50 * 5 = 502.50
- ✅ **Large amounts:** 100000 * 5 = 500000

---

### 4. test_financial_validation.py - Тесты финансовой валидации
**Покрытие:** Deposit levels, Partner requirements, Withdrawal validation, Balance checks

**Ключевые тесты:**

#### A. Deposit Level Configuration
- ✅ **All levels defined:** Уровни 1-5 определены
- ✅ **Positive amounts:** Все суммы положительные
- ✅ **Ascending order:** 10 < 50 < 100 < 150 < 300
- ✅ **Specific amounts:** Level 1=10, Level 2=50, Level 3=100, Level 4=150, Level 5=300

#### B. Partner Requirements
- ✅ **All defined:** Требования для уровней 1-5
- ✅ **Non-negative:** Все требования >= 0
- ✅ **Level 1 no partners:** Level 1 не требует партнёров

#### C. Withdrawal Minimum Amount
- ✅ **Above minimum:** 10 >= 1 -> valid
- ✅ **Exactly at minimum:** 1 >= 1 -> valid
- ✅ **Below minimum:** 0.99 < 1 -> invalid
- ✅ **Zero:** 0 < 1 -> invalid
- ✅ **Negative:** -10 < 1 -> invalid

#### D. Withdrawal Balance Check
- ✅ **Sufficient balance:** 100 >= 50 -> valid
- ✅ **Exact balance:** 100 >= 100 -> valid
- ✅ **Insufficient:** 100 < 150 -> invalid
- ✅ **Zero balance:** 0 < 10 -> invalid
- ✅ **Negative balance:** -10 < 10 -> invalid
- ✅ **Very small difference:** 100.00 < 100.01 -> invalid

#### E. X5 Withdrawal Rule (Detailed)
- ✅ **First withdrawal:** 0 + 1000 <= 5000 -> valid
- ✅ **Exactly at limit:** 4000 + 1000 = 5000 -> valid
- ✅ **Exceeds limit:** 4500 + 600 > 5000 -> invalid
- ✅ **Just over:** 4999 + 2 > 5000 -> invalid
- ✅ **No deposits:** 0 deposits -> no withdrawals
- ✅ **Multiple small:** Накопительный эффект множества выводов
- ✅ **Decimal precision:** 100.50 * 5 = 502.50

#### F. Global Daily Limit
- ✅ **Within limit:** 5000 + 3000 <= 10000 -> valid
- ✅ **Exactly at limit:** 7000 + 3000 = 10000 -> valid
- ✅ **Exceeds limit:** 8000 + 3000 > 10000 -> invalid
- ✅ **First withdrawal:** 0 + 5000 <= 10000 -> valid

#### G. ROI Cap Boundaries
- ✅ **At 500%:** 1000 * 5 = 5000
- ✅ **Just under cap:** 4999.99 < 5000 -> not complete
- ✅ **Exactly at cap:** 5000 >= 5000 -> complete
- ✅ **Over cap:** 5000.01 > 5000 -> complete
- ✅ **Remaining calculation:** 5000 - 3000 = 2000
- ✅ **Negative remaining -> 0:** max(5000 - 6000, 0) = 0

#### H. Decimal Precision
- ✅ **Addition:** 100.12 + 50.34 = 150.46
- ✅ **Subtraction:** 100.12 - 50.34 = 49.78
- ✅ **Multiplication:** 100.12 * 1.5 = 150.180
- ✅ **Division:** 100 / 3 = 33.33333...
- ✅ **Comparison:** 100.000001 < 100.000002
- ✅ **Rounding:** 100.12345 -> 100.12 (2 decimals)

#### I. Negative Amount Handling
- ✅ **Negative deposit:** -100 <= 0 -> invalid
- ✅ **Negative withdrawal:** -50 <= 0 -> invalid
- ✅ **Negative balance:** balance < 0 -> detected
- ✅ **Zero not negative:** 0 is not < 0

#### J. Boundary Conditions
- ✅ **Min USDT unit:** 0.01 USDT
- ✅ **Large amounts:** 1000000 * 0.01 = 10000
- ✅ **Very small:** 0.000001 обрабатывается
- ✅ **Integer amounts:** 100 == 100.00

---

## Покрытие Edge Cases

### ✅ Финансовые расчёты:
- Отрицательные значения
- Нулевые значения
- Граничные значения (min/max)
- Decimal precision
- Округление
- Очень большие суммы
- Очень малые суммы
- Division by zero protection

### ✅ Валидация данных:
- Пустые строки
- Null/None
- Неправильные типы данных
- Невалидные форматы
- Граничные длины
- Специальные символы
- Unicode/Emoji

### ✅ Безопасность:
- Encryption/Decryption roundtrip
- Random IV
- Invalid key handling
- Disabled encryption mode
- Wrong key detection

### ✅ Business Logic:
- ROI cap 500%
- x5 withdrawal rule
- Partner requirements
- Deposit level order
- Daily limits
- Balance checks
- Minimum amounts

---

## Запуск тестов

### Все unit тесты:
```bash
python -m pytest tests/unit/ -v
```

### Конкретные модули:
```bash
# Тесты валидации
python -m pytest tests/unit/test_validation.py -v

# Тесты шифрования
python -m pytest tests/unit/test_encryption.py -v

# Тесты расчёта наград
python -m pytest tests/unit/test_reward_calculation.py -v

# Тесты финансовой валидации
python -m pytest tests/unit/test_financial_validation.py -v
```

### С покрытием кода:
```bash
python -m pytest tests/unit/ --cov=app --cov-report=html
```

### С подробным выводом:
```bash
python -m pytest tests/unit/ -vv --tb=short
```

---

## Статистика

### test_validation.py
- **Тестов:** 9
- **Классы:** TestBSCAddressValidation
- **Покрытие:** validate_bsc_address

### test_encryption.py
- **Тестов:** 6
- **Классы:** TestEncryption
- **Покрытие:** EncryptionService
- **Результат:** ✅ 6/6 passed

### test_reward_calculation.py
- **Тестов:** 53
- **Классы:**
  - TestRewardAmountCalculation (11 тестов)
  - TestROICapCalculation (8 тестов)
  - TestRemainingROICalculation (8 тестов)
  - TestROICapReached (7 тестов)
  - TestCapRewardToRemainingROI (6 тестов)
  - TestROIProgressCalculation (8 тестов)
  - TestWithdrawalX5Rule (7 тестов)
- **Покрытие:** RewardCalculator

### test_financial_validation.py
- **Тестов:** 64
- **Классы:**
  - TestDepositLevelAmounts (7 тестов)
  - TestPartnerRequirements (3 теста)
  - TestWithdrawalMinAmount (6 тестов)
  - TestWithdrawalBalanceCheck (6 тестов)
  - TestX5WithdrawalRule (9 тестов)
  - TestGlobalDailyLimit (5 тестов)
  - TestDepositLevelValidation (4 теста)
  - TestROICapBoundaries (6 тестов)
  - TestAmountPrecision (6 тестов)
  - TestNegativeAmountHandling (4 теста)
  - TestBoundaryConditions (4 теста)
- **Покрытие:** DepositValidationService, WithdrawalValidator

### Итого:
- **Всего тестов:** 132+
- **Все критические функции покрыты**
- **Edge cases учтены**
- **Business logic валидирована**

---

## Важные замечания

1. **Decimal Precision:** Все финансовые расчёты используют `Decimal` для точности
2. **Edge Cases:** Покрыты нулевые, отрицательные, граничные значения
3. **Security:** Шифрование тестируется на roundtrip и random IV
4. **Business Rules:** x5 rule, ROI cap 500%, Partner requirements проверены
5. **Error Handling:** Все функции корректно обрабатывают невалидные входы

---

## Зависимости для тестов

```bash
pip install pytest pytest-asyncio cryptography web3 sqlalchemy loguru cffi pydantic-settings
```

## Известные проблемы

1. **test_validation.py:** Требует web3 с корректными версиями eth_utils
2. **test_reward_calculation.py:** Требует настроенные environment variables (или mock)
3. **test_financial_validation.py:** Требует database session mock

## Решения

Для изоляции unit тестов от внешних зависимостей используются:
- Mock objects для database sessions
- Fixture для EncryptionService с генерацией ключей
- Параметризованные тесты для множественных сценариев
