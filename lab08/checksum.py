from typing import ByteString


def compute_checksum(data: ByteString) -> int:
    """Возвращает 16-битовую контрольную сумму (one-complement sum).

    Алгоритм:
        1. Разбиваем данные на 16-битные слова (big-endian).
        2. Складываем, сохраняя переносы.
        3. Дополнение до единицы.
    """
    if len(data) % 2 == 1:
        data += b"\x00"

    s: int = 0
    for i in range(0, len(data), 2):
        word = data[i] << 8 | data[i + 1]
        s += word
        s = (s & 0xFFFF) + (s >> 16)  # перенос

    return (~s) & 0xFFFF


def valid_checksum(data: ByteString, checksum: int) -> bool:
    """Проверяет, совпадает ли контрольная сумма с данными."""
    # Складываем данные и переданную контрольную сумму; корректное сообщение
    # должно дать результат 0xFFFF после дополнения до единицы.
    if len(data) % 2 == 1:
        data += b"\x00"

    s: int = 0
    for i in range(0, len(data), 2):
        word = data[i] << 8 | data[i + 1]
        s += word
        s = (s & 0xFFFF) + (s >> 16)

    s += checksum
    s = (s & 0xFFFF) + (s >> 16)

    return s == 0xFFFF


if __name__ == "__main__":
    # Простые тесты без фреймворка
    samples = [b"hello", b"0123456789abcd", b""]
    for sample in samples:
        cs = compute_checksum(sample)
        assert valid_checksum(sample, cs), "checksum should validate"

    # Повреждаем данные
    broken = b"hello"
    cs = compute_checksum(broken)
    tampered = bytearray(broken)
    tampered[0] ^= 0xFF  # flip bits
    assert not valid_checksum(tampered, cs), "checksum must fail on corrupted data"

    print("checksum tests passed") 