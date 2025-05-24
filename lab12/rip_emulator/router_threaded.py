import threading
import time
import queue

INFINITY_METRIC = 16
UPDATE_INTERVAL = 5

class RouterThread(threading.Thread):
    def __init__(self, router_id, ip_address, all_router_threads_queues):
        super().__init__()
        self.router_id = router_id
        self.ip_address = ip_address
        self.routing_table = {self.ip_address: (self.ip_address, 0)}
        self.neighbors_info = {} 
        self.in_queue = queue.Queue()
        self.all_router_threads_queues = all_router_threads_queues
        self.stop_event = threading.Event()
        self.log_prefix = f"Router {self.router_id} ({self.ip_address}): "

    def add_neighbor_link(self, neighbor_id, neighbor_ip, direct_metric):
        neighbor_in_queue = self.all_router_threads_queues.get(neighbor_id)
        if neighbor_in_queue:
            self.neighbors_info[neighbor_id] = (neighbor_ip, direct_metric, neighbor_in_queue)
            if neighbor_ip not in self.routing_table or self.routing_table[neighbor_ip][1] > direct_metric:
                self.routing_table[neighbor_ip] = (neighbor_ip, direct_metric)
        else:
            print(f"{self.log_prefix}Error: Could not find input queue for neighbor {neighbor_id}")

    def send_updates(self):
        advertisement = self.routing_table.copy()
        for neighbor_id, (n_ip, n_metric, n_queue) in self.neighbors_info.items():

            n_queue.put(("UPDATE", self.ip_address, advertisement))

    def update_routing_table(self, adv_source_ip, advertisement, direct_metric_to_source):
        table_changed = False
        for dest_ip, (adv_next_hop_unused, adv_metric) in advertisement.items():
            if dest_ip == self.ip_address: 
                continue

            new_metric = direct_metric_to_source + adv_metric

            if new_metric >= INFINITY_METRIC:

                if dest_ip in self.routing_table and self.routing_table[dest_ip][0] == adv_source_ip:
                    if self.routing_table[dest_ip][1] < INFINITY_METRIC:
                        self.routing_table[dest_ip] = (adv_source_ip, INFINITY_METRIC)
                        table_changed = True
                continue

            current_route = self.routing_table.get(dest_ip)
            if current_route is None or \
               new_metric < current_route[1] or \
               (new_metric == current_route[1] and current_route[0] == adv_source_ip):
                
                if current_route is None or new_metric != current_route[1] or current_route[0] != adv_source_ip:
                    self.routing_table[dest_ip] = (adv_source_ip, new_metric)
                    table_changed = True

        return table_changed

    def run(self):
        last_update_time = time.time()
        time.sleep(0.1)

        while not self.stop_event.is_set():
            current_time = time.time()
            if current_time - last_update_time >= UPDATE_INTERVAL:
                self.send_updates()
                last_update_time = current_time

            try:
                message_type, source_ip, data = self.in_queue.get(block=True, timeout=0.05) 
                
                if message_type == "UPDATE":
                    direct_metric_to_source = INFINITY_METRIC
                    for n_id, (n_ip, d_metric, _) in self.neighbors_info.items():
                        if n_ip == source_ip:
                            direct_metric_to_source = d_metric
                            break
                    
                    if direct_metric_to_source < INFINITY_METRIC:
                        if self.update_routing_table(source_ip, data, direct_metric_to_source):
                            self.send_updates()
                            last_update_time = time.time()
                
                self.in_queue.task_done()
            except queue.Empty:
                pass
            except Exception as e:
                print(f"{self.log_prefix}ERROR in run loop: {e}")
                break
            
            time.sleep(0.01)

    def stop(self):
        self.stop_event.set()

    def get_formatted_routing_table(self):
        output_lines = []

        current_table_copy = self.routing_table.copy() 
        sorted_destinations = sorted(current_table_copy.keys())

        if not sorted_destinations:
            output_lines.append("<empty>")
        else:
            for dest_ip in sorted_destinations:
                next_hop_ip, metric = current_table_copy[dest_ip]
                output_lines.append(f"{self.ip_address:<18} {dest_ip:<20} {next_hop_ip:<18} {metric:<8}")
        return output_lines 