import threading
import tkinter as tk
from tkinter import ttk
from scapy.all import sniff, IP, TCP, UDP, ARP, Ether
import time
import psutil
from collections import defaultdict

root = tk.Tk()
root.title("Network Analyzer")
root.geometry("1000x700")

# --- Main Notebook for Tabs ---
notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)

# --- Tab 1: Packet List & Details ---
tab_sniffer = ttk.Frame(notebook)
notebook.add(tab_sniffer, text="Packet List & Details")

# --- Controls for the sniffer tab (e.g., autoscroll checkbox) ---
controls_frame = ttk.Frame(tab_sniffer)
controls_frame.pack(fill=tk.X, pady=(0,5)) # Pack it above the tree_frame

autoscroll_var = tk.BooleanVar(value=True) # Autoscroll is ON by default
autoscroll_check = ttk.Checkbutton(controls_frame, text="Autoscroll", variable=autoscroll_var)
autoscroll_check.pack(side=tk.LEFT, padx=5)

# StringVars for live total traffic on sniffer tab
sniffer_tab_bytes_recv_var = tk.StringVar(value="Recv: 0 B")
sniffer_tab_bytes_sent_var = tk.StringVar(value="Sent: 0 B")

ttk.Label(controls_frame, textvariable=sniffer_tab_bytes_sent_var).pack(side=tk.RIGHT, padx=5)
ttk.Label(controls_frame, textvariable=sniffer_tab_bytes_recv_var).pack(side=tk.RIGHT, padx=5)

# Frame to hold Treeview and its scrollbar
tree_frame = ttk.Frame(tab_sniffer)
tree_frame.pack(fill=tk.BOTH, expand=True)

# --- Treeview for packet list (on tab_sniffer) ---
columns_sniffer = ("no", "time", "source", "destination", "protocol", "length", "info")

# Create scrollbars FIRST, then the tree
tree_sniffer_scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical")
tree_sniffer_scrollbar_x = ttk.Scrollbar(tree_frame, orient="horizontal")

tree_sniffer = ttk.Treeview(tree_frame, columns=columns_sniffer, show="headings", 
                    yscrollcommand=tree_sniffer_scrollbar_y.set, 
                    xscrollcommand=tree_sniffer_scrollbar_x.set)

tree_sniffer_scrollbar_y.config(command=tree_sniffer.yview)
tree_sniffer_scrollbar_x.config(command=tree_sniffer.xview)

# Layout: scrollbars first, then tree fills the rest
tree_sniffer_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
tree_sniffer_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
tree_sniffer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) # Tree fills remaining space

# Define column headings and properties
tree_sniffer.heading("no", text="No.")
tree_sniffer.column("no", width=50, minwidth=40, stretch=tk.NO, anchor="center")
tree_sniffer.heading("time", text="Time")
tree_sniffer.column("time", width=70, minwidth=60, stretch=tk.NO, anchor="center")
tree_sniffer.heading("source", text="Source")
tree_sniffer.column("source", width=200, minwidth=150)
tree_sniffer.heading("destination", text="Destination")
tree_sniffer.column("destination", width=200, minwidth=150)
tree_sniffer.heading("protocol", text="Protocol")
tree_sniffer.column("protocol", width=70, minwidth=50, stretch=tk.NO, anchor="center")
tree_sniffer.heading("length", text="Length")
tree_sniffer.column("length", width=60, minwidth=50, stretch=tk.NO, anchor="e")
tree_sniffer.heading("info", text="Info")
tree_sniffer.column("info", width=300, minwidth=200)

# --- Details Area (on tab_sniffer, below tree_frame) ---
details_text_sniffer = tk.Text(tab_sniffer, height=10, wrap=tk.WORD, state=tk.DISABLED, relief=tk.SUNKEN, borderwidth=1)
details_text_sniffer.pack(fill=tk.X, pady=(5,0), expand=False)

packets_sniffer_list = []
packet_sniffer_counter = 0

def on_select_sniffer(e):
    sel = tree_sniffer.selection()
    if not sel:
        return
    
    selected_item = tree_sniffer.item(sel[0])
    try:
        packet_index = int(selected_item['values'][0]) -1
    except (IndexError, ValueError):
        details_text_sniffer.config(state=tk.NORMAL)
        details_text_sniffer.delete(1.0, tk.END)
        details_text_sniffer.insert(tk.END, "Error fetching packet details from selection.")
        details_text_sniffer.config(state=tk.DISABLED)
        return

    if 0 <= packet_index < len(packets_sniffer_list):
        pkt = packets_sniffer_list[packet_index]
        detail_lines = []
        if IP in pkt:
            ip_layer = pkt[IP]
            detail_lines.append(f"IP Version: {ip_layer.version}")
            detail_lines.append(f"Header Length: {ip_layer.ihl*4} bytes")
            detail_lines.append(f"Type of Service (ToS): {ip_layer.tos}")
            detail_lines.append(f"Total Length (IP): {ip_layer.len}")
            detail_lines.append(f"Identification: {ip_layer.id}")
            detail_lines.append(f"Flags (IP): {str(ip_layer.flags)}")
            detail_lines.append(f"Fragment Offset: {ip_layer.frag}")
            detail_lines.append(f"TTL: {ip_layer.ttl}")
            detail_lines.append(f"Header Checksum (IP): {hex(ip_layer.chksum)}")
            detail_lines.append(f"Source IP: {ip_layer.src}")
            detail_lines.append(f"Destination IP: {ip_layer.dst}")
            
            protocol_name = "Unknown"
            src_port = "N/A"
            dst_port = "N/A"

            if TCP in pkt:
                protocol_name = "TCP"
                tcp_layer = pkt[TCP]
                src_port = tcp_layer.sport
                dst_port = tcp_layer.dport
                detail_lines.append(f"Source Port: {src_port}")
                detail_lines.append(f"Destination Port: {dst_port}")
                detail_lines.append(f"Sequence: {tcp_layer.seq}")
                detail_lines.append(f"Acknowledgment: {tcp_layer.ack}")
                detail_lines.append(f"Data Offset (TCP Header Length): {tcp_layer.dataofs*4} bytes")
                flags_str_list = []
                if tcp_layer.flags.F: flags_str_list.append("FIN")
                if tcp_layer.flags.S: flags_str_list.append("SYN")
                if tcp_layer.flags.R: flags_str_list.append("RST")
                if tcp_layer.flags.P: flags_str_list.append("PSH")
                if tcp_layer.flags.A: flags_str_list.append("ACK")
                if tcp_layer.flags.U: flags_str_list.append("URG")
                if tcp_layer.flags.E: flags_str_list.append("ECE")
                if tcp_layer.flags.C: flags_str_list.append("CWR")
                detail_lines.append(f"Flags (TCP): {str(tcp_layer.flags)} ({', '.join(flags_str_list) if flags_str_list else 'None'})")
                detail_lines.append(f"Window Size: {tcp_layer.window}")
                detail_lines.append(f"Checksum (TCP): {hex(tcp_layer.chksum)}")
                detail_lines.append(f"Urgent Pointer: {tcp_layer.urgptr}")
                if tcp_layer.options:
                    opts_str = ", ".join([f"{opt[0]}:{opt[1]}" for opt in tcp_layer.options])
                    detail_lines.append(f"Options (TCP): {opts_str}")

            elif UDP in pkt:
                protocol_name = "UDP"
                udp_layer = pkt[UDP]
                src_port = udp_layer.sport
                dst_port = udp_layer.dport
                detail_lines.append(f"Source Port: {src_port}")
                detail_lines.append(f"Destination Port: {dst_port}")
                detail_lines.append(f"Length (UDP): {udp_layer.len}")
                detail_lines.append(f"Checksum (UDP): {hex(udp_layer.chksum)}")
            elif pkt.haslayer(IP) and not pkt.haslayer(TCP) and not pkt.haslayer(UDP):
                protocol_name = f"IP/{ip_layer.proto}"

            detail_lines.insert(2, f"Protocol: {protocol_name} (IP Proto Number: {ip_layer.proto})")
            detail_lines.append(f"Payload Length: {len(ip_layer.payload)} bytes")
            detail_lines.append(f"Total Captured Length: {len(pkt)} bytes")

        elif ARP in pkt:
            arp_layer = pkt[ARP]
            detail_lines.append("Protocol: ARP")
            detail_lines.append(f"Hardware Type: {arp_layer.hwtype} ({'Ethernet' if arp_layer.hwtype == 1 else 'Unknown'})")
            detail_lines.append(f"Protocol Type: {hex(arp_layer.ptype)} ({'IPv4' if arp_layer.ptype == 0x0800 else 'Unknown'})")
            detail_lines.append(f"Hardware Size: {arp_layer.hwlen}")
            detail_lines.append(f"Protocol Size: {arp_layer.plen}")
            op_type = "request" if arp_layer.op == 1 else "reply" if arp_layer.op == 2 else f"op {arp_layer.op}"
            detail_lines.append(f"Operation: {op_type}")
            detail_lines.append(f"Sender MAC: {arp_layer.hwsrc}")
            detail_lines.append(f"Sender IP: {arp_layer.psrc}")
            detail_lines.append(f"Target MAC: {arp_layer.hwdst}")
            detail_lines.append(f"Target IP: {arp_layer.pdst}")
            detail_lines.append(f"Total Captured Length: {len(pkt)} bytes")
        else:
            detail_lines.append("Non-IP/ARP Packet")
            detail_lines.append(pkt.summary())
        
        details_text_sniffer.config(state=tk.NORMAL)
        details_text_sniffer.delete(1.0, tk.END)
        details_text_sniffer.insert(tk.END, "\n".join(detail_lines))
        details_text_sniffer.config(state=tk.DISABLED)

tree_sniffer.bind('<<TreeviewSelect>>', on_select_sniffer)

def add_packet_to_sniffer_list(pkt):
    global packet_sniffer_counter
    packet_sniffer_counter += 1
    packets_sniffer_list.append(pkt)

    pkt_time = time.strftime('%H:%M:%S', time.localtime(pkt.time))
    
    source = "N/A"
    destination = "N/A"
    protocol_str = "N/A"
    length = len(pkt)
    info = pkt.summary()

    if IP in pkt:
        ip_layer = pkt[IP]
        source = ip_layer.src
        destination = ip_layer.dst
        
        if TCP in pkt:
            protocol_str = "TCP"
            source += f":{pkt[TCP].sport}"
            destination += f":{pkt[TCP].dport}"
            flags_str = str(pkt[TCP].flags)
            info = f"{pkt[TCP].sport} > {pkt[TCP].dport} [{flags_str}] Seq={pkt[TCP].seq} Ack={pkt[TCP].ack} Win={pkt[TCP].window}"
        elif UDP in pkt:
            protocol_str = "UDP"
            source += f":{pkt[UDP].sport}"
            destination += f":{pkt[UDP].dport}"
            info = f"{pkt[UDP].sport} > {pkt[UDP].dport} Len={pkt[UDP].len}"
        else: 
            protocol_str = f"IP/{ip_layer.proto}"
            info = pkt.summary().split(" > ",1)[1] if (" > " in pkt.summary() and len(pkt.summary().split(" > ",1)) > 1) else pkt.summary()

    elif ARP in pkt:
        protocol_str = "ARP"
        source = pkt[ARP].psrc
        destination = pkt[ARP].pdst
        op_type = "request" if pkt[ARP].op == 1 else "reply"
        info = f"Who has {pkt[ARP].pdst}? Tell {pkt[ARP].psrc}" if op_type == "request" else f"{pkt[ARP].psrc} is at {pkt[ARP].hwsrc}"

    elif Ether in pkt:
        source, destination, protocol_str = pkt[Ether].src, pkt[Ether].dst, hex(pkt[Ether].type)

    values = (packet_sniffer_counter, pkt_time, source, destination, protocol_str, length, info)
    item_id = tree_sniffer.insert("", tk.END, values=values)
    if autoscroll_var.get():
        if packet_sniffer_counter > 20 and packet_sniffer_counter % 10 == 0:
            tree_sniffer.see(item_id)

# --- Tab 2: Port Traffic ---
tab_ports = ttk.Frame(notebook)
notebook.add(tab_ports, text="Port Traffic")

port_stats_controls_frame = ttk.Frame(tab_ports)
port_stats_controls_frame.pack(fill=tk.X, pady=5)

port_sniff_thread = None
port_sniff_stop_event = threading.Event()
port_statistics = defaultdict(lambda: {"bytes": 0, "packets": 0})

columns_ports = ("protocol", "src_port", "dst_port", "packets", "bytes")
tree_ports = ttk.Treeview(tab_ports, columns=columns_ports, show="headings")
tree_ports.heading("protocol", text="Protocol"); tree_ports.column("protocol", width=80, anchor="center")
tree_ports.heading("src_port", text="Source Port"); tree_ports.column("src_port", width=100, anchor="center")
tree_ports.heading("dst_port", text="Dest. Port"); tree_ports.column("dst_port", width=100, anchor="center")
tree_ports.heading("packets", text="Packets"); tree_ports.column("packets", width=80, anchor="e")
tree_ports.heading("bytes", text="Bytes"); tree_ports.column("bytes", width=100, anchor="e")
tree_ports.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0,5))

def handle_port_packet(pkt):
    if IP in pkt:
        proto_num = pkt[IP].proto
        proto_name = "OTHER"
        length = len(pkt)
        sport, dport = "N/A", "N/A"

        if TCP in pkt:
            proto_name = "TCP"
            sport, dport = pkt[TCP].sport, pkt[TCP].dport
        elif UDP in pkt:
            proto_name = "UDP"
            sport, dport = pkt[UDP].sport, pkt[UDP].dport
        
        if sport != "N/A":
            key = (proto_name, sport, dport)
            port_statistics[key]["bytes"] += length
            port_statistics[key]["packets"] += 1

def update_port_treeview():
    for i in tree_ports.get_children():
        tree_ports.delete(i)
    sorted_stats = sorted(port_statistics.items(), key=lambda item: item[1]["bytes"], reverse=True)
    for (proto, sport, dport), stats_dict in sorted_stats:
        tree_ports.insert("", tk.END, values=(proto, sport, dport, stats_dict["packets"], f"{stats_dict['bytes']:,} B"))

def do_port_sniff():
    port_sniff_stop_event.clear()
    port_statistics.clear()
    update_port_treeview()
    sniff(prn=handle_port_packet, store=False, stop_filter=lambda p: port_sniff_stop_event.is_set())
    update_port_treeview()
    port_btn_start.config(state=tk.NORMAL)
    port_btn_stop.config(state=tk.DISABLED)

def start_port_sniff():
    global port_sniff_thread
    port_btn_start.config(state=tk.DISABLED)
    port_btn_stop.config(state=tk.NORMAL)
    port_sniff_thread = threading.Thread(target=do_port_sniff, daemon=True)
    port_sniff_thread.start()

def stop_port_sniff():
    port_sniff_stop_event.set()

port_btn_start = ttk.Button(port_stats_controls_frame, text="Start Sniffing", command=start_port_sniff)
port_btn_start.pack(side=tk.LEFT, padx=5)
port_btn_stop = ttk.Button(port_stats_controls_frame, text="Stop and Refresh", command=stop_port_sniff, state=tk.DISABLED)
port_btn_stop.pack(side=tk.LEFT, padx=5)

# --- Tab 3: Total Traffic ---
tab_total = ttk.Frame(notebook)
notebook.add(tab_total, text="Total Traffic")

# Variables for total traffic stats
total_bytes_sent_var = tk.StringVar(value="0 B")
total_bytes_recv_var = tk.StringVar(value="0 B")
total_pkts_sent_var = tk.StringVar(value="0")
total_pkts_recv_var = tk.StringVar(value="0")

# Layout for total traffic stats
stats_frame_total = ttk.Frame(tab_total)
stats_frame_total.pack(padx=10, pady=10, anchor="nw")

ttk.Label(stats_frame_total, text="Bytes Sent:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
ttk.Label(stats_frame_total, textvariable=total_bytes_sent_var).grid(row=0, column=1, sticky="w", padx=5, pady=2)
ttk.Label(stats_frame_total, text="Bytes Received:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
ttk.Label(stats_frame_total, textvariable=total_bytes_recv_var).grid(row=1, column=1, sticky="w", padx=5, pady=2)
ttk.Label(stats_frame_total, text="Packets Sent:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
ttk.Label(stats_frame_total, textvariable=total_pkts_sent_var).grid(row=2, column=1, sticky="w", padx=5, pady=2)
ttk.Label(stats_frame_total, text="Packets Received:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
ttk.Label(stats_frame_total, textvariable=total_pkts_recv_var).grid(row=3, column=1, sticky="w", padx=5, pady=2)

def update_total_traffic():
    # Initialize values for the first tab's live counters as well
    try:
        initial_counters_psutil = psutil.net_io_counters()
        sniffer_tab_bytes_recv_var.set(f"Recv: {initial_counters_psutil.bytes_recv:,} B")
        sniffer_tab_bytes_sent_var.set(f"Sent: {initial_counters_psutil.bytes_sent:,} B")
        total_bytes_sent_var.set(f"{initial_counters_psutil.bytes_sent:,} B")
        total_bytes_recv_var.set(f"{initial_counters_psutil.bytes_recv:,} B")
        total_pkts_sent_var.set(f"{initial_counters_psutil.packets_sent:,}")
        total_pkts_recv_var.set(f"{initial_counters_psutil.packets_recv:,}")
    except Exception as e:
        print(f"Error initializing total traffic: {e}")
        # Set to default error values if psutil fails initially
        default_error_val = "Error"
        sniffer_tab_bytes_recv_var.set(f"Recv: {default_error_val}")
        sniffer_tab_bytes_sent_var.set(f"Sent: {default_error_val}")
        total_bytes_sent_var.set(default_error_val)
        total_bytes_recv_var.set(default_error_val)
        total_pkts_sent_var.set(default_error_val)
        total_pkts_recv_var.set(default_error_val)

    while True: 
        try:
            if not root.winfo_exists(): break
            counters = psutil.net_io_counters()
            
            # Update for Tab 3 (Total Traffic)
            total_bytes_sent_var.set(f"{counters.bytes_sent:,} B")
            total_bytes_recv_var.set(f"{counters.bytes_recv:,} B")
            total_pkts_sent_var.set(f"{counters.packets_sent:,}")
            total_pkts_recv_var.set(f"{counters.packets_recv:,}")

            # Update for Tab 1 (Packet List & Details) live counters
            sniffer_tab_bytes_recv_var.set(f"Recv: {counters.bytes_recv:,} B")
            sniffer_tab_bytes_sent_var.set(f"Sent: {counters.bytes_sent:,} B")
            
            time.sleep(1) 
        except tk.TclError: break 
        except Exception as e: 
            print(f"Error in update_total_traffic: {e}")
            # Optionally set error values in GUI if psutil fails during loop
            error_update_val = "Error updating"
            sniffer_tab_bytes_recv_var.set(f"Recv: {error_update_val}")
            sniffer_tab_bytes_sent_var.set(f"Sent: {error_update_val}")
            # Consider if tab 3 also needs error state display on loop failure
            break

# Start packet sniffer for the first tab
threading.Thread(target=lambda: sniff(prn=add_packet_to_sniffer_list, store=False, filter=""), daemon=True).start()

# Start total traffic update thread for the third tab
total_traffic_thread = threading.Thread(target=update_total_traffic, daemon=True)
total_traffic_thread.start()

root.mainloop() 