import sys
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import tostring

max_depth = 3

def get_nodes():
    with open('facebook_nodes', 'r') as f:
        lines = f.readlines()

        nodes = {}
        parent = None
        last = None
        indent = 1

        for line in lines:
            split = line.split("    ")
            line_indent = len(split)
            line = line.strip()

            # Check if root node
            if line_indent == indent:
                nodes[line] = {'node_name': line}
                parent = line
            else:
                if line[0] == "{":
                    nodes[parent][last] = line
                else:
                    nodes[parent][line] = None

            last = line

        return nodes

def expand_nodes(nodes):
    for key, value in nodes.items():
        for node in value.keys():
            if value[node] != None and node != "node_name":
                node_name = value[node][1:-1]
                nodes[key][node] = nodes[node_name]
    return nodes

def _counter(d):
    # how many keys do we have?
    yield len(d)

    # stream the key counts of our children
    for v in d.values():
        if isinstance(v, dict):
            for x in _counter(v):
                yield x

def count_faster(d):
    return sum(_counter(d))


def build_functions(nodes, parent=None, depth=0):
    functions = []
    if not nodes or depth > max_depth:
        return functions
    for node, values in nodes.items():
        if node == 'node_name':
            continue

        function_node = node if not parent else parent['node']

        function_name = node if not parent else "{}_{}".format(parent['name'], node)

        # function_args = "{}_fields=None, {}_args=None".format(node, node)
        # if parent:
        #     function_args = "{}, {}".format(parent['args'], function_args)

        function_args = "fields=None, **kwargs"
        function_definition = f"def {function_name}(self, {function_node}_id, {function_args}):"

        if depth == 0:
            function_type = "iter()"
        elif depth == 1:
            function_type = f"self.FacebookIter(self.api_key, {function_node}_id, '{node}', fields=fields, **kwargs)"
        else:
            function_type = \
                f"self.iter_iter(self.{parent['name']}({function_node}_id), 'id', self.{nodes['node_name']}_{node}, kwargs)"

        function_full = f"\t{function_definition}\n\t\treturn {function_type}\n\n"

        functions.append(function_full)

        this = {
            'node': function_node,
            'name': function_name,
            'args': function_args
        }

        functions.extend(build_functions(values, this, depth + 1))

    return functions

def build_nodes(nodes, root, depth=0):
    if not nodes or depth > 2:
        return
    for key, value in nodes.items():
        if key == 'node_name':
            continue
        node = ET.SubElement(root, 'node')

        node_name = ET.SubElement(node, 'name')
        node_name.text = key.title()

        node_function = ET.SubElement(node, 'function')
        node_function.text = "blabla"

        node_inputs = ET.SubElement(node, 'inputs')

        node_input_id = ET.SubElement(node_inputs, 'input')
        node_input_id.attrib['required'] = "true"
        node_input_id_name = ET.SubElement(node_input_id, 'name')
        node_input_id_name.text = f"{key.title()} id"
        node_input_id_type = ET.SubElement(node_input_id, 'type')
        node_input_id_type.text = "text"

        node_input_fields = ET.SubElement(node_inputs, 'input')
        node_input_fields_name = ET.SubElement(node_input_fields, 'name')
        node_input_fields_name.text = "Fields"
        node_input_fields_type = ET.SubElement(node_input_fields, 'type')
        node_input_fields_type.text = "list"

        node_input_args = ET.SubElement(node_inputs, 'input')
        node_input_args_name = ET.SubElement(node_input_args, 'name')
        node_input_args_name.text = "Arguments"
        node_input_args_type = ET.SubElement(node_input_args, 'type')
        node_input_args_type.text = "arguments"
        node_input_args_columns = ET.SubElement(node_input_args, 'columns')
        node_input_args_column_arg = ET.SubElement(node_input_args_columns, 'column')
        node_input_args_column_arg.text = "Argument"
        node_input_args_column_val = ET.SubElement(node_input_args_columns, 'column')
        node_input_args_column_val.text = "Value"

        node_children = ET.SubElement(node, 'children')

        build_nodes(value, node_children, depth + 1)
        # node_children = ET.SubElement(node, 'children')
    return root


sys.setrecursionlimit(1500)
nodes = get_nodes()
expand_nodes(nodes)
root = ET.Element("children")
children = build_nodes(nodes, root)
with open('out.xml', 'wb') as f:
    f.write(tostring(root))

functions = build_functions(nodes)


with open('output.py', 'w') as f:
    class_definition = "class FacebookFunctions:\n"
    f.write(class_definition)
    f.writelines(functions)
