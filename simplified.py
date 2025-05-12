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

def bpmn_simplified(dg):
    """
        Compose a simplified form of the BPMN model.
    """
    output_lines = []
    output_lines.append("I have the BPMN model of a business process.\n")
    output_lines.append("The tasks in a BPMN model represent specific activities within the business process. Each task signifies a step that must be performed to complete the process. The tasks included in this BPMN model are:\n")
    
    #Tasks
    for node, data in dg.nodes(data=True):
        if data.get('type') == 'task':
            output_lines.append(f"{data['label']} (task)")

    output_lines.append("\nEvents in a BPMN model represent occurrences that affect the flow of the process. They can signify the start, intermediate, or end of a process. In this BPMN model, the events are:\n")
    
    #Events
    for node, data in dg.nodes(data=True):
        if data.get('type') == 'event':
            output_lines.append(f"{node} ({data['label']})")

    output_lines.append("\nGateways in a BPMN model control the process flow by either diverging into multiple paths or converging different paths back together. There are two types of gateways: \n")
    output_lines.append("- **Parallel Gateway (AND):** This type can only be fired when all its incoming flows are 'active', and its firing activates all its outgoing flows.\n")
    output_lines.append("- **Exclusive Gateway (OR):** This type allows only one of its outgoing flows to be taken based on predefined conditions. The choice of which flow to take is determined at runtime.\n")
    
    #Gateways
    for node, data in dg.nodes(data=True):
        if data.get('type') == 'gateway':
            output_lines.append(f"{node} ({data['label']})")

    output_lines.append("\nFlows in a BPMN model define the sequence of execution for tasks, events, and gateways. The flows in this model are:\n")
    
    #Flows
    for source, target in dg.edges():
        output_lines.append(f"{source} -> {target}")

    return "\n".join(output_lines)


if __name__ == '__main__':
    bpmn_file = 'models/main/level 3/process_019/process_019.bpmn'
    directed_graph = bpmn_to_directed_graph(bpmn_file)

    #Print the simplified BPMN output
    simplified_output = bpmn_simplified(directed_graph)
    print('--------------- Simplified BPMN: -----------------\n\n')
    print(simplified_output)
    print('\n\n--------------- Simplified BPMN end -------------\n\n')