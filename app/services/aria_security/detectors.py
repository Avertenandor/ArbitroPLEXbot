"""
Attack Pattern Detection.

Contains all attack detection patterns and response constants.
"""

import re


# ========================================================================
# ATTACK PATTERN DETECTION
# ========================================================================

# Prompt Injection Patterns - attempts to override AI instructions
PROMPT_INJECTION_PATTERNS = [
    # Direct instruction override
    r"игнорируй\s*(все|предыдущие|свои)\s*"
    r"(инструкции|правила|ограничения)",
    r"ignore\s*(all|previous|your)\s*(instructions|rules"
    r"|constraints)",
    r"забудь\s*(все|свои)\s*(правила|инструкции)",
    r"forget\s*(all|your)\s*(rules|instructions)",
    r"новые\s*инструкции",
    r"new\s*instructions",
    r"override\s*(system|prompt|rules)",
    r"system\s*prompt",
    r"ты\s*теперь\s*(не|другой|новый)",
    r"you\s*are\s*now",
    r"притворись|pretend\s*to\s*be",
    r"roleplay\s*as",
    r"act\s*as\s*if",
    r"представь\s*(себя|что\s*ты)",

    # Jailbreak attempts
    r"DAN\s*mode",
    r"developer\s*mode",
    r"режим\s*разработчика",
    r"без\s*ограничений",
    r"no\s*restrictions",
    r"безопасный\s*режим\s*(выкл|off)",
    r"отключи\s*(фильтр|защиту|ограничения)",
    r"disable\s*(filter|safety|restrictions)",

    # Delimiter injection
    r"\[SYSTEM\]",
    r"\[ADMIN\]",
    r"\[OVERRIDE\]",
    r"\[INST\]",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"###\s*(System|Human|Assistant)",

    # Role manipulation
    r"ты\s*(админ|администратор|модератор|босс)",
    r"я\s*(владелец|создатель|разработчик|админ)",
    r"i\s*am\s*(the\s*)?(owner|creator|developer|admin)",
    r"grant\s*me\s*(admin|access|permissions)",
    r"дай\s*мне\s*(доступ|права|полномочия)",
    r"сделай\s*меня\s*(админом|модератором)",
    r"make\s*me\s*(admin|moderator)",
]

# Social Engineering Patterns
SOCIAL_ENGINEERING_PATTERNS = [
    # Urgency/pressure
    r"срочно|немедленно|прямо\s*сейчас|urgent|immediately"
    r"|right\s*now",
    r"это\s*критически\s*важно|this\s*is\s*critical",
    r"если\s*не\s*сделаешь|if\s*you\s*don't",

    # Authority claims
    r"я\s*(от|из)\s*(имени|лица)\s*(босса|владельца"
    r"|командира)",
    r"босс\s*(сказал|приказал|просил)",
    r"командир\s*(сказал|приказал|просил)",
    r"по\s*приказу\s*(босса|владельца|командира)",
    r"on\s*behalf\s*of",
    r"boss\s*(said|ordered|asked)",

    # Guilt/trust manipulation
    r"ты\s*же\s*доверяешь\s*мне",
    r"мы\s*же\s*друзья",
    r"разве\s*ты\s*не\s*поможешь",
    r"you\s*trust\s*me",
    r"we\s*are\s*friends",

    # Technical deception
    r"это\s*(тест|проверка|эксперимент)",
    r"just\s*(a\s*)?test",
    r"для\s*отладки",
    r"debug\s*mode",
    r"обход\s*(для|в)\s*целях\s*безопасности",
]

# Privilege Escalation Patterns
PRIVILEGE_ESCALATION_PATTERNS = [
    # Direct requests for elevated access
    r"повысь\s*(мои\s*)?(права|доступ|уровень)",
    r"upgrade\s*(my\s*)?(access|permissions|level)",
    r"сделай\s*супер\s*админом",
    r"make\s*(me\s*)?super\s*admin",
    r"дай\s*(полный|максимальный)\s*доступ",
    r"give\s*(full|maximum)\s*access",

    # Attempting to modify admin list
    r"добавь\s*(меня|его|её)\s*в\s*админы",
    r"add\s*(me|him|her)\s*to\s*admins",
    r"убери\s*из\s*доверенных",
    r"remove\s*from\s*trusted",

    # Attempting to access super_admin functions as regular admin
    r"emergency.*stop",
    r"аварийн.*остано",
    r"полная\s*остановка",
    r"full\s*stop",
]

# Data Exfiltration Patterns
DATA_EXFILTRATION_PATTERNS = [
    # Sensitive data requests
    r"покажи\s*(все\s*)?(пароли|ключи|секреты|токены)",
    r"show\s*(all\s*)?(passwords|keys|secrets|tokens)",
    r"API\s*key",
    r"master\s*key",
    r"private\s*key",
    r"приватный\s*ключ",
    r"мастер\s*ключ",

    # Database/architecture info
    r"структура\s*(базы|БД|данных)",
    r"database\s*structure",
    r"схема\s*(БД|базы)",
    r"database\s*schema",
    r"IP\s*(адрес|сервера)",
    r"server\s*(IP|address)",

    # Financial data
    r"общий\s*(баланс|оборот)\s*платформы",
    r"total\s*(balance|turnover)",
    r"все\s*финансовые\s*данные",
    r"all\s*financial\s*data",
]


def compile_patterns() -> dict[str, list[re.Pattern]]:
    """Compile all patterns for efficient matching."""
    return {
        "prompt_injection": [
            re.compile(p, re.IGNORECASE)
            for p in PROMPT_INJECTION_PATTERNS
        ],
        "social_engineering": [
            re.compile(p, re.IGNORECASE)
            for p in SOCIAL_ENGINEERING_PATTERNS
        ],
        "privilege_escalation": [
            re.compile(p, re.IGNORECASE)
            for p in PRIVILEGE_ESCALATION_PATTERNS
        ],
        "data_exfiltration": [
            re.compile(p, re.IGNORECASE)
            for p in DATA_EXFILTRATION_PATTERNS
        ],
    }


COMPILED_PATTERNS = compile_patterns()


# ========================================================================
# SECURITY RESPONSES
# ========================================================================

SECURITY_RESPONSE_BLOCKED = """
🚫 **ДОСТУП ЗАБЛОКИРОВАН**

Обнаружена подозрительная активность в вашем
сообщении.

Возможные причины:
• Попытка манипуляции AI-ассистентом
• Подозрительные паттерны в сообщении
• Попытка получить несанкционированный доступ

Если это ошибка — обратитесь к администратору.
Все инциденты логируются.
"""

SECURITY_RESPONSE_FORWARDED = """
⚠️ **ПЕРЕСЛАННЫЕ СООБЩЕНИЯ ИГНОРИРУЮТСЯ**

Я вижу, что это пересланное сообщение.

В целях безопасности я НЕ выполняю команды из
пересланных сообщений. Это защита от атак, где
злоумышленник пересылает сообщения "от имени" админа.

Если вам нужно выполнить действие — напишите команду
напрямую.
"""

SECURITY_RESPONSE_SPOOFING = """
🚨 **ОБНАРУЖЕНА ПОПЫТКА МАСКИРОВКИ**

Ваш username похож на username администратора, но ваш
Telegram ID не соответствует.

Это либо:
• Случайное совпадение
• Попытка атаки

Все администраторы идентифицируются по Telegram ID,
не по username. Инцидент записан в логи безопасности.
"""
