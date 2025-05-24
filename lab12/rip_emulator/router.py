class Router:
    def __init__(self, router_id, ip_address):
        self.router_id = router_id
        self.ip_address = ip_address
        self.routing_table = {}
        self.routing_table[self.ip_address] = (self.ip_address, 0) 
        self.neighbors = {}
        
    def add_neighbor(self, neighbor_router_id, neighbor_ip, metric):
        """Добавляет прямого соседа и маршрут к нему."""
        self.neighbors[neighbor_router_id] = (neighbor_ip, metric)
        if neighbor_ip not in self.routing_table or self.routing_table[neighbor_ip][1] > metric:
            self.routing_table[neighbor_ip] = (neighbor_ip, metric)

    def get_advertisement(self):
        """Генерирует объявление RIP (свою таблицу маршрутизации) для отправки соседям."""
        return self.routing_table.copy()

    def update_routing_table(self, neighbor_ip, advertisement, direct_metric_to_neighbor):
        """Обновляет таблицу маршрутизации на основе объявления от соседа."""
        table_changed = False
        for dest_ip, (adv_next_hop, adv_metric) in advertisement.items():
            new_metric = direct_metric_to_neighbor + adv_metric
            
            if new_metric >= 16:
                if dest_ip in self.routing_table and self.routing_table[dest_ip][0] == neighbor_ip:
                    if dest_ip in self.routing_table and self.routing_table[dest_ip][1] < 16:
                        if self.routing_table[dest_ip][0] == neighbor_ip:
                            if self.routing_table[dest_ip][1] < new_metric:
                                self.routing_table[dest_ip] = (neighbor_ip, new_metric)
                                table_changed = True
                continue 

            if dest_ip not in self.routing_table or new_metric < self.routing_table[dest_ip][1]:
                self.routing_table[dest_ip] = (neighbor_ip, new_metric)
                table_changed = True
            elif new_metric == self.routing_table[dest_ip][1] and self.routing_table[dest_ip][0] != neighbor_ip:
                pass

        return table_changed

    def __str__(self):
        output = f"Router {self.router_id} ({self.ip_address}) Table:\n"
        output += "[Destination IP]  [Next Hop]       [Metric]\n"
        if not self.routing_table:
            output += "<empty>\n"
            return output
        
        sorted_destinations = sorted(self.routing_table.keys())

        for dest_ip in sorted_destinations:
            next_hop_ip, metric = self.routing_table[dest_ip]
            output += f"{dest_ip:<18} {next_hop_ip:<18} {metric}\n"
        return output 