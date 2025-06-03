import matplotlib.pyplot as plt
import numpy as np

# Параметры задачи
F = 15 * 10**9  # Размер файла в битах (15 Гбит)
u_s = 30 * 10**6  # Скорость отдачи сервера в бит/с (30 Мбит/с)
d_min = 2 * 10**6  # Скорость загрузки пира в бит/с (2 Мбит/с)

N_values = [10, 100, 1000]  # Количество пиров
u_peer_values_str = ["0.3 Мбит/с", "0.7 Мбит/с", "2 Мбит/с"] # Строки для меток
u_peer_values = np.array([0.3 * 10**6, 0.7 * 10**6, 2 * 10**6])  # Скорости отдачи пиров в бит/с

# Функции для расчета времени раздачи
def calculate_D_cs(N, F, u_s, d_min):
    return max((N * F) / u_s, F / d_min)

def calculate_D_p2p(N, F, u_s, d_min, u_peer):
    return max(F / u_s, F / d_min, (N * F) / (u_s + N * u_peer))

# Подготовка данных для графиков
results = {}
for N in N_values:
    results[N] = {'cs': [], 'p2p': []}
    d_cs_val = calculate_D_cs(N, F, u_s, d_min)
    for u_p in u_peer_values:
        results[N]['cs'].append(d_cs_val) # D_cs не зависит от u_peer
        results[N]['p2p'].append(calculate_D_p2p(N, F, u_s, d_min, u_p))

# Построение графиков
fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)
fig.suptitle('Время раздачи vs Скорость отдачи пиров для разного N', fontsize=16)

for i, N in enumerate(N_values):
    ax = axes[i]
    # Используем u_peer_values / 10**6 для отображения в Мбит/с на оси X
    ax.plot(u_peer_values / 10**6, results[N]['cs'], marker='o', linestyle='-', label='Клиент-Сервер')
    ax.plot(u_peer_values / 10**6, results[N]['p2p'], marker='s', linestyle='--', label='P2P')
    
    ax.set_xlabel('Скорость отдачи пира (u) [Мбит/с]')
    if i == 0:
        ax.set_ylabel('Минимальное время раздачи (с)')
    ax.set_title(f'N = {N}')
    ax.legend()
    ax.grid(True)
    
    # Установка меток на оси X
    ax.set_xticks(u_peer_values / 10**6)
    ax.set_xticklabels(u_peer_values_str) 

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig("lab05/distribution_time_plots.png") 
# print("График сохранен как distribution_time_plots.png")

# Показ графика
plt.show()

print("\nРасчетные значения времени (в секундах):")
print("-" * 50)
print(f"{'N':>4} | {'u (Мбит/с)':>12} | {'D_CS (с)':>10} | {'D_P2P (с)':>10}")
print("-" * 50)
for N_val in N_values:
    d_cs_s = results[N_val]['cs'][0] # D_CS одинаково для всех u
    for idx, u_p_s_str in enumerate(u_peer_values_str):
        u_val_for_print = u_p_s_str.split(' ')[0] # Берем только число
        d_p2p_s = results[N_val]['p2p'][idx]
        print(f"{N_val:>4} | {u_val_for_print:>12} | {d_cs_s:>10.0f} | {d_p2p_s:>10.2f}")
    print("-" * 50) 