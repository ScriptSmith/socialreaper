import json
import sys
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import tostring

import os

max_depth = 3


def get_nodes(path):
    with open(os.path.join(path, 'facebook_nodes'), 'r') as f:
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


def get_fields(path):
    with open(os.path.join(path, 'facebook_fields.json'), 'r') as f:
        return json.load(f)


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

        function_args = "fields=None, **kwargs"
        function_definition = f"def {function_name}(self, {function_node}_id, {function_args}):"

        method = None
        if depth == 0:
            # function_type = f"self.SingleIter(self.api.node_edge, {function_node}_id, fields=fields, **kwargs)"
            def method(self, node_id, fields=None, **kwargs):
                return self.SingleIter(self.api.node_edge, node_id, fields=fields, **kwargs)
        elif depth == 1:
            # function_type = f"self.FacebookIter(self.api.node_edge, {function_node}_id, '{node}', fields=fields, **kwargs)"
            def method(self, node_id, fields=None, _node=node, **kwargs):
                return self.FacebookIter(self.api.node_edge, node_id, _node, fields=fields, **kwargs)

        else:
            # function_type = f"self.iter_iter(self.{parent['name']}({function_node}_id), 'id', self.{nodes['node_name']}_{node}, fields=fields, **kwargs)"
            def method(self, node_id, fields=None, _parent_name=parent['name'], _node_name=f"{nodes['node_name']}_{node}", **kwargs):
                return self.iter_iter(getattr(self, _parent_name)(node_id), 'id', getattr(self, _node_name), fields=fields, **kwargs)

        functions.append((function_name, method))

        this = {
            'node': function_node,
            'name': function_name,
            'args': function_args
        }

        functions.extend(build_functions(values, this, depth + 1))

    return functions


def build_nodes(nodes, root, parent_id=None, depth=0):
    root_children = ET.SubElement(root, 'children')
    parent_node_function = root.find('function')
    if not nodes or depth > max_depth:
        return
    for key, value in nodes.items():
        if key == 'node_name':
            continue

        node = ET.SubElement(root_children, 'node')

        node_name = ET.SubElement(node, 'name')
        node_name.text = key.title()

        node_function = ET.SubElement(node, 'function')

        node_function.text = f"{parent_node_function.text}_{key}" if parent_node_function != None else key

        node_inputs = ET.SubElement(node, 'inputs')

        node_input_id = ET.SubElement(node_inputs, 'input')
        node_input_id.attrib['required'] = "true"
        node_input_id_name = ET.SubElement(node_input_id, 'name')
        id_text = parent_id if parent_id else key.title()
        node_input_id_name.text = f"{id_text} id"
        node_input_id_type = ET.SubElement(node_input_id, 'type')
        node_input_id_type.text = "primary"

        node_input_fields = ET.SubElement(node_inputs, 'input')
        node_input_fields_name = ET.SubElement(node_input_fields, 'name')
        node_input_fields_name.text = "Fields"
        node_input_fields_type = ET.SubElement(node_input_fields, 'type')
        node_input_fields_type.text = "list"
        node_input_fields_elems = ET.SubElement(node_input_fields, 'elems')

        if value:
            node_fields = fields.get(value['node_name'])
            if node_fields:
                for field in node_fields:
                    elem = ET.SubElement(node_input_fields_elems, 'elem')
                    elem.text = field

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

        node_input_args_setters = ET.SubElement(node_input_args, 'setters')

        if depth > 0:
            node_input_args_setter_counter = ET.SubElement(
                node_input_args_setters, 'setter')
            node_input_args_setter_counter_name = ET.SubElement(
                node_input_args_setter_counter, 'name')
            node_input_args_setter_counter_name.text = f"{key.title()} count"
            node_input_args_setter_counter_argument = ET.SubElement(
                node_input_args_setter_counter, 'argument')
            node_input_args_setter_counter_argument.text = "count"
            node_input_args_setter_counter_value = ET.SubElement(
                node_input_args_setter_counter, 'value')
            node_input_args_setter_counter_value.text = "500"
            node_input_args_setter_counter_type = ET.SubElement(
                node_input_args_setter_counter, 'type')
            node_input_args_setter_counter_type.text = "counter"

        if depth > 1:
            node_input_args_setter_parent = ET.SubElement(node_input_args_setters, 'setter')
            node_input_args_setter_parent_name = ET.SubElement(node_input_args_setter_parent, 'name')
            node_input_args_setter_parent_name.text = "Include parent id"
            node_input_args_setter_parent_argument = ET.SubElement(node_input_args_setter_parent, 'argument')
            node_input_args_setter_parent_argument.text = "include_parents"
            node_input_args_setter_parent_value = ET.SubElement(node_input_args_setter_parent, 'value')
            node_input_args_setter_parent_value.text = "True"
            node_input_args_setter_parent_type = ET.SubElement(node_input_args_setter_parent, 'type')
            node_input_args_setter_parent_type.text = "checkbox"

        build_nodes(value, node, id_text, depth + 1)
    return root


sys.setrecursionlimit(1500)

path = os.path.dirname(__file__)
nodes = get_nodes(path)
expand_nodes(nodes)

fields = get_fields(path)

### To generate XML for github.com/scriptsmith/reaper
# root = ET.Element("source")
# root_name = ET.SubElement(root, 'name')
# root_name.text = "Facebook"
# keys = ET.SubElement(root, 'keys')
# key = ET.SubElement(keys, 'key')
# key_name = ET.SubElement(key, 'name')
# key_name.text = "Access token"
# key_value = ET.SubElement(key, 'value')
# key_value.text = "access_token"
# children = build_nodes(nodes, root)
#
# with open('out.xml', 'wb') as f:
#     f.write(tostring(root))

class Shell():
    def __init__(self):
        pass

for name, method in build_functions(nodes):
    setattr(Shell, name, method)
