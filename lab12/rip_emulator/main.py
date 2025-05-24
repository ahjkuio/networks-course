import json
from router import Router

CONFIG_FILE = 'network_config.json'
MAX_ITERATIONS = 20 # это для предотвращения бесконечного цикла
INFINITY_METRIC = 16

def load_network_config(file_path):
    """Загружает конфигурацию сети из JSON файла."""
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config

def initialize_routers(config):
    """Инициализирует маршрутизаторы на основе конфигурации."""
    routers = {}
    router_id_to_ip = {}
    for r_data in config['routers']:
        router = Router(r_data['id'], r_data['ip'])
        routers[r_data['id']] = router
        router_id_to_ip[r_data['id']] = r_data['ip']
    
    for link_data in config['links']:
        router_from = routers.get(link_data['from'])
        router_to_id = link_data['to']
        router_to_ip = router_id_to_ip.get(router_to_id)
        metric = link_data['metric']
        
        if router_from and router_to_ip:
            router_from.add_neighbor(router_to_id, router_to_ip, metric)
        else:
            print(f"Warning: Could not establish link {link_data['from']} -> {link_data['to']}. Router ID or IP not found.")
            
    return routers

def simulate_rip(routers):
    """Симулирует работу протокола RIP."""
    print("Starting RIP simulation...\n")
    
    for i in range(MAX_ITERATIONS):
        print(f"--- Iteration {i + 1} ---")
        overall_tables_changed_in_this_iteration = False
        
        advertisements = {}
        for router_id, router in routers.items():
            advertisements[router_id] = router.get_advertisement()

        routers_changed_in_iteration = set()

        for router_id, router in routers.items():
            iteration_router_table_changed = False
            for neighbor_id, (neighbor_ip, direct_metric) in router.neighbors.items():
                neighbor_advertisement = advertisements.get(neighbor_id)
                if neighbor_advertisement:
                    if router.update_routing_table(neighbor_ip, neighbor_advertisement, direct_metric):
                        iteration_router_table_changed = True
            
            if iteration_router_table_changed:
                overall_tables_changed_in_this_iteration = True
                routers_changed_in_iteration.add(router_id)
        
        # Задание Б
        if overall_tables_changed_in_this_iteration:
            print(f"\n--- Tables after iteration {i + 1} (only changed or all if first meaningful iteration) ---")
            for r_id, r_obj in routers.items():
                print(f"Simulation step {i + 1} of router {r_obj.ip_address} table:")
                print(f"{'[Source IP]':<18} {'[Destination IP]':<20} {'[Next Hop]':<18} {'[Metric]':<8}")
                sorted_destinations = sorted(r_obj.routing_table.keys())
                for dest_ip in sorted_destinations:
                    next_hop_ip, metric = r_obj.routing_table[dest_ip]
                    print(f"{r_obj.ip_address:<18} {dest_ip:<20} {next_hop_ip:<18} {metric:<8}")
                print("")
            print("---------------------------------------------------------------------\n")

        if not overall_tables_changed_in_this_iteration:
            print(f"\nConvergence reached in {i + 1} iterations.")
            break
    else:
        print(f"\nReached maximum iterations ({MAX_ITERATIONS}). Convergence might not be complete.")
    
    print("\n--- Final Routing Tables ---")
    for r_id, r_obj in routers.items():
        print(f"Final state of router {r_obj.ip_address} table:")
        print(f"{'[Source IP]':<18} {'[Destination IP]':<20} {'[Next Hop]':<18} {'[Metric]':<8}")
        
        sorted_destinations = sorted(r_obj.routing_table.keys())
        for dest_ip in sorted_destinations:
            next_hop_ip, metric = r_obj.routing_table[dest_ip]
            print(f"{r_obj.ip_address:<18} {dest_ip:<20} {next_hop_ip:<18} {metric:<8}")
        print("")

if __name__ == "__main__":
    network_config = load_network_config(CONFIG_FILE)
    if network_config:
        initialized_routers = initialize_routers(network_config)
        simulate_rip(initialized_routers)
    else:
        print(f"Could not load network configuration from {CONFIG_FILE}") 