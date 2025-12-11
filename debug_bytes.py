text = "🔐 *Кошелёк администратора*\n\n🔥 *HOT WALLET* (Выплатной)\n"
encoded = text.encode("utf-8")
print(f"Total bytes: {len(encoded)}")
print(f"Byte 46: {encoded[46:47]}")
print(f"Context around 46: {encoded[40:60]}")

# Let's find where '*' are
for i, b in enumerate(encoded):
    if b == 42:  # '*'
        print(f"Found '*' at offset {i}")
