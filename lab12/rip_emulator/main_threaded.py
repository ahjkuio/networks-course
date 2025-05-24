import json
import time
import threading
from router_threaded import RouterThread, UPDATE_INTERVAL

CONFIG_FILE = 'network_config.json'
SIMULATION_DURATION_MULTIPLIER = 4 

def load_network_config(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config

def main():
    network_config = load_network_config(CONFIG_FILE)
    if not network_config:
        print(f"Error: Could not load network configuration from {CONFIG_FILE}")
        return

    router_threads = {}
    all_router_queues = {}
    router_id_to_ip = {}

    print("Initializing router threads...")
    
    for r_data in network_config['routers']:
        router_id = r_data['id']
        ip_address = r_data['ip']
        router_id_to_ip[router_id] = ip_address
        
        thread = RouterThread(router_id, ip_address, all_router_queues)
        router_threads[router_id] = thread
        all_router_queues[router_id] = thread.in_queue

    for r_data in network_config['routers']:
        current_router_id = r_data['id']
        current_thread = router_threads[current_router_id]
        
        for link_data in network_config['links']:
            if link_data['from'] == current_router_id:
                neighbor_id = link_data['to']
                neighbor_ip = router_id_to_ip.get(neighbor_id)
                metric = link_data['metric']
                if neighbor_ip:
                    current_thread.add_neighbor_link(neighbor_id, neighbor_ip, metric)
                else:
                    print(f"Warning: Neighbor IP for {neighbor_id} not found when linking from {current_router_id}")
    
    print("\nStarting RIP simulation with threads...")
    for router_id, thread in router_threads.items():
        thread.start()

    num_routers = len(network_config['routers'])

    estimated_convergence_time = num_routers * UPDATE_INTERVAL 
    simulation_time_seconds = estimated_convergence_time * SIMULATION_DURATION_MULTIPLIER
    simulation_time_seconds = max(simulation_time_seconds, 15)
    
    print(f"Simulation will run for approximately {simulation_time_seconds:.1f} seconds.")
    print(f"(Based on ~{SIMULATION_DURATION_MULTIPLIER} update cycles for {num_routers} routers with {UPDATE_INTERVAL}s interval)")
    
    time.sleep(simulation_time_seconds)

    print("\nStopping router threads...")
    for router_id, thread in router_threads.items():
        thread.stop()
    
    for router_id, thread in router_threads.items():
        thread.join(timeout=UPDATE_INTERVAL + 2)
        if thread.is_alive():
            print(f"Warning: Router thread {router_id} did not stop gracefully.")

    print("\n--- Final Routing Tables (Threaded Simulation) ---")
    for router_id, thread_obj in router_threads.items():
        table_lines = thread_obj.get_formatted_routing_table()
        print(f"Final state of router {thread_obj.ip_address} table:")
        print(f"{"[Source IP]":<18} {"[Destination IP]":<20} {"[Next Hop]":<18} {"[Metric]":<8}")
        for line in table_lines:
            print(line)
        print("")

if __name__ == "__main__":
    main() 