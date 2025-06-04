import argparse
import json
import copy


class Node:
    def __init__(self, idx, neighbors):
        self.id = idx
        self.neighbors = neighbors  # dict neighbor -> cost
        self.table = {idx: (0, idx)}  # dest -> (cost, next_hop)

    def send_vector(self):
        return {dest: cost for dest, (cost, _) in self.table.items()}

    def update(self, frm, vector):
        changed = False
        cost_to_neighbor = self.neighbors[frm]
        for dest, cost in vector.items():
            new_cost = cost + cost_to_neighbor
            if dest not in self.table or new_cost < self.table[dest][0]:
                # нашли лучший маршрут
                self.table[dest] = (new_cost, frm)
                changed = True
            elif self.table[dest][1] == frm and new_cost != self.table[dest][0]:
                # маршрут через того же соседа ухудшился/улучшился
                self.table[dest] = (new_cost, frm)
                changed = True
        return changed

    def __str__(self):
        lines = [f"Routing table for node {self.id}"]
        for dest, (cost, via) in sorted(self.table.items()):
            lines.append(f"  to {dest}: cost {cost} via {via}")
        return "\n".join(lines)


class Network:
    def __init__(self, edges):
        self.nodes = {}
        for a, b, w in edges:
            for x, y in [(a, b), (b, a)]:
                self.nodes.setdefault(x, {})[y] = w
        self.nodes = {i: Node(i, nbrs) for i, nbrs in self.nodes.items()}

    def iterate(self):
        changed = False
        for node in self.nodes.values():
            vec = node.send_vector()
            for neigh in node.neighbors:
                if self.nodes[neigh].update(node.id, vec):
                    changed = True
        return changed

    def run_until_converge(self):
        while self.iterate():
            pass

    def update_edge(self, a, b, new_w):
        self.nodes[a].neighbors[b] = new_w
        self.nodes[b].neighbors[a] = new_w
        self.run_until_converge()

    def dump(self):
        for node in self.nodes.values():
            print(node)
            print()


def parse_edges(text):
    edges = []
    for part in text.split():
        a, b, w = part.split(',')
        edges.append((int(a), int(b), int(w)))
    return edges


def main():
    p = argparse.ArgumentParser(description='Distance vector simulator')
    p.add_argument('--edges', required=True, help='Edge list "0,1,1 1,2,3"')
    p.add_argument('--update', help='Edge update "a,b,new_w"')
    args = p.parse_args()
    net = Network(parse_edges(args.edges))
    net.run_until_converge()
    print('Initial tables:')
    net.dump()
    if args.update:
        a, b, w = map(int, args.update.split(','))
        net.update_edge(a, b, w)
        print(f'After update {a}-{b}={w}:')
        net.dump()


if __name__ == '__main__':
    main() 