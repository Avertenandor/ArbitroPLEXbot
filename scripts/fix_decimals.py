"""Fix the broken decimals in blockchain_service.py"""

with open('app/services/blockchain_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken USDT_DECIMALS line
content = content.replace(
    '# USDT decimals (BEP-20 USDT uses 18 decimals)\nUSDT_# PLEX uses 9 decimals\n        decimals = 9',
    '# USDT decimals (BEP-20 USDT uses 18 decimals)\nUSDT_DECIMALS = 18'
)

# Write back
with open('app/services/blockchain_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed USDT_DECIMALS line")

