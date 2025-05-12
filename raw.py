import xml.etree.ElementTree as ET
import os


def get_structural_bpmn(bpmn_file_path):
    """
        Return a cleaned-up “structural” view of the BPMN <process> tag
    """

    tree = ET.parse(bpmn_file_path)
    root = tree.getroot()

    #Find Process tag
    process = None
    for elem in root.iter():
        if '}' in elem.tag: _, tag = elem.tag.split('}', 1)
        else: tag = elem.tag
        if tag == 'process':
            process = elem
            break
    if process is None:
        print("No process element")
        return

    #Separate children based on flow
    non_sequence_flows = []
    sequence_flows = []
    for child in process:
        if '}' in child.tag: _, tag = child.tag.split('}', 1)
        else: tag = child.tag
        if tag == 'sequenceFlow':
            sequence_flows.append(child)
        else:
            non_sequence_flows.append(child)

    #Attribute keys
    def process_attr_key(key):
        if key.startswith('{http://www.w3.org/2001/XMLSchema-instance}'):
            return 'xsi:' + key.split('}', 1)[1]
        elif '}' in key:
            return key.split('}', 1)[1]
        else:
            return key

    # Cconvert to XML string
    def element_to_str(elem):
        # Process tag
        if '}' in elem.tag:
            _, tag = elem.tag.split('}', 1)
        else:
            tag = elem.tag

        #Skip extensionElements
        if tag == 'extensionElements':
            return ''

        attrs = ' '.join([f'{process_attr_key(k)}="{v}"' for k, v in elem.attrib.items()])
        attrs = attrs.strip()

        #Children
        children = []
        for child in elem:
            if '}' in child.tag:
                _, child_tag = child.tag.split('}', 1)
            else:
                child_tag = child.tag
            if child_tag != 'extensionElements':
                children.append(child)

        #XML string
        if not children:
            if attrs:
                return f'<{tag} {attrs} />'
            else:
                return f'<{tag} />'
        else:
            child_strs = [element_to_str(child) for child in children]
            child_strs = [s for s in child_strs if s]  # Clean-up
            inner = '\n'.join(child_strs)
            if attrs:
                return f'<{tag} {attrs}>\n{inner}\n</{tag}>'
            else:
                return f'<{tag}>\n{inner}\n</{tag}>'

    process_attrs = ' '.join([f'{process_attr_key(k)}="{v}"' for k, v in process.attrib.items()])

    #Compose output
    output = []
    output.append(f'<process {process_attrs}>')

    #non-sequenceFlow elements first
    for elem in non_sequence_flows:
        elem_str = element_to_str(elem)
        if elem_str:  # Skip empty strings
            for line in elem_str.split('\n'):
                output.append(f'    {line}')

    output.append('    <!-- Sequence Flows -->') #Adding clarity

    #sequenceFlow elements
    for elem in sequence_flows:
        elem_str = element_to_str(elem)
        if elem_str:
            for line in elem_str.split('\n'):
                output.append(f'    {line}')

    output.append('</process>')
    return('\n'.join(output))

if __name__ == '__main__':
    process_id = 'process_020'
    path = f'models/main/level 3/{process_id}/{process_id}.bpmn'
    save_path = f'models/main/level 3/{process_id}/prompts'

    if not os.path.isdir(save_path):
        raise FileNotFoundError("Folder does not exist.")


    result = get_structural_bpmn(path)
    file_path = os.path.join(save_path, "raw.txt")

    # Write the result to raw.txt
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(result)