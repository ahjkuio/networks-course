import random
from checksum import compute_checksum, valid_checksum

print("Running tests...")

passed = 0

# 1. Небольшая строка
data1 = b"hello"
cs1 = compute_checksum(data1)
print(f"Test 1 - Checksum: {cs1}")
assert valid_checksum(data1, cs1)
passed += 1

# 2. Ошибка в контрольной сумме
print(f"Test 2 - Wrong checksum: {cs1 ^ 0xFFFF}")
assert not valid_checksum(data1, cs1 ^ 0xFFFF)
passed += 1

# 3. Повреждённые данные
broken = bytearray(data1)
broken[0] ^= 0xFF
print("Test 3 - Corrupted data")
assert not valid_checksum(broken, cs1)
passed += 1

# 4. Нечётная длина
odd_data = b"abc"
cs_odd = compute_checksum(odd_data)
print(f"Test 4 - Odd-length checksum: {cs_odd}")
assert valid_checksum(odd_data, cs_odd)
passed += 1

# 5. Пустой массив
empty = b""
cs_empty = compute_checksum(empty)
print(f"Test 5 - Empty data checksum: {cs_empty}")
assert valid_checksum(empty, cs_empty)
passed += 1

# 6. Все байты = 0xFF (должна быть нулевая сумма)
all_ones = bytes([0xFF] * 8)
cs_ones = compute_checksum(all_ones)
print(f"Test 6 - All-ones data checksum: {cs_ones}")
assert valid_checksum(all_ones, cs_ones)
passed += 1

# 7. Случайный массив (32 байта)
rand_data = bytes(random.getrandbits(8) for _ in range(32))
cs_rand = compute_checksum(rand_data)
print(f"Test 7 - Random data checksum: {cs_rand}")
assert valid_checksum(rand_data, cs_rand)
passed += 1

# 8. Проверка некорректных данных для случая 7
print("Test 8 - Corrupted random data")
corrupt = bytearray(rand_data)
corrupt[-1] ^= 0xAA
assert not valid_checksum(corrupt, cs_rand)
passed += 1

print(f"\nAll {passed} tests passed!") 