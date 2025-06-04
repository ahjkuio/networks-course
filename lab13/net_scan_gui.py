import threading
import tkinter as tk
from tkinter import ttk
import ipaddress
from scapy.all import ARP, Ether, srp
import socket
import psutil
import time


def get_local_network_info():
    """
    Tries to determine local IP, MAC, hostname, and network CIDR.
    """
    hostname = socket.gethostname()
    local_ip = ""
    local_mac = ""
    network_cidr = "192.168.1.0/24" # Default
    
    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80)) 
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        try:
            local_ip = socket.gethostbyname(hostname)
        except socket.gaierror:
            local_ip = "127.0.0.1"

    best_iface = None
    if_addrs = psutil.net_if_addrs()

    for interface_name, snic_list in if_addrs.items():
        for snic in snic_list:
            if snic.family == socket.AF_INET and snic.address == local_ip:
                best_iface = interface_name
                if hasattr(snic, 'address') and hasattr(snic, 'netmask') and hasattr(snic, 'broadcast'): 

                    for snic_mac_check in if_addrs.get(interface_name, []):
                        if snic_mac_check.family == psutil.AF_LINK:
                             local_mac = snic_mac_check.address.replace('-', ':').lower()
                             break
                    if local_mac and snic.netmask:
                        try:
                            ip_interface = ipaddress.ip_interface(f'{local_ip}/{snic.netmask}')
                            network_cidr = str(ip_interface.network)
                            return {
                                "ip": local_ip, 
                                "mac": local_mac if local_mac else "N/A",
                                "hostname": hostname,
                                "network_cidr": network_cidr
                            }
                        except ValueError:
                            pass

            if not local_ip and snic.family == socket.AF_INET and not snic.address.startswith("127."):
                temp_ip = snic.address
                temp_mac = ""
                for snic_mac_check_fb in if_addrs.get(interface_name, []):
                    if snic_mac_check_fb.family == psutil.AF_LINK:
                        temp_mac = snic_mac_check_fb.address.replace('-', ':').lower()
                        break
                if temp_mac and hasattr(snic, 'netmask') and snic.netmask:
                    try:
                        ip_interface = ipaddress.ip_interface(f'{temp_ip}/{snic.netmask}')
                        return {
                            "ip": temp_ip,
                            "mac": temp_mac,
                            "hostname": hostname,
                            "network_cidr": str(ip_interface.network)
                        }
                    except ValueError:
                         pass
    
    for interface_name, snic_list in if_addrs.items():
        for snic in snic_list:
            if snic.family == socket.AF_INET and not snic.address.startswith("127.") and hasattr(snic, 'netmask') and snic.netmask:
                mac_addr = "N/A"
                for snic_mac in if_addrs.get(interface_name, []):
                    if snic_mac.family == psutil.AF_LINK:
                        mac_addr = snic_mac.address.replace('-', ':').lower()
                        break
                try:
                    ip_iface_obj = ipaddress.ip_interface(f'{snic.address}/{snic.netmask}')
                    return {
                        "ip": snic.address,
                        "mac": mac_addr,
                        "hostname": hostname,
                        "network_cidr": str(ip_iface_obj.network)
                    }
                except ValueError:
                    continue

    return {"ip": local_ip if local_ip else "N/A", "mac": "N/A", "hostname": hostname, "network_cidr": network_cidr}


def resolve_hostname(ip_address):
    try:
        name, _, _ = socket.gethostbyaddr(ip_address)
        return name
    except socket.herror: 
        return "Unknown"
    except socket.gaierror: 
        return "Unknown (gaierror)"
    except Exception:
        return "Unknown (error)"

def scan_network_thread(network_cidr_str, tree, progress_bar, local_info, root_tk):
    try:
        network = ipaddress.ip_network(network_cidr_str, strict=False)
    except ValueError:
        root_tk.after(0, lambda: update_tree(tree, local_info["ip"], "Invalid Network", "Error", True, is_local=False, error_msg=f"Invalid network: {network_cidr_str}"))
        root_tk.after(0, lambda: progress_bar.config(value=100))
        return

    all_ips = list(network.hosts())
    total_ips = len(all_ips)
    progress_bar['value'] = 0


    for i, ip_obj in enumerate(all_ips):
        ip_str = str(ip_obj)
        if ip_str == local_info["ip"]:
            root_tk.after(0, lambda p=i: progress_bar.config(value=(p + 1) / total_ips * 100))
            continue

        if not root_tk.winfo_exists():
            return

        ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip_str), timeout=0.1, verbose=0, iface_hint=local_info.get("ip"))
        mac_address = "N/A"
        hostname = "N/A"

        if ans:
            mac_address = ans[0][1].hwsrc
            hostname = resolve_hostname(ip_str)
            root_tk.after(0, update_tree, tree, ip_str, mac_address, hostname, False, False)
        else:
            pass 
            
        current_progress = (i + 1) / total_ips * 100
        root_tk.after(0, lambda p=current_progress: progress_bar.config(value=p))

    root_tk.after(0, lambda: progress_bar.config(value=100))
    root_tk.after(0, lambda: scan_button.config(state=tk.NORMAL))


def update_tree(tree, ip, mac, name, is_first, is_local, error_msg=None):
    if error_msg: 
        tree.insert("", tk.END, values=("Error", error_msg, ""))
        return

    display_name = name
    if is_local:
        display_name += " <- Ваш компьютер"
    
    if is_first:
        tree.insert("", 0, values=(ip, mac, display_name))
    else:
        tree.insert("", tk.END, values=(ip, mac, display_name))


# --- GUI Setup ---
root = tk.Tk()
root.title("Network Scanner")
root.geometry("600x450")

input_frame = ttk.Frame(root, padding="10")
input_frame.pack(fill=tk.X)

ttk.Label(input_frame, text="Network (e.g., 192.168.1.0/24):").pack(side=tk.LEFT, padx=(0, 5))
network_entry = ttk.Entry(input_frame, width=40)
network_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

initial_local_info = get_local_network_info()
network_entry.insert(0, initial_local_info["network_cidr"])

scan_button = ttk.Button(input_frame, text="Scan Network")
scan_button.pack(side=tk.LEFT, padx=(5,0))


progress_bar = ttk.Progressbar(root, orient="horizontal", length=100, mode="determinate")
progress_bar.pack(fill=tk.X, padx=10, pady=5)

columns = ("ip", "mac", "hostname")
results_tree = ttk.Treeview(root, columns=columns, show="headings")
results_tree.heading("ip", text="IP-адрес")
results_tree.heading("mac", text="MAC-адрес")
results_tree.heading("hostname", text="Имя хоста")

results_tree.column("ip", width=150, anchor="w")
results_tree.column("mac", width=150, anchor="w")
results_tree.column("hostname", width=250, anchor="w")

results_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))


# --- Scan Action ---
scan_thread = None

def start_scan():
    global scan_thread, initial_local_info
    
    scan_button.config(state=tk.DISABLED)
    progress_bar['value'] = 0
    results_tree.delete(*results_tree.get_children())

    update_tree(results_tree, 
                initial_local_info["ip"], 
                initial_local_info["mac"], 
                initial_local_info["hostname"], 
                is_first=True, 
                is_local=True)

    network_to_scan = network_entry.get()
    
    scan_thread = threading.Thread(target=scan_network_thread, 
                                 args=(network_to_scan, results_tree, progress_bar, initial_local_info, root),
                                 daemon=True)
    scan_thread.start()

scan_button.config(command=start_scan)


# --- Main Loop ---
root.mainloop() 