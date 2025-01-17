import networkx as nx
import math
from ..Utils.utils import Point

class PeopleGraph:
    def __init__(self, edge_threshold=-1):
        self.nx_graph = nx.Graph()
        self.edge_threshold = edge_threshold
        self.edges_calculated = False
        self.n_people = 0
        self.n_edges = 0
        self.n_groups = 0
        self.groups = []
        self.avg_people_distance = 0
        self.avg_machine_distance = 0
        self.max_weight = 0
        self.min_weight = 9999

    def init_graph(self):
        PeopleGraph.__init__(self, self.edge_threshold)

    def add_node(self, x, y, z=None):
        node = Point(x,y,z)
        self.nx_graph.add_node(node, pos=node.pos)
        return node.pos

    def add_edge(self, from_node, to_node, dist_threshold=-1):
        dist = from_node.distance_from(to_node)
        if dist_threshold > 0:
            if dist <= dist_threshold:
                if dist >= self.max_weight:
                    self.max_weight = dist
                if dist <= self.min_weight:
                    self.min_weight = dist
                self.nx_graph.add_edge(from_node, to_node, weight=dist)
            else:
                return dist
        else:
            self.nx_graph.add_edge(from_node, to_node, weight=dist)
        return dist
    
    def update_graph(self, machine_pos=None):
        try:
            self.calculate_edges()
            self.update_avg_distance()
            self.update_avg_machine_distance(machine_pos=machine_pos)
            self.n_people = self.nx_graph.number_of_nodes()
            self.n_edges = self.nx_graph.number_of_edges()
            if self.edge_threshold > 0:
                    self.groups = []
                    self.n_groups = 0
                    for c in connected_components(self.nx_graph):
                        subgraph = self.nx_graph.subgraph(c)
                        self.groups.append(subgraph)
                        self.n_groups = 1 if subgraph.number_of_nodes() > 1 else 0 # n gives the number of sub graphs
        except Exception as e:
            pass
            # print(f"Error ugrading graph {e}")

    def calculate_edges(self):
        for i in self.nx_graph.nodes():
            for j in self.nx_graph.nodes():
                if i != j:
                    if not self.nx_graph.has_edge(i, j):            
                        self.add_edge(i, j, self.edge_threshold)
        self.edges_calculated = True

    def update_avg_distance(self):
        n_edges = self.nx_graph.number_of_edges()
        if self.edges_calculated and n_edges > 0:
            total_distance = 0
            for i, j, w in self.nx_graph.edges(data=True):
                total_distance += w['weight']
                self.avg_people_distance = total_distance/n_edges
            return self.avg_people_distance
        return 0

    def update_avg_machine_distance(self, machine_pos=None):
        m_pos = machine_pos
        n_nodes = self.nx_graph.number_of_nodes()
        if self.edges_calculated and n_nodes > 0:
            total_distance_from_machine = 0
            for node, node_data in self.nx_graph.nodes(data=True):
                total_distance_from_machine += node.distance_from(m_pos)
            if n_nodes > 1:
                n_nodes -= 1
            self.avg_machine_distance = total_distance_from_machine/(n_nodes)
            return self.avg_machine_distance
        return 0

    def get_average_clustering(self):
        # if self.edges_calculated:
        #     return nx.average_clustering(self.nx_graph, weight='weight')
        return 0

    def draw_nx_graph(self):
        labels = nx.get_edge_attributes(self.nx_graph, 'weight')
        pos = nx.get_node_attributes(self.nx_graph, 'pos')
        nx.draw(self.nx_graph, pos)
        nx.draw_networkx_edge_labels(self.nx_graph, pos, edge_labels=labels)

    def normalize_weight(self, weight):
        normalized = (weight - self.min_weight) / (self.max_weight - self.min_weight)
        if normalized is None or math.isnan(normalized):
            normalized = 1
        return normalized

    def draw_nodes(self, logger, debug=False, surfaces=None):
        color = (255, 255, 255)
        for node, node_data in self.nx_graph.nodes(data=True):
            logger.draw_circle(Point(node.pos[0], node.pos[1]), (255, 255, 255), 3, 3, s_names=surfaces)

    def draw_edges(self, logger, debug=False, surfaces=None):
        if self.edges_calculated:
            thickness = 1
            # thickness = int((self.normalize_weight(w['weight'])+1) * 2)
            for i, j, w in self.nx_graph.edges(data=True):
                logger.draw_line(Point(i.pos[0], i.pos[1]), Point(j.pos[0], j.pos[1]), (0, 0, 255), thickness, s_names=surfaces)
                if debug:
                    print(f"thickness (max: {self.min_weight}, min: {self.max_weight}, Original: {w['weight']} Normalized: {thickness}")

    def draw_dist_from_machine(self, logger, m_pos, debug=False, surfaces=None):
        for node, node_data in self.nx_graph.nodes(data=True):
            logger.draw_line(Point(node.pos[0], node.pos[1]), Point(m_pos.x, m_pos.y), (255, 0, 0), 1, s_names=surfaces)
        logger.draw_circle(Point(m_pos.x, m_pos.y), (255, 255, 255), 3, 3, s_names=surfaces)

    def draw_debug_text(self, logger, start_pos, camera_n=0, debug=False, surfaces=None):
        nodes_data = ""
        for node in self.nx_graph.nodes():
            nodes_data = f"{nodes_data}, ({node.pos[0]:.2f}, {node.pos[1]:.2f})"
        nodes_data = f"[{nodes_data}]"
        edges_data = ""
        for i, j, w in self.nx_graph.edges(data=True):
            # edges_data = f"{edges_data}, ({i.pos[0]:.2f}, {i.pos[1]:.2f}, weight: {w['weight']:.2f}\n)"
            edges_data = f"{edges_data},{w['weight']:.2f}"
        edges_data = f"[{edges_data}]"

        color = (255, 255, 0)

        start_pos = logger.add_text_line(f"People {self.n_people}: {nodes_data}", color, start_pos, s_names=surfaces)
        start_pos = logger.add_text_line(f"Links {self.n_edges}: {edges_data}", color, start_pos, s_names=surfaces)
        start_pos = logger.add_text_line(f"Groups (n_nodes > 1) {self.n_groups}", color, start_pos, s_names=surfaces)
        start_pos = logger.add_text_line(f"Crowd Ratio {self.n_groups/self.n_people if self.n_people > 0 else 0}", color, start_pos, s_names=surfaces)
        start_pos = logger.add_text_line(f"Avg dist: {self.avg_people_distance:.2f}", color, start_pos, s_names=surfaces)
        start_pos = logger.add_text_line(f"Avg_m: {self.avg_machine_distance:.2f}", color, start_pos, s_names=surfaces)
        if debug:
            print(f"Camera {camera_n:<2} - Nodes: {self.nx_graph.number_of_nodes():<3} Edges: {self.nx_graph.number_of_edges():<3}")

    def get_graph_data(self):
        data = {}
        data["nodes"] = []
        data["edges"] = []
        for node, node_data in self.nx_graph.nodes(data=True):
            data["nodes"].append({'x': node.pos[0], 'y': node.pos[1]})
        for i, j, w in self.nx_graph.edges(data=True):
            data["edges"].append({'p1': {'x': i.pos[0], 'y': i.pos[1]},'p2': {'x': j.pos[0], 'y': j.pos[1]}, 'weight': w['weight']})
        return data


