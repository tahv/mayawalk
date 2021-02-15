# mayawalk

[![Latest Release](https://img.shields.io/github/v/release/tahv/mayawalk)](https://github.com/tahv/mayawalk/releases/)
[![Github](https://img.shields.io/github/license/tahv/mayawalk?color=blue)](https://choosealicense.com/licenses/mit/)
[![Tests](https://img.shields.io/github/workflow/status/tahv/mayawalk/Tests%20Runner?label=tests)](https://github.com/tahv/mayawalk/)
[![Docs](https://img.shields.io/github/workflow/status/tahv/mayawalk/Github%20Pages?label=docs)](https://tahv.github.io/mayawalk/)

Collection of traversal algorithms for Autodesk Maya.

Visit the [github repo](https://github.com/tahv/mayawalk/) for source code
and the [command reference](https://tahv.github.io/mayawalk/) for documentation.

## Installation

This package is composed of a single file, you can either:

- Copy the content of [mayawalk.py](https://raw.githubusercontent.com/tahv/mayawalk/main/mayawalk.py) directly.

- Download the [latest release](https://github.com/tahv/mayawalk/releases/latest/download/mayawalk.py).

- Install using pip:

```bash
pip install git+git://github.com/Tahv/mayawalk#egg=mayawalk
```

## Requirements

Run Maya >= 2020. It may run on older version but was not tested on them.

## Functions

- ``parent(node, include_world=False)``
- ``children(node, api_type=None)``
- ``siblings(node, api_type=None)``
- ``hierarchy(root, stoppers=None, api_type=None, depth_first=False``
- ``top_nodes(nodes, sparse=False)``
- ``connections(root, stoppers=None, api_type=None, depth_first=False, upstream=False)``
- ``connected(node, sources=True, destinations=True)``
- ``plugs(node, connection=None)``
- ``plug_parent(plug)``
- ``plug_children(plug, reverse=False, physical_indexes=False)``
- ``plug_has_source(plug, nested=False)``
- ``plug_has_destinations(plug, nested=False)``
- ``plug_has_connections(plug, nested=False)``

## Usage examples

### hierarchy

```python
from maya.api import OpenMaya
from mayawalk import hierarchy

modifier = OpenMaya.MDagModifier()

root = modifier.createNode('transform')              # root
node_a = modifier.createNode('transform', root)      # |- node_a
shape_a = modifier.createNode('nurbsCurve', node_a)  #    |- shape_a
node_b = modifier.createNode('joint', root)          # |- node_b

modifier.doIt()

assert list(hierarchy(root)) == [root, node_a, node_b, shape_a]
assert list(hierarchy(shape_a, upstream=True)) == [shape_a, node_a, root]
```

### connections

```python
from maya.api import OpenMaya
from mayawalk import connections

modifier = OpenMaya.MDagModifier()

node_a = modifier.createNode('transform')
node_b = modifier.createNode('transform')
node_c = modifier.createNode('transform')

modifier.doIt()

plug_a = OpenMaya.MFnDagNode(node_a).findPlug('tx', False)
plug_b = OpenMaya.MFnDagNode(node_b).findPlug('tx', False)
plug_c = OpenMaya.MFnDagNode(node_c).findPlug('tx', False)

modifier.connect(plug_a, plug_b).doIt()
modifier.connect(plug_b, plug_c).doIt()
# node_a.tx >> node_b.tx >> node_c.tx

assert list(connections(node_a)) == [node_a, node_b, node_c]
assert list(connections(node_c, upstream=True)) == [node_c, node_b, node_a]
assert list(connections(node_a, stoppers=[node_b])) == [node_a, node_b]
```

### top_nodes

```python
from maya.api import OpenMaya
from mayawalk import top_nodes

modifier = OpenMaya.MDagModifier()

node_a = modifier.createNode('transform')          # node_a
node_b = modifier.createNode('transform', node_a)  # |- node_b
node_c = modifier.createNode('transform', node_b)  #    |- node_c

modifier = modifier.doIt()

assert list(top_nodes([node_b, node_c])) == [node_b]
assert list(top_nodes([node_a, node_c], sparse=True)) == [node_a]
```

## Contributing

Pull requests are welcome. Please make sure to update tests as appropriate.
