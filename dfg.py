import networkx as nx
import xml.etree.ElementTree as ET

def bpmn_to_directed_graph(bpmn_file):
    """
        Convert BPMN file into a directed graph with relevant node information
    """

    tree = ET.parse(bpmn_file)
    root = tree.getroot()

    namespaces = {'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}

    dg = nx.DiGraph()

    # Add nodes and edges based on BPMN elements
    for process in root.findall('.//bpmn2:process', namespaces):
        for task in process.findall('.//bpmn2:task', namespaces):
            task_id = task.get('id')
            task_name = task.get('name', task_id)  #Use name, fallback to ID
            dg.add_node(task_id, label=task_name, type='task')

        #Parallel AND gateways
        for gateway in process.findall('.//bpmn2:parallelGateway', namespaces):
            gateway_id = gateway.get('id')
            gateway_name = gateway.get('name', gateway_id)

            # Identify AND-split and AND-join
            if "split" in gateway_name.lower():
                gateway_label = "AND-split"
            elif "join" in gateway_name.lower():
                gateway_label = "AND-join"
            else:
                gateway_label = gateway_name

            dg.add_node(gateway_id, label=gateway_label, type='gateway')

        #Inclusive OR gateways
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

        # Add start and end events
        for start_event in process.findall('.//bpmn2:startEvent', namespaces):
            event_id = start_event.get('id')
            event_name = start_event.get('name', event_id)
            dg.add_node(event_id, label=event_name, type='event')

        for end_event in process.findall('.//bpmn2:endEvent', namespaces):
            event_id = end_event.get('id')
            event_name = end_event.get('name', event_id)
            dg.add_node(event_id, label=event_name, type='event')

        #Identify nodes as gateways
        gateway_ids = set()
        for elem in root.iter():
            if elem.tag.endswith('exclusiveGateway') or elem.tag.endswith('parallelGateway'):
                gateway_ids.add(elem.attrib['id'])

        #Edges based on sequence flows
        for flow in process.findall('.//bpmn2:sequenceFlow', namespaces):
            source_ref = flow.get('sourceRef')
            target_ref = flow.get('targetRef')

            # Get the source and target labels using the ID
            source_label = dg.nodes[source_ref].get('label', source_ref) if source_ref in dg else source_ref
            target_label = dg.nodes[target_ref].get('label', target_ref) if target_ref in dg else target_ref

            edge_data = {}

            #Check if the source or target is a gateway
            if source_ref in gateway_ids:
                edge_data['gateway_id'] = source_ref
            elif target_ref in gateway_ids:
                edge_data['gateway_id'] = target_ref

            dg.add_edge(source_label, target_label, **edge_data)

    return dg

def print_dfg(dg):
    """
        Print a human-readable description of a directly-follows graph (DFG).

        1) Remove join gateways.
        2) Detect & remove split gateways; store them in *split_map*.
        3) Identify start nodes (nodes with in-degree = 0).
        4) For each start node, run a BFS:
           - If the current node is in *split_map*, print
             ``From [X] to [Y] AND [Z]...``
           - Otherwise, for each successor, print ``From [X] to [Y]``
           - Mark visited nodes so the walk does not loop infinitely on cycles.
    """
    #Mapping from node IDs to labels
    node_labels = {}
    start_node = None
    end_node = None

    for node in dg.nodes():
        data = dg.nodes[node]
        if data.get('type') == 'task':
            node_labels[node] = data['label']
        elif data.get('type') == 'start':
            start_node = data.get('label', node)
            node_labels[node] = start_node
        elif data.get('type') == 'end':
            end_node = data.get('label', node)
            node_labels[node] = end_node

    #Gateway connections and regular edges
    gateway_groups = {}
    regular_edges = []

    for u, v, data in dg.edges(data=True):
        if 'gateway_id' in data:
            gid = data['gateway_id']
            if gid not in gateway_groups:
                gateway_groups[gid] = []
            gateway_groups[gid].append((u, v))
        else:
            regular_edges.append((u, v))

    #Direct connections for gateways
    direct_edges = []
    for gid, edges in gateway_groups.items():
        gateway = None
        sources = set()
        targets = set()

        for u, v in edges:
            sources.add(u)
            targets.add(v)


        candidates = sources & targets
        if candidates:
            gateway = candidates.pop()

            #Split into incoming and outgoing
            incoming = [u for u, v in edges if v == gateway]
            outgoing = [v for u, v in edges if u == gateway]

            #Create direct connection
            for src in incoming:
                for tgt in outgoing:
                    direct_edges.append((src, tgt))

    #Combine edges and map to labels
    all_edges = direct_edges + regular_edges
    dfg_edges = []

    for u, v in all_edges:
        u_label = node_labels.get(u, u)
        v_label = node_labels.get(v, v)
        if 'AND-' not in u_label and 'OR-' not in u_label and 'AND-' not in v_label and 'OR-' not in v_label:
            dfg_edges.append((u_label, v_label))

    # Create ordered edge list
    ordered_edges = []
    visited = set()
    q = [start_node] if start_node else []

    while q:
        current = q.pop(0)
        if current in visited:
            continue
        visited.add(current)

        #All outgoing edges from node
        outgoing = [(u, v) for u, v in dfg_edges if u == current and v not in visited]

        # Add edges
        for edge in dfg_edges:
            if edge[0] == current and edge not in ordered_edges:
                ordered_edges.append(edge)
                if edge[1] not in visited:
                    q.append(edge[1])

    #Add remaining edges not connected to start node
    for edge in dfg_edges:
        if edge not in ordered_edges:
            ordered_edges.append(edge)

    #Output
    nodes = sorted({label for label in node_labels.values()
                    if 'AND-' not in label and 'OR-' not in label})

    edge_strings = [f"({u}, {v})" for u, v in ordered_edges]

    print("Nodes:", ", ".join(nodes))
    print("Edges:", ", ".join(edge_strings))

if __name__ == '__main__':
    bpmn_file = 'models/main/level 3/process_020/process_020.bpmn'
    directed_graph = bpmn_to_directed_graph(bpmn_file)

    print_dfg(directed_graph)
