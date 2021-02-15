from __future__ import division, absolute_import, print_function

from maya.api import OpenMaya

import mayawalk

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Helpers


def create_node(node_type, parent=None, name=None):
    args = [node_type, parent] if parent is not None else [node_type]
    try:  # Try to create a dependency node.
        modifier = OpenMaya.MDGModifier()
        node_mob = modifier.createNode(*args)
    except TypeError:  # invalid node type (or invalid modifier)
        try:  # Try to create a dag node.
            modifier = OpenMaya.MDagModifier()
            node_mob = modifier.createNode(*args)
        except TypeError:  # invalid node type
            raise TypeError('Invalid node type: {}.'.format(node_type))
    if name is not None:
        modifier.renameNode(node_mob, name)
    modifier.doIt()

    # Renames created shapes.
    if node_mob.hasFn(OpenMaya.MFn.kTransform):
        dag = OpenMaya.MFnDagNode(node_mob)
        for index in range(dag.childCount()):
            child = dag.child(index)
            if child.hasFn(OpenMaya.MFn.kShape):
                modifier.renameNode(child, name + 'Shape')
        modifier.doIt()

    return node_mob


def find_plug(node, name):
    return OpenMaya.MFnDependencyNode(node).findPlug(name, False)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Tests


def test_parent():
    parent = create_node('transform')
    child = create_node('transform', parent=parent)
    assert mayawalk.parent(child) == parent


def test_parent_world():
    world = OpenMaya.MItDependencyNodes(OpenMaya.MFn.kWorld).thisNode()
    node = create_node('transform')
    assert mayawalk.parent(node, include_world=False) is None
    assert mayawalk.parent(node, include_world=True) == world


def test_children_any():
    parent = create_node('transform')
    child_shape = create_node('nurbsCurve', parent=parent)
    child_transform = create_node('transform', parent=parent)
    assert list(mayawalk.children(parent)) == [child_shape, child_transform]


def test_children_filtered():
    parent = create_node('transform')                    # parent
    shape = create_node('nurbsCurve', parent=parent)     # |- shape
    transform = create_node('transform', parent=parent)  # |- transform

    found = list(mayawalk.children(parent, api_type=OpenMaya.MFn.kNurbsCurve))
    assert found == [shape]


def test_siblings_any():
    parent = create_node('transform')                    # parent
    node = create_node('transform', parent=parent)       #  |- node
    transform = create_node('transform', parent=parent)  #  |- transform
    joint = create_node('joint', parent=parent)          #  |- joint
    assert list(mayawalk.siblings(node)) == [transform, joint]


def test_siblings_filtered():
    parent = create_node('transform')                    # parent
    node = create_node('transform', parent=parent)       #  |- node
    transform = create_node('transform', parent=parent)  #  |- transform
    joint = create_node('joint', parent=parent)          #  |- joint
    assert list(mayawalk.siblings(node, api_type=OpenMaya.MFn.kJoint)) == [joint]


def test_siblings_world():
                                        # world
    node = create_node('transform')     #  |- node
    sibling = create_node('transform')  #  |- sibling

    # Default Maya camera nodes are also siblings of node.
    assert sibling in mayawalk.siblings(node)


def test_hierarchy_downstream():
    root = create_node('transform')                            # root
    curve_transform = create_node('transform', parent=root)    #  |- curve_transform
    shape = create_node('nurbsCurve', parent=curve_transform)  #      |- shape
    transform = create_node('transform', parent=root)          #  |- transform

    # Breadth first search
    breadth_first = list(mayawalk.hierarchy(root, depth_first=False))
    assert breadth_first == [root, curve_transform, transform, shape]

    # Depth first search
    depth_first = list(mayawalk.hierarchy(root, depth_first=True))
    assert depth_first == [root, transform, curve_transform, shape]


def test_hierarchy_upstream():
    parent = create_node('transform')                    # parent
    child = create_node('transform', parent=parent)      #  |- child
    grandchild = create_node('transform', parent=child)  #      |- grandchild

    found = list(mayawalk.hierarchy(grandchild, upstream=True))
    assert found == [grandchild, child, parent]


def test_hierarchy_stoppers():
    parent = create_node('transform')                   # parent
    child = create_node('transform', parent=parent)     #  |- child
    granchild = create_node('transform', parent=child)  #      |- grandchild
    assert list(mayawalk.hierarchy(parent, stoppers=[child])) == [parent, child]


def test_hierarchy_filtered():
    parent = create_node('transform')                         # parent
    child_joint = create_node('joint', parent=parent)         #  |- child_joint
    granchild = create_node('transform', parent=child_joint)  #      |- grandchild

    found = list(mayawalk.hierarchy(parent, api_type=OpenMaya.MFn.kJoint))
    assert found == [child_joint]


def test_top_nodes():
    node_a = create_node('transform')                 # node_a
    node_b = create_node('transform', parent=node_a)  #  |- node_b
    node_c = create_node('transform')                 # node_c
    node_d = create_node('transform', parent=node_c)  #  |- node_d
    node_e = create_node('transform', parent=node_d)  #      |- node_e

    found = list(mayawalk.top_nodes((node_a, node_b, node_d, node_e)))
    assert found == [node_a, node_d]


def test_top_nodes_sparse():
    node_a = create_node('transform')                 # node_a
    node_b = create_node('transform', parent=node_a)  #  |- node_b
    node_c = create_node('transform', parent=node_b)  #      |- node_c

    found = list(mayawalk.top_nodes((node_a, node_c), sparse=True))
    assert found == [node_a]


def test_plug_parent():
    node = OpenMaya.MFnDependencyNode(create_node('transform'))
    translate = node.findPlug('translate', False)
    translate_x = node.findPlug('translateX', False)
    assert mayawalk.plug_parent(translate) is None
    assert mayawalk.plug_parent(translate_x) == translate


def test_plug_children():
    node = OpenMaya.MFnDependencyNode(create_node('transform'))
    translate = node.findPlug('translate', False)
    children = [node.findPlug('translate' + axis, False) for axis in 'XYZ']
    assert list(mayawalk.plug_children(translate)) == children


def test_plug_children_reverse():
    node = OpenMaya.MFnDependencyNode(create_node('transform'))
    translate = node.findPlug('translate', False)
    children = [node.findPlug('translate' + axis, False) for axis in 'ZYX']
    assert list(mayawalk.plug_children(translate, reverse=True)) == children


def test_plugs():
    node_src = create_node('transform')
    node_dst = create_node('transform')
    plug_src = find_plug(node_src, 'translateX')
    plug_dst = find_plug(node_dst, 'translateY')
    OpenMaya.MDGModifier().connect(plug_src, plug_dst).doIt()

    status = mayawalk.ConnectionStatus

    # Has plug
    assert plug_src in mayawalk.plugs(node_src)

    # Has connections
    assert list(mayawalk.plugs(node_src, status.kConnected)) == [plug_src]
    assert plug_src not in mayawalk.plugs(node_src, status.kDisconnected)

    # Has destination connections
    assert list(mayawalk.plugs(node_src, status.kConnectedDestinations)) == [plug_src]
    assert plug_src not in mayawalk.plugs(node_src, status.kDisconnectedDestinations)

    # Has no source connections
    assert plug_src not in mayawalk.plugs(node_src, status.kConnectedSources)
    assert plug_src in mayawalk.plugs(node_src, status.kDisconnectedSources)


def test_connected():
    src = create_node('transform')
    dst = create_node('transform')

    # source >> destination
    modifier = OpenMaya.MDGModifier()
    modifier.connect(find_plug(src, 'translateX'), find_plug(dst, 'translateY'))
    modifier.doIt()

    # Connected sources
    assert list(mayawalk.connected(src, sources=False, destinations=True)) == [dst]
    assert list(mayawalk.connected(dst, sources=True, destinations=False)) == [src]


def test_connections_visite_once():
    node_src = create_node('transform')
    node_dst = create_node('transform')

    plug_src = find_plug(node_src, 'translateX')
    plug_dst = find_plug(node_dst, 'translateY')
    plug_loop = find_plug(node_src, 'translateZ')

    # source >> destination >> source
    modifier = OpenMaya.MDGModifier()
    modifier.connect(plug_src, plug_dst)
    modifier.connect(plug_dst, plug_loop)
    modifier.doIt()

    assert list(mayawalk.connections(node_src)) == [node_src, node_dst]

# TODO write more tests for mayawalk.connections


def test_plug_children_ignore_placeholder_plug():
    node = create_node('transform')
    plug = find_plug(node, 'instObjGroups')

    # instObjGroups has a '[-1]' index, which is at the same time an array and a
    # compound. Maya crash When we try to query the compound child.
    # The goal of this test is to make sure mayawalk.plug_children return the array
    # children and not the compounds.
    assert list(mayawalk.plug_children(plug)) == []


def test_plug_children_array():
    node_src = create_node('transform')
    modifier = OpenMaya.MDGModifier()

    # Add an array of int.
    mattribute = OpenMaya.MFnNumericAttribute()
    attr_obj = mattribute.create('array', 'array', OpenMaya.MFnNumericData.kShort)
    mattribute.array = True
    modifier.addAttribute(node_src, attr_obj).doIt()
    array = find_plug(node_src, 'array')

    # Connect array plugs so they "exists".
    # array[0] >> array[3]
    index_1 = array.elementByLogicalIndex(1)
    index_3 = array.elementByLogicalIndex(3)
    modifier.connect(index_1, index_3).doIt()

    assert list(mayawalk.plug_children(array)) == [index_1, index_3]


def test_plug_has_source():
    node_src = create_node('transform')
    node_dst = create_node('transform')
    plug_src = find_plug(node_src, 'translateX')
    plug_dst = find_plug(node_dst, 'translateY')
    OpenMaya.MDGModifier().connect(plug_src, plug_dst).doIt()
    assert mayawalk.plug_has_source(plug_dst)


def test_plug_has_source_nested():
    node_src = create_node('transform')
    node_dst = create_node('transform')
    plug_src = find_plug(node_src, 'translateX')
    plug_dst = find_plug(node_dst, 'translateY')
    OpenMaya.MDGModifier().connect(plug_src, plug_dst).doIt()
    assert mayawalk.plug_has_source(find_plug(node_dst, 'translate'), nested=True)


def test_plug_has_destinations():
    node_src = create_node('transform')
    node_dst = create_node('transform')
    plug_src = find_plug(node_src, 'translateX')
    plug_dst = find_plug(node_dst, 'translateY')
    OpenMaya.MDGModifier().connect(plug_src, plug_dst).doIt()
    assert mayawalk.plug_has_destinations(plug_src)


def test_plug_has_destinations_nested():
    node_src = create_node('transform')
    node_dst = create_node('transform')
    plug_src = find_plug(node_src, 'translateX')
    plug_dst = find_plug(node_dst, 'translateY')
    OpenMaya.MDGModifier().connect(plug_src, plug_dst).doIt()
    assert mayawalk.plug_has_destinations(find_plug(node_src, 'translate'), nested=True)
