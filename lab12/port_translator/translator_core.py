import socket
import threading
import json
import os
import queue
import time

class PortTranslatorCore:
    def __init__(self):
        self.rules = []

        self.active_listeners = {} 

        self.active_connections = []

        self.log_queue = queue.Queue()
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(base_dir, "port_rules.json")
        
        self._is_running = False
        
        self.rules_lock = threading.Lock()
        self.listeners_lock = threading.Lock()
        self.connections_lock = threading.Lock()
        
        self.load_rules_from_file()

    def _get_rule_key(self, rule):
        """Создает уникальный ключ для правила на основе listen_ip и listen_port."""
        listen_ip = rule.get("listen_ip", "0.0.0.0")
        listen_port = int(rule["listen_port"])
        return (listen_ip, listen_port)

    def _log(self, message):
        print(f"[Core]: {message}")
        self.log_queue.put(message)

    def load_rules_from_file(self):
        self._log(f"Loading rules from {self.config_file}...")
        try:
            with open(self.config_file, 'r') as f:
                loaded_rules = json.load(f)
            
            valid_rules = []
            seen_keys = set()
            for rule in loaded_rules:
                if not all(k in rule for k in ["name", "listen_port", "target_host", "target_port"]): 
                    self._log(f"Warning: Invalid rule structure skipped: {rule}")
                    continue
                
                rule["listen_ip"] = rule.get("listen_ip", "0.0.0.0")

                try:
                    key = self._get_rule_key(rule)
                except KeyError as e:
                    self._log(f"Warning: Rule missing essential field ({e}) for key generation: {rule}. Skipping.")
                    continue
                except ValueError as e:
                    self._log(f"Warning: Rule has invalid port for key generation ({e}): {rule}. Skipping.")
                    continue

                if key in seen_keys:
                    self._log(f"Warning: Duplicate listen_ip/listen_port {key} for rule '{rule.get('name', 'N/A')}'. Skipping.")
                else:
                    seen_keys.add(key)
                    valid_rules.append(rule)
            
            with self.rules_lock:
                self.rules = valid_rules
            self._log(f"Loaded {len(self.rules)} unique rules.")
            return True
        except FileNotFoundError:
            self._log(f"Error: Config file {self.config_file} not found.")
            with self.rules_lock:
                self.rules = []
            return False
        except json.JSONDecodeError as e:
            self._log(f"Error: Could not decode JSON from {self.config_file}. Details: {e}")
            with self.rules_lock:
                self.rules = []
            return False
        except Exception as e:
            self._log(f"Error loading rules: {e}")
            with self.rules_lock:
                self.rules = []
            return False

    def get_rules(self):
        with self.rules_lock:
            return json.loads(json.dumps(self.rules))

    def reload_rules_from_file(self):
        self._log("Перезагрузка правил из файла...")
        try:
            with open(self.config_file, 'r') as f:
                new_rules_list_raw = json.load(f)
            self._log(f"Найдено {len(new_rules_list_raw)} правил в файле для перезагрузки.")

            validated_new_rules_list = []
            seen_new_keys = set()
            for rule in new_rules_list_raw:
                if not all(k in rule for k in ["name", "listen_port", "target_host", "target_port"]):
                    self._log(f"ПРЕДУПРЕЖДЕНИЕ (перезагрузка): Некорректная структура правила {rule}. Пропускается.")
                    continue
                
                rule["listen_ip"] = rule.get("listen_ip", "0.0.0.0")
                
                try:
                    key = self._get_rule_key(rule)
                except KeyError as e:
                    self._log(f"ПРЕДУПРЕЖДЕНИЕ (перезагрузка): Правило не содержит поля ({e}) для ключа: {rule}. Пропускается.")
                    continue
                except ValueError as e:
                    self._log(f"ПРЕДУПРЕЖДЕНИЕ (перезагрузка): Неверный порт в правиле ({e}): {rule}. Пропускается.")
                    continue

                if key in seen_new_keys:
                    self._log(f"ПРЕДУПРЕЖДЕНИЕ (перезагрузка): Дублирующее правило для {key[0]}:{key[1]} в '{rule.get('name', 'N/A')}'. Правило будет проигнорировано.")
                else:
                    seen_new_keys.add(key)
                    validated_new_rules_list.append(rule)
            
            if len(validated_new_rules_list) != len(new_rules_list_raw):
                 self._log(f"После проверки (перезагрузка) осталось {len(validated_new_rules_list)} уникальных правил.")
            
            new_rules_map = {self._get_rule_key(rule): rule for rule in validated_new_rules_list}

            with self.listeners_lock:
                current_listener_keys = set(self.active_listeners.keys())
            
            new_listener_keys = set(new_rules_map.keys())

            keys_to_stop = current_listener_keys - new_listener_keys
            keys_to_start = new_listener_keys - current_listener_keys
            
            keys_to_restart = set()
            with self.rules_lock:
                current_rules_map = {self._get_rule_key(r): r for r in self.rules}

            for key in current_listener_keys.intersection(new_listener_keys):
                current_rule_details = current_rules_map.get(key)
                new_rule_details = new_rules_map.get(key)
                if current_rule_details and new_rule_details:
                    if (current_rule_details.get("target_host") != new_rule_details.get("target_host") or
                        current_rule_details.get("target_port") != new_rule_details.get("target_port")):
                        self._log(f"Обнаружено изменение в target для правила '{new_rule_details.get('name')}'. Слушатель будет перезапущен.")
                        keys_to_restart.add(key)

            keys_to_stop.update(keys_to_restart)
            keys_to_start.update(keys_to_restart)


            self._log(f"Ключи слушателей для остановки: {keys_to_stop}")
            self._log(f"Ключи слушателей для запуска (или перезапуска): {keys_to_start}")

            for key in keys_to_stop:
                self._stop_specific_listener(key)

            if self._is_running:
                for key in keys_to_start:
                    rule_config = new_rules_map.get(key)
                    if rule_config:
                        self._start_specific_listener(rule_config)
            
            with self.rules_lock:
                self.rules = validated_new_rules_list
            
            self._log(f"Правила успешно перезагружены. Текущее количество правил: {len(self.rules)}")
            return True

        except FileNotFoundError:
            self._log(f"ОШИБКА (перезагрузка): Файл конфигурации {self.config_file} не найден.")
            return False
        except json.JSONDecodeError as e:
            self._log(f"ОШИБКА (перезагрузка): Не удалось декодировать JSON из {self.config_file}. Детали: {e}")
            return False
        except Exception as e:
            self._log(f"ОШИБКА при перезагрузке правил: {e}")
            import traceback
            self._log(traceback.format_exc())
            return False

    def _start_specific_listener(self, rule_config):
        rule_key = self._get_rule_key(rule_config)
        name = rule_config.get("name", f"rule_{rule_key[0]}_{rule_key[1]}")
        listen_ip = rule_config.get("listen_ip", "0.0.0.0")
        
        try:
            listen_port = int(rule_config["listen_port"])
            if "target_host" not in rule_config or "target_port" not in rule_config:
                 raise KeyError("target_host or target_port missing in rule_config")
        except (KeyError, ValueError) as e:
            self._log(f"ОШИБКА: Некорректный формат правила '{name}': {e}. Пропускаем запуск слушателя.")
            return

        listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener_socket.bind((listen_ip, listen_port))
            listener_socket.listen(5)
            self._log(f"Слушатель для правила '{name}' ({listen_ip}:{listen_port}) успешно привязан и слушает.")
        except OSError as e:
            self._log(f"ОШИБКА при запуске слушателя для '{name}' на {listen_ip}:{listen_port}: {e}. Возможно, порт уже занят.")
            listener_socket.close()
            return

        thread = threading.Thread(target=self._listen_for_rule, args=(listener_socket, rule_config, name), daemon=True)
        thread.start()
        
        with self.listeners_lock:
            self.active_listeners[rule_key] = {"thread": thread, "socket": listener_socket, "rule_name": name, "rule_config": rule_config}

    def _stop_specific_listener(self, rule_key):
        with self.listeners_lock:
            listener_info = self.active_listeners.pop(rule_key, None)

        if listener_info:
            name = listener_info["rule_name"]
            self._log(f"Остановка слушателя для правила '{name}' (ключ: {rule_key})...")
            listener_socket = listener_info.get("socket")
            listener_thread = listener_info.get("thread")
            if listener_socket:
                try:
                    listener_socket.shutdown(socket.SHUT_RDWR)
                except OSError as e:
                    self._log(f"Предупреждение при shutdown сокета слушателя '{name}': {e}")
                finally:
                    try:
                        listener_socket.close()
                    except OSError as e_close:
                         self._log(f"Ошибка при close сокета слушателя '{name}': {e_close}")


            if listener_thread and listener_thread.is_alive():
                listener_thread.join(timeout=0.5)
                if listener_thread.is_alive():
                    self._log(f"ПРЕДУПРЕЖДЕНИЕ: Поток слушателя '{name}' не завершился вовремя после закрытия сокета.")
            self._log(f"Слушатель для правила '{name}' остановлен.")
        else:
            self._log(f"ПРЕДУПРЕЖДЕНИЕ: Попытка остановить несуществующий слушатель с ключом {rule_key}")

    def start_translator(self):
        self._log("Attempting to start translator...")
        current_rules = self.get_rules()
        if not current_rules:
            self._log("No rules loaded. Cannot start translator.")
            return False
        if self._is_running:
            self._log("Translator is already running.")
            return True

        self._is_running = True
        
        with self.listeners_lock:
            if self.active_listeners:
                self._log("Clearing any pre-existing listeners before start...")
                keys_to_clear = list(self.active_listeners.keys())
                for key in keys_to_clear:
                    self._stop_specific_listener(key)


        num_started = 0
        for rule_config in current_rules:
            self._start_specific_listener(rule_config)
            rule_key_check = self._get_rule_key(rule_config)
            with self.listeners_lock:
                if rule_key_check in self.active_listeners:
                    num_started +=1
        
        if num_started == 0:
            self._log("No listeners were started successfully. Translator will not run.")
            self._is_running = False
            return False
            
        self._log(f"Translator started. {num_started} listeners active.")
        return True

    def _listen_for_rule(self, listener_socket, rule_config, rule_name):
        listen_ip_port_tuple = listener_socket.getsockname() 
        original_rule_key = self._get_rule_key(rule_config)

        self._log(f"Поток для правила '{rule_name}' ({listen_ip_port_tuple[0]}:{listen_ip_port_tuple[1]}) активен и ожидает соединений.")

        try:
            while self._is_running:
                try:
                    listener_socket.settimeout(1.0)
                    client_socket, client_address = listener_socket.accept()
                    
                    if not self._is_running:
                        client_socket.close()
                        self._log(f"Транслятор остановлен во время accept для '{rule_name}'. Соединение от {client_address} закрыто.")
                        break
                        
                    self._log(f"Для правила '{rule_name}': принято соединение от {client_address[0]}:{client_address[1]}")
                    
                    forward_thread = threading.Thread(
                        target=self._forward_data,
                        args=(client_socket, client_address, rule_config, rule_name),
                        daemon=True
                    )
                    forward_thread.start()

                except socket.timeout:
                    continue
                except OSError as e:
                    if self._is_running:
                        self._log(f"Ошибка сокета (вероятно, закрыт) в слушателе для '{rule_name}' ({original_rule_key}): {e}. Поток завершается.")
                    break
                except Exception as e:
                    if self._is_running:
                        self._log(f"Неизвестная ошибка в слушателе для '{rule_name}' ({original_rule_key}): {e}. Поток завершается.")
                    break
        finally:
            if listener_socket:
                try:
                    listener_socket.close()
                except OSError:
                    pass
            self._log(f"Поток слушателя для правила '{rule_name}' ({original_rule_key}) окончательно завершен.")

    def _forward_data(self, client_socket, client_address, rule_config, rule_name_for_log):
        target_host = rule_config["target_host"]
        target_port = int(rule_config["target_port"])
        
        self._log(f"[{rule_name_for_log}] Пересылка: {client_address} -> {target_host}:{target_port}")
        target_socket = None
        resolved_target_ip = ""
        
        try:
            try:
                socket.inet_aton(target_host)
                resolved_target_ip = target_host
            except socket.error:
                self._log(f"[{rule_name_for_log}] Разрешение имени хоста {target_host}...")
                try:
                    resolved_target_ip = socket.gethostbyname(target_host)
                    self._log(f"[{rule_name_for_log}] {target_host} разрешен в {resolved_target_ip}")
                except socket.gaierror as e:
                    self._log(f"[{rule_name_for_log}] ОШИБКА DNS разрешения для {target_host}: {e}. Закрытие соединения с {client_address}.")
                    client_socket.close()
                    return

            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.settimeout(10)
            self._log(f"[{rule_name_for_log}] Подключение к {target_host}({resolved_target_ip}):{target_port}...")
            target_socket.connect((resolved_target_ip, target_port))
            self._log(f"[{rule_name_for_log}] Подключено к {target_host}({resolved_target_ip}):{target_port}")
            target_socket.settimeout(None)

            conn_info = {
                "client_socket": client_socket, "target_socket": target_socket,
                "client_address": client_address, "target_address": (resolved_target_ip, target_port),
                "rule_name": rule_name_for_log, "active": True,
                "thread_to_target": None, "thread_to_client": None
            }
            with self.connections_lock:
                self.active_connections.append(conn_info)
            
            thread_to_target = threading.Thread(target=self._pipe_stream, args=(client_socket, target_socket, f"C->T ({rule_name_for_log})", conn_info), daemon=True)
            thread_to_client = threading.Thread(target=self._pipe_stream, args=(target_socket, client_socket, f"T->C ({rule_name_for_log})", conn_info), daemon=True)
            
            conn_info["thread_to_target"] = thread_to_target
            conn_info["thread_to_client"] = thread_to_client

            thread_to_target.start()
            thread_to_client.start()

        except socket.timeout:
            self._log(f"[{rule_name_for_log}] Таймаут при подключении к {target_host}({resolved_target_ip}):{target_port}")
            if client_socket: client_socket.close()
            if target_socket: target_socket.close()
        except socket.error as e:
            self._log(f"[{rule_name_for_log}] Ошибка сокета при пересылке для {client_address} к {target_host}({resolved_target_ip}): {e}")
            if client_socket: client_socket.close()
            if target_socket: target_socket.close()
        except Exception as e:
            self._log(f"[{rule_name_for_log}] Неожиданная ошибка при пересылке для {client_address}: {e}")
            import traceback
            self._log(traceback.format_exc())
            if client_socket: client_socket.close()
            if target_socket: target_socket.close()
            pass


    def _remove_connection_info_if_both_pipes_done(self, conn_info):
        with self.connections_lock:
            if conn_info in self.active_connections:
                is_to_target_alive = conn_info.get("thread_to_target") and conn_info["thread_to_target"].is_alive()
                is_to_client_alive = conn_info.get("thread_to_client") and conn_info["thread_to_client"].is_alive()

                if not is_to_target_alive and not is_to_client_alive:
                    self.active_connections.remove(conn_info)
                    self._log(f"Запись о соединении для {conn_info.get('rule_name', 'N/A')} {conn_info.get('client_address')} <-> {conn_info.get('target_address')} удалена (оба канала завершены).")

    def _pipe_stream(self, source_socket, dest_socket, pipe_description, conn_info):
        self._log(f"Запуск канала: {pipe_description}")
        try:
            while self._is_running and conn_info.get("active", False):
                source_socket.settimeout(1.0)
                try:
                    data = source_socket.recv(4096)
                except socket.timeout:
                    if not (self._is_running and conn_info.get("active", False)):
                        self._log(f"Канал {pipe_description}: Транслятор или соединение неактивно. Завершение по таймауту.")
                        break
                    continue
                except OSError:
                    self._log(f"Канал {pipe_description}: Ошибка сокета при чтении (вероятно, закрыт). Завершение.")
                    break

                if not data:
                    self._log(f"Канал {pipe_description}: Соединение закрыто удаленной стороной (нет данных).")
                    break 
                
                try:
                    dest_socket.sendall(data)
                except OSError:
                    self._log(f"Канал {pipe_description}: Ошибка сокета при записи (вероятно, закрыт). Завершение.")
                    break
        except Exception as e:
            self._log(f"Канал {pipe_description}: Неизвестная ошибка: {e}.")
        finally:
            self._log(f"Канал {pipe_description}: Завершение пересылки.")
            conn_info["active"] = False

            try: source_socket.shutdown(socket.SHUT_RDWR)
            except: pass
            finally:
                try: source_socket.close()
                except: pass
            
            try: dest_socket.shutdown(socket.SHUT_RDWR)
            except: pass
            finally:
                try: dest_socket.close()
                except: pass
            
            self._remove_connection_info_if_both_pipes_done(conn_info)


    def stop_translator(self):
        self._log("Attempting to stop translator...")
        if not self._is_running:
            self._log("Translator is not running.")
            return
        
        self._is_running = False

        with self.listeners_lock:
            listener_keys_to_stop = list(self.active_listeners.keys())
        
        for key in listener_keys_to_stop:
            self._stop_specific_listener(key)
        
        with self.listeners_lock:
            if self.active_listeners:
                 self._log(f"ПРЕДУПРЕЖДЕНИЕ: После остановки всех слушателей остались: {list(self.active_listeners.keys())}")
                 self.active_listeners.clear()

        self._log("Остановка активных соединений...")
        with self.connections_lock:
            active_conn_copy = list(self.active_connections) 
            for conn_info in active_conn_copy:
                conn_info["active"] = False
                client_sock = conn_info.get("client_socket")
                target_sock = conn_info.get("target_socket")
                
                if client_sock:
                    try: client_sock.shutdown(socket.SHUT_RDWR); client_sock.close() 
                    except: pass
                if target_sock:
                    try: target_sock.shutdown(socket.SHUT_RDWR); target_sock.close()
                    except: pass
            
            time.sleep(0.2)
            
            final_check_connections = list(self.active_connections)
            if final_check_connections:
                self._log(f"Принудительное ожидание/очистка для {len(final_check_connections)} оставшихся соединений...")
                for conn_info in final_check_connections:
                    tt_thread = conn_info.get("thread_to_target")
                    tc_thread = conn_info.get("thread_to_client")
                    if tt_thread and tt_thread.is_alive(): tt_thread.join(timeout=0.1)
                    if tc_thread and tc_thread.is_alive(): tc_thread.join(timeout=0.1)
                    if conn_info in self.active_connections:
                        self.active_connections.remove(conn_info)
                        self._log(f"Принудительно удалена запись о соединении для {conn_info.get('rule_name', 'N/A')}")

        with self.connections_lock:
            if self.active_connections:
                self._log(f"ПРЕДУПРЕЖДЕНИЕ: После остановки и попыток join, осталось {len(self.active_connections)} активных соединений. Очистка.")
                self.active_connections.clear()
        
        self._log("Translator stopped.")

if __name__ == '__main__':
    core = PortTranslatorCore()
    
    def print_logs_from_queue(q):
        while True:
            try:
                print(f"[TestLogQueue]: {q.get_nowait()}")
            except queue.Empty:
                break
            except Exception as e:
                print(f"Error reading log queue: {e}")
                break
    
    print("--- Initial Load ---")
    print_logs_from_queue(core.log_queue)
    print("Rules:", core.get_rules())
    
    print("\n--- Starting Translator ---")
    core.start_translator()
    time.sleep(0.1)
    print_logs_from_queue(core.log_queue)

    print("\n--- Modifying config file for reload ---")
    initial_rules_for_test = [
        {"name": "InitialRule1", "listen_ip": "127.0.0.1", "listen_port": 12345, "target_host": "neverssl.com", "target_port": 80},
        {"name": "InitialRule2", "listen_ip": "127.0.0.1", "listen_port": 12346, "target_host": "example.com", "target_port": 80}
    ]
    if not os.path.exists(core.config_file):
        with open(core.config_file, 'w') as f:
            json.dump(initial_rules_for_test, f, indent=2)
        core.load_rules_from_file()
        core.stop_translator()
        core.start_translator()
        time.sleep(0.1)
        print_logs_from_queue(core.log_queue)

    reloaded_rules_for_test = [
        {"name": "InitialRule1_MODIFIED", "listen_ip": "127.0.0.1", "listen_port": 12345, "target_host": "google.com", "target_port": 80},
        {"name": "NewRule", "listen_ip": "127.0.0.1", "listen_port": 12347, "target_host": "wikipedia.org", "target_port": 80}
    ]
    with open(core.config_file, 'w') as f:
        json.dump(reloaded_rules_for_test, f, indent=2)
    
    print("\n--- Attempting to Reload Config While Running ---")
    if core.reload_rules_from_file():
        print("Reload successful.")
    else:
        print("Reload failed.")
    time.sleep(0.1)
    print_logs_from_queue(core.log_queue)
    print("Rules after reload:", core.get_rules())

    print("\n--- Stopping Translator ---")
    core.stop_translator()
    time.sleep(0.1)
    print_logs_from_queue(core.log_queue)

    print("\n--- Test Complete ---") 