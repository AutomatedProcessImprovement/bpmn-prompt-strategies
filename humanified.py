import xml.etree.ElementTree as ET
import networkx as nx


def bpmn_to_directed_graph(bpmn_file):
    """
        Convert BPMN file into a directed graph with relevant node information
    """
    tree = ET.parse(bpmn_file)
    root = tree.getroot()

    namespaces = {'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
    dg = nx.DiGraph()

    for process in root.findall('.//bpmn2:process', namespaces):
        #Add nodes (IDs as keys, labels as an attribute)
        for task in process.findall('.//bpmn2:task', namespaces):
            task_id = task.get('id')
            task_name = task.get('name', task_id)
            dg.add_node(task_id, label=task_name, type='task')

        for gateway in process.findall('.//bpmn2:parallelGateway', namespaces):
            gateway_id = gateway.get('id')
            gateway_name = gateway.get('name', gateway_id)
            if "split" in gateway_name.lower():
                gateway_label = "AND-split"
            elif "join" in gateway_name.lower():
                gateway_label = "AND-join"
            else:
                gateway_label = gateway_name
            dg.add_node(gateway_id, label=gateway_label, type='gateway')

        for gateway in process.findall('.//bpmn2:exclusiveGateway', namespaces):
            gateway_id = gateway.get('id')
            gateway_name = gateway.get('name', gateway_id)
            if "split" in gateway_name.lower():
                gateway_label = "OR-split"
            elif "join" in gateway_name.lower():
                gateway_label = "OR-join"
            else:
                gateway_label = gateway_name
            dg.add_node(gateway_id, label=gateway_label, type='gateway')

        for start_event in process.findall('.//bpmn2:startEvent', namespaces):
            event_id = start_event.get('id')
            event_name = start_event.get('name', event_id)
            dg.add_node(event_id, label=event_name, type='event')

        for end_event in process.findall('.//bpmn2:endEvent', namespaces):
            event_id = end_event.get('id')
            event_name = end_event.get('name', event_id)
            dg.add_node(event_id, label=event_name, type='event')

        # 2) Add edges by ID
        for flow in process.findall('.//bpmn2:sequenceFlow', namespaces):
            src = flow.get('sourceRef')
            tgt = flow.get('targetRef')
            if src in dg and tgt in dg:
                dg.add_edge(src, tgt)

    return dg

def remove_isolated_nodes(dg):
    """
    Remove all nodes from the directed graph that have degree 0.
    """
    isolated = [n for n in dg.nodes() if dg.degree(n) == 0]
    dg.remove_nodes_from(isolated)
    return dg

def remove_join_gateways(dg):
    """
    Remove 'AND-join' or 'OR-join' nodes by connecting each predecessor
    directly to each successor, then removing the join node.
    """
    joins = []
    for node_id in list(dg.nodes()):
        label = dg.nodes[node_id].get('label', '')
        if 'join' in label.lower():
            joins.append(node_id)

    for jn in joins:
        preds = list(dg.predecessors(jn))
        succs = list(dg.successors(jn))
        dg.remove_node(jn)
        for p in preds:
            for s in succs:
                dg.add_edge(p, s)

def detect_and_remove_splits(dg):
    """
    Find 'AND-split' or 'OR-split' gateway nodes.
    Return a dict: { predecessor_id: (splitType, [successors...]) }
    Then remove those gateway nodes from the graph and rewire.
    """
    split_map = {}
    split_nodes = []

    for node_id in list(dg.nodes()):
        label = dg.nodes[node_id].get('label', '')
        node_type = dg.nodes[node_id].get('type', '')
        if node_type == 'gateway' and 'split' in label.lower():
            split_nodes.append(node_id)

    for sn in split_nodes:
        label = dg.nodes[sn].get('label', '')
        preds = list(dg.predecessors(sn))
        succs = list(dg.successors(sn))

        if len(preds) == 1 and len(succs) >= 2:
            gateway_type = 'AND' if 'and-split' in label.lower() else 'OR'
            p = preds[0]
            #Map so we can print "From [p] to [s1] AND [s2]..."
            split_map[p] = (gateway_type, succs)

        # Remove the gateway, connect p -> each successor
        for p in preds:
            for s in succs:
                dg.add_edge(p, s)
        dg.remove_node(sn)

    return split_map

def bfs_print(dg):
    """
    BFS-based approach to print lines in a rough order.

    1) Remove join gateways.
    2) Detect & remove split gateways; store them in split_map.
    3) Identify start nodes (nodes with in-degree=0).
    4) For each start node, run a BFS:
       - If the current node is in split_map, print "From [X] to [Y] AND [Z]..."
       - Otherwise, for each successor: print "From [X] to [Y]"
       - Mark visited nodes so we don't loop infinitely on cycles.
    """
    remove_join_gateways(dg)
    split_map = detect_and_remove_splits(dg)

    start_nodes = [n for n in dg.nodes() if dg.in_degree(n) == 0]
    if not start_nodes:
        start_nodes = list(dg.nodes())

    visited = set()
    lines = []

    #BFS from each start node in ascending order
    start_nodes.sort()
    queue = list(start_nodes)

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        current_label = dg.nodes[current].get('label', current)

        if current in split_map:
            split_type, successors = split_map[current]
            successors_str = f' {split_type} '.join(
                f"[{dg.nodes[s].get('label', s)}]" for s in successors
            )
            lines.append(f"From [{current_label}] to {successors_str}")
            #We'll enqueue successors, but skip printing them as normal edges below
            for s in successors:
                if s not in visited:
                    queue.append(s)
        else:
            #No split, just print each edge
            for succ in dg.successors(current):
                succ_label = dg.nodes[succ].get('label', succ)
                lines.append(f"From [{current_label}] to [{succ_label}]")
                if succ not in visited:
                    queue.append(succ)

    #Print all lines in BFS-discovery order
    for line in lines:
        print(line)


if __name__ == '__main__':
    bpmn_file = 'models/main/level 3/process_020/process_020.bpmn'
    directed_graph = bpmn_to_directed_graph(bpmn_file)

    remove_isolated_nodes(directed_graph)

    print('This BPMN process flow represents a structured sequence of tasks. Each task leads to one or more subsequent tasks.\n')
    bfs_print(directed_graph)

    print("""\nExplanations for edge types:

"From [A] to [B]" denotes a sequential flow indicating that B is executed after A happened.
"From [A] to [B] and [C]" denotes a flow indicating that both B and C are executed after A happened.
"From [A] to [B] or [C]" denotes a flow indicating that either B or C (but only one) can be executed after A happened.""")
