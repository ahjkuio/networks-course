# Практика 9. Сетевой уровень

## Wireshark: ICMP
В лабораторной работе предлагается исследовать ряд аспектов протокола ICMP:
- ICMP-сообщения, генерируемые программой Ping
- ICMP-сообщения, генерируемые программой Traceroute
- Формат и содержимое ICMP-сообщения

### 1. Ping (4 балла)
Программа Ping на исходном хосте посылает пакет на целевой IP-адрес; если хост с этим адресом
активен, то программа Ping на нем откликается, отсылая ответный пакет хосту, инициировавшему
связь. Оба этих пакета Ping передаются по протоколу ICMP.

Выберите какой-либо хост, расположенный на другом континенте (например, в Америке или
Азии). Захватите с помощью Wireshark ICMP пакеты от утилиты ping.
Для этого из командной строки запустите команду (аргумент `-n 10` означает, что должно быть
отослано 10 ping-сообщений): `ping –n 10 host_name`

Для анализа пакетов в Wireshark введите строку icmp в области фильтрации вывода.

![image](https://github.com/user-attachments/assets/c8971c4c-9a67-442c-a32f-b5a4060699c6)
![image](https://github.com/user-attachments/assets/8c88dac2-cda2-4308-b174-12d08544ed26)


#### Вопросы
1. Каков IP-адрес вашего хоста? Каков IP-адрес хоста назначения?
   - 192.168.1.96
   - 110.242.68.66 (`baidu.com`)
2. Почему ICMP-пакет не обладает номерами исходного и конечного портов?
   - ICMP функционирует на сетевом уровне (аналогично IP) и предназначен для передачи управляющих сообщений и сообщений об ошибках между хостами и маршрутизаторами. Он не используется для прямой связи между приложениями, как протоколы транспортного уровня (TCP, UDP), которые используют номера портов для идентификации конкретных процессов. Поэтому ICMP-пакетам не требуются номера портов.

3. Рассмотрите один из ping-запросов, отправленных вашим хостом. Каковы ICMP-тип и кодовый
   номер этого пакета? Какие еще поля есть в этом ICMP-пакете? Сколько байт приходится на поля 
   контрольной суммы, порядкового номера и идентификатора?
   ![image](https://github.com/user-attachments/assets/cf895aa4-1e32-4a82-89a4-f1d20150b5ef)
   - Тип 0 (Echo (ping) request), код - 0
   - Другие поля в заголовке ICMP: `Checksum` , `Identifier`, `Sequence Number`. Также пакет содержит поле `Data`.
   - На каждое поле 2 байта
5. Рассмотрите соответствующий ping-пакет, полученный в ответ на предыдущий. 
   Каковы ICMP-тип и кодовый номер этого пакета? Какие еще поля есть в этом ICMP-пакете? 
   Сколько байт приходится на поля контрольной суммы, порядкового номера и идентификатора?
   ![image](https://github.com/user-attachments/assets/3df2ee4f-7eb2-44c7-86c7-359d912223e0)
   - Тип 8 (Echo reply), код - 0
   - Другие поля в заголовке ICMP: `Checksum` , `Identifier`, `Sequence Number`. Также пакет содержит поле `Data`.
   - На каждое поле 2 байта

### 2. Traceroute (4 балла)
Программа Traceroute может применяться для определения пути, по которому пакет попал с
исходного на конечный хост.

Traceroute отсылает первый пакет со значением TTL = 1, второй – с TTL = 2 и т.д. Каждый
маршрутизатор понижает TTL-значение пакета, когда пакет проходит через этот маршрутизатор.
Когда на маршрутизатор приходит пакет со значением TTL = 1, этот маршрутизатор отправляет
обратно к источнику ICMP-пакет, свидетельствующий об ошибке.

Задача – захватить ICMP пакеты, инициированные программой traceroute, в сниффере Wireshark.
В ОС Windows вы можете запустить: `tracert host_name`

Выберите хост, который **расположен на другом континенте**.
![image](https://github.com/user-attachments/assets/81c37de6-0fb1-4533-b256-a1a5e6b90cf0)
![image](https://github.com/user-attachments/assets/d3fc5972-5529-4521-aab8-6bbec035c5d7)


#### Вопросы
1. Рассмотрите ICMP-пакет с эхо-запросом на вашем скриншоте. Отличается ли он от ICMP-пакетов
   с ping-запросами из Задания 1 (Ping)? Если да – то как?
   - ICMP эхо-запросы (Type 8, Code 0) от `traceroute -I` (например, пакет №224). Они идентичны по структуре (Type 8, Code 0, поля Identifier, Sequence Number, Data) ICMP эхо-запросам от `ping`. Отличие: `traceroute` последовательно увеличивает TTL в IP-заголовке этих запросов, `ping` использует стандартный высокий TTL.
   - ![image](https://github.com/user-attachments/assets/6b3467af-3c86-4459-a51d-5839e4fd6ef2)

2. Рассмотрите на вашем скриншоте ICMP-пакет с сообщением об ошибке. В нем больше полей,
   чем в ICMP-пакете с эхо-запросом. Какая информация содержится в этих дополнительных полях?
   - Пакет ICMP Time-to-live exceeded (Type 11, Code 0, например, пакет №240 на скриншоте) содержит:
      - Стандартный заголовок ICMP ошибки: поля Type, Code, Checksum и Unused.
      - Инкапсулированные данные (для идентификации исходного пакета):
      - Полный IP-заголовок исходного пакета. Включает IP-адреса источника/назначения, идентификатор IP, протокол (ICMP) и т.д.
      - Первые 8 байт полезной нагрузки (L4 payload) исходного IP-пакета. Поскольку исходный пакет был ICMP Echo Request, эти 8 байт представляют собой полный ICMP-заголовок этого Echo Request (поля Type: 8, Code: 0, Checksum, Identifier, Sequence Number).
   - ![image](https://github.com/user-attachments/assets/315bf18c-1307-4e72-b115-076b8cc08acb)

3. Рассмотрите три последних ICMP-пакета, полученных исходным хостом. Чем эти пакеты
   отличаются от ICMP-пакетов, сообщающих об ошибках? Чем объясняются такие отличия?
   - Echo Reply (Type 0) не является сообщением об ошибке. Это штатный ответ, подтверждающий, что ICMP Echo Request (зонд от traceroute) успешно достиг конечного хоста, и хост на него ответил.
Пакеты ошибок, такие как Time-to-live exceeded (Type 11), генерируются промежуточными маршрутизаторами и сигнализируют о проблеме с доставкой исходного пакета (например, истечение TTL).
Содержимое Echo Reply: Включает поля Type: 0, Code: 0, Checksum, а также Identifier и Sequence Number, которые соответствуют значениям из исходного Echo Request. Также возвращаются данные (Data), которые были в Echo Request. Это позволяет отправителю сопоставить ответ с конкретным запросом.
   - ![image](https://github.com/user-attachments/assets/98db5643-79e3-4e81-b34f-9a6100522a0e)
 

4. Есть ли такой канал, задержка в котором существенно превышает среднее значение? Можете
   ли вы, опираясь на имена маршрутизаторов, определить местоположение двух маршрутизаторов,
   расположенных на обоих концах этого канала?
   - ![image](https://github.com/user-attachments/assets/8031f31b-647f-4a69-a8c2-e05d599947b1)
   - Да, такой канал наблюдается между хопом 9 и 10:
   - **Маршрутизатор 1 (хоп 9):** IP `223.120.10.41`, средняя задержка ~57 мс. Принадлежит China Mobile. Расположен, вероятно, на европейской стороне или на входе в трансконтинентальную магистраль China Mobile (учитывая предыдущий хоп 8 `ipv4.de-cix.fra.de.as58453.chinamobile.com` во Франкфурте).
   - **Маршрутизатор 2 (хоп 10):** IP `223.120.16.14`, средняя задержка ~290 мс. Принадлежит China Mobile. Расположен уже глубоко в китайской части сети China Mobile.
   - Задержка на этом участке возрастает примерно на 233 мс, что норм для трансконтинентального канала (вероятно, Европа - Азия).

## Программирование.

### 1. IP-адрес и маска сети (1 балл)
Напишите консольное приложение, которое выведет IP-адрес вашего компьютера и маску сети на консоль.

#### Демонстрация работы
![image](https://github.com/user-attachments/assets/6edd94d0-ab94-482e-9759-4789f057c5c0)


### 2. Доступные порты (2 балла)
Выведите все доступные (свободные) порты в указанном диапазоне для заданного IP-адреса. 
IP-адрес и диапазон портов должны передаваться в виде входных параметров.

#### Демонстрация работы
![image](https://github.com/user-attachments/assets/2b51c5a7-2007-4d14-b11b-713588fc3f1b)


### 3. Широковещательная рассылка для подсчета копий приложения (6 баллов)
Разработать приложение, подсчитывающее количество копий себя, запущенных в локальной сети.
Приложение должно использовать набор сообщений, чтобы информировать другие приложения
о своем состоянии. После запуска приложение должно рассылать широковещательное сообщение
о том, что оно было запущено. Получив сообщение о запуске другого приложения, оно должно
сообщать этому приложению о том, что оно работает. Перед завершением работы приложение
должно информировать все известные приложения о том, что оно завершает работу. На экран
должен выводиться список IP адресов компьютеров (с указанием портов), на которых приложение
запущено.

Приложение считает другое приложение запущенным, если в течение промежутка времени,
равного нескольким интервалам между рассылками широковещательных сообщений, от него
пришло сообщение.

**Такое приложение может быть использовано, например, при наличии ограничения на
количество лицензионных копий программ.*

Пример GUI:

<img src="images/copies.png" width=200 />

#### Демонстрация работы
![image](https://github.com/user-attachments/assets/3a03472d-3bc9-4586-93d2-75ab4074c910)


## Задачи. Работа протокола TCP

### Задача 1. Докажите формулы (3 балла)
Пусть за период времени, в который изменяется скорость соединения с $\frac{W}{2 \cdot RTT}$
до $\frac{W}{RTT}$, только один пакет был потерян (очень близко к концу периода).
1. Докажите, что частота потери $L$ (доля потерянных пакетов) равна
   $$L = \dfrac{1}{\frac{3}{8} W^2 + \frac{3}{4} W}$$
2. Используйте выше полученный результат, чтобы доказать, что, если частота потерь равна
   $L$, то средняя скорость приблизительно равна
   $$\approx \dfrac{1.22 \cdot MSS}{RTT \cdot \sqrt{L}}$$

#### Решение
$L = \dfrac{\text{число потерянных пакетов}}{\text{число отправленных пакетов}}$

$\sum_{i=0}^{\frac{W}{2}} \left( \frac{W}{2} + i \right) = \frac{3W^2}{8} + \frac{3W}{4}$

$L = \dfrac{1}{\frac{3}{8}W^2 + \frac{3}{4}W}$

$\frac{3W^2}{8} \gg \frac{3W}{4}$

$L \approx \dfrac{8}{3W^2}$

$W \approx \sqrt{\dfrac{8}{3L}}$

$V_{\text{avg}} = \dfrac{3}{4} \cdot W \cdot \dfrac{MSS}{RTT}$

$V_{\text{avg}} \approx \dfrac{3}{4} \cdot \sqrt{\dfrac{8}{3L}} \cdot \dfrac{MSS}{RTT}$

$V_{\text{avg}} \approx \dfrac{1.22 \cdot MSS}{RTT \cdot \sqrt{L}}$

### Задача 2. Найдите функциональную зависимость (3 балла)
Рассмотрим модификацию алгоритма управления перегрузкой протокола TCP. Вместо
аддитивного увеличения, мы можем использовать мультипликативное увеличение. 
TCP-отправитель увеличивает размер своего окна в небольшую положительную 
константу $a$ ($a > 1$), как только получает верный ACK-пакет.
1. Найдите функциональную зависимость между частотой потерь $L$ и максимальным
размером окна перегрузки $W$.
2. Докажите, что для этого измененного протокола TCP, независимо от средней пропускной
способности, TCP-соединение всегда требуется одинаковое количество времени для
увеличения размера окна перегрузки с $\frac{W}{2}$ до $W$.

#### Решение
1. Общее количество сегментов:
   $$S = \dfrac{W}{2} + \dfrac{W}{2} (1+a) + \dfrac{W}{2} (1+a)^2 + \cdots + \dfrac{W}{2} (1+a)^n, \quad n = \log_{1+a}2$$
2. Тогда:
   $$S = \dfrac{W (2a + 1)}{2a}$$
3. Частота потерь:
   $$L = \dfrac{1}{S} = \dfrac{2a}{W (2a + 1)}$$
4. Время, требуемое TCP для увеличения окна:
   $$n \cdot RTT = \log_{1+a}2 \cdot RTT$$
5. Средняя пропускная способность:
   $$V_{\text{avg}} = MSS \cdot \dfrac{S}{(n+1) \cdot RTT} = \dfrac{MSS}{L \cdot (n+1) \cdot RTT}$$
