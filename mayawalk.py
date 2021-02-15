"""Collection of traversal algorithms for Autodesk Maya."""
from __future__ import division, absolute_import, print_function

import itertools
from collections import deque
import logging

from maya.api import OpenMaya

__version__ = '0.1.0'

_LOG = logging.getLogger(__name__)


class ConnectionStatus(object):
    """All connections status a plug can have. Enum class."""

    kConnected = 1
    """Has any connection."""

    kConnectedSources = 2
    """Has a source / is a destination."""

    kConnectedDestinations = 3
    """Has destination(s) / is a source."""

    kDisconnected = 4
    """Has no connection."""

    kDisconnectedSources = 5
    """Has no source / is not a destination."""

    kDisconnectedDestinations = 6
    """Has no destinations / is not a source."""

    @classmethod
    def has_status(cls, plug, connection):
        """
        Args:
            plug (MPlug): Plug to check.
            connection (int): `.ConnectionStatus` constant.

        Returns:
            bool: True if ``plug`` has ``connection`` status, False otherwise.
        """
        if any((
                connection == cls.kConnected and not plug.isConnected,
                connection == cls.kConnectedDestinations and not plug.isSource,
                connection == cls.kConnectedSources and not plug.isDestination,
                connection == cls.kDisconnected and plug.isConnected,
                connection == cls.kDisconnectedDestinations and plug.isSource,
                connection == cls.kDisconnectedSources and plug.isDestination,
            )):
            return False
        return True


def parent(node, include_world=False):
    """Return the parent of ``node``, if it has one, None otherwise.

    Args:
        node (MObject): Dag node we want the parent of.
        include_world (bool): If parent is the world node, return it if True,
            return None if False. Defaults to False.

    Returns:
        MObject, None:

    Example:
        >>> modifier = OpenMaya.MDagModifier()
        >>> root = modifier.createNode('transform')        # root
        >>> child = modifier.createNode('transform', root) # |- child
        >>> modifier = modifier.doIt()
        >>> parent(child) == root
        True
        >>> parent(root) == None
        True
    """
    dag = OpenMaya.MFnDagNode(node)
    try:
        parent_mob = dag.parent(0)
    except RuntimeError:  # Node has no parent (is probably the world node).
        return None

    if not include_world:
        world = OpenMaya.MItDependencyNodes(OpenMaya.MFn.kWorld).thisNode()
        if parent_mob == world:
            return None
    return parent_mob


def children(node, api_type=None):
    """Make an iterator returning children of ``node``.

    Args:
        node (MObject): Dag node we want the children of.
        api_type (int, None): Only yields nodes of specified *Mfn* constant
            type. Defaults to None (same as filtering by *MFn.kDagNode*).

    Yields:
        MObject: children of ``node``.

    Example:
        >>> modifier = OpenMaya.MDagModifier()
        >>> root = modifier.createNode('transform')         # root
        >>> shape = modifier.createNode('nurbsCurve', root) # |- shape
        >>> group = modifier.createNode('transform', root)  # |- group
        >>> modifier = modifier.doIt()
        >>> list(children(root)) == [shape, group]
        True
        >>> list(children(root, api_type=OpenMaya.MFn.kNurbsCurve)) == [shape]
        True
    """
    if node.hasFn(OpenMaya.MFn.kShape):
        # A shape has no children.
        return

    dag = OpenMaya.MFnDagNode(node)
    for index in range(dag.childCount()):
        child = dag.child(index)
        if not api_type or child.hasFn(api_type):
            yield child


def siblings(node, api_type=None):
    """Make an iterator returning siblings of ``node``.

    Args:
        node (MObject): Dag node we want the siblings of.
        api_type (int, None): Only yields nodes of specified *Mfn* constant
            type. Defaults to None (same as filtering by *MFn.kDagNode*).

    Yields:
        MObject: Nodes at the same hierarchical level (same parent) than
        ``node``.

    Example:
        >>> modifier = OpenMaya.MDagModifier()
        >>> root = modifier.createNode('transform')        # root
        >>> node = modifier.createNode('transform', root)  # |- node
        >>> group = modifier.createNode('transform', root) # |- group
        >>> joint = modifier.createNode('joint', root)     # |- joint
        >>> modifier = modifier.doIt()
        >>> list(siblings(node, api_type=OpenMaya.MFn.kJoint)) == [joint]
        True
        >>> list(siblings(node)) == [group, joint]
        True
    """
    parent_mob = parent(node, include_world=True)

    if not parent_mob:
        # node is the world node, it has no parent and no siblings.
        return

    world = OpenMaya.MItDependencyNodes(OpenMaya.MFn.kWorld).thisNode()
    parent_is_world = parent_mob == world

    parent_dag = OpenMaya.MFnDagNode(parent_mob)
    for index in range(parent_dag.childCount()):
        child = parent_dag.child(index)
        if child == node:
            continue

        # If iterating siblings at root level, don't yield the 'default' nodes
        # automatically created by Maya and invisibles in outliner.
        if parent_is_world and OpenMaya.MFnDagNode(child).isDefaultNode:
            continue

        if not api_type or child.hasFn(api_type):
            yield child


def hierarchy(root, stoppers=None, api_type=None, depth_first=False,
              upstream=False):
    """Traverse ``root`` hierarchy.

    Info:
        ``root`` is included as the first element in the returned iterator.

    Args:
        root (MObject): Starting dag node.
        stoppers (list[MObject], None): Don't iterate past these nodes. They
            are still yielded and won't break the iteration. Defaults to None.
        api_type (int, None): Only yields nodes of specified *Mfn* constant
            type. Defaults to None (same as filtering by *MFn.kDagNode*).
        depth_first (bool): Traversal algorithm.
            Use *depth-first search* if True, *breadth-first search* if False.
            Defaults to False.
        downstream (bool): Traversal direction.
            Go *upstream* (parents) if True, *downstream* (children) if False.
            The ``depth_first`` param has no effect when going upstream.
            Defaults to False.

    Yields:
        MObject: Nodes in ``root`` (**included**) hierarchy.

    Example:
        >>> modifier = OpenMaya.MDagModifier()
        >>> root = modifier.createNode('transform')           # root
        >>> node_a = modifier.createNode('transform', root)   # |- node_a
        >>> shape = modifier.createNode('nurbsCurve', node_a) #    |- shape
        >>> node_b = modifier.createNode('joint', root)       # |- node_b
        >>> modifier = modifier.doIt()
        >>> list(hierarchy(root)) == [root, node_a, node_b, shape]
        True
        >>> list(hierarchy(shape, upstream=True)) == [shape, node_a, root]
        True
    """
    def parents(node):
        """Returns node parent as a list, or an empty list if has no parents."""
        parent_mob = parent(node, include_world=False)
        return [parent_mob] if parent_mob is not None else []

    stoppers = stoppers or []
    stack = deque([root])
    while stack:
        current = stack.pop() if depth_first else stack.popleft()

        if not api_type or current.hasFn(api_type):
            yield current

        if current in stoppers:
            continue

        stack.extend(parents(current) if upstream else children(current))


def top_nodes(nodes, sparse=False):
    """Make an iterator returning the topmost nodes in ``nodes``.

    A top node is a node whose parent(s) is not in the input ``nodes`` list.

    Args:
        nodes (list[MObject]): A list of dag nodes objects.
        sparse (bool): If you want to find the top nodes in a sparse hierarchy.
            If **False**, only check the first parent of each node against
            ``nodes``.
            If **True**, check all parents in the upstream hierarchy of each
            nodes against ``nodes``.

    Yields:
        MObject: Members of ``nodes`` list whose parent is not in ``nodes``.

    Example:
        >>> modifier = OpenMaya.MDagModifier()
        >>> node_a = modifier.createNode('transform')          # node_a
        >>> node_b = modifier.createNode('transform', node_a)  # |- node_b
        >>> node_c = modifier.createNode('transform', node_b)  #    |- node_c
        >>> modifier = modifier.doIt()
        >>> list(top_nodes([node_b, node_c])) == [node_b]
        True
        >>> list(top_nodes([node_a, node_c], sparse=True)) == [node_a]
        True
    """
    if sparse:
        def parents(node):
            return itertools.islice(hierarchy(node, upstream=True), 1, None)
    else:
        def parents(node):
            parent_mob = parent(node, include_world=False)
            return [parent_mob] if parent_mob is not None else []

    nodes = list(nodes)
    for node in nodes:
        if not any(parent in nodes for parent in parents(node)):
            yield node


def connections(root, stoppers=None, api_type=None, depth_first=False, upstream=False):
    """Traverse ``root`` connections.

    Info:
        ``root`` is included as the first element in the returned iterator.

    Args:
        root (MObject): Starting dependency node.
        stoppers (list[MObject], None): Don't iterate past these nodes. They
            are still yielded and won't break the iteration. Defaults to None.
        api_type (int, None): Only yields nodes of specified Mfn constant type.
            Defaults to None (same as filtering by MFn.kDagNode).
        depth_first (bool): Traversal algorithm.
            Use *depth-first search* if True, *breadth-first search* if False.
            Defaults to False.
        downstream (bool): Traversal direction.
            Go *upstream* (sources, left) if True,
            *downstream* (destinations, right) if False.
            Defaults to False.

    Yields:
        MObject: Nodes connected directly and indirectly to ``root``
        (**included**).

    Example:
        >>> modifier = OpenMaya.MDagModifier()
        >>> node_a = modifier.createNode('transform')
        >>> node_b = modifier.createNode('transform')
        >>> node_c = modifier.createNode('transform')
        >>> modifier = modifier.doIt()
        >>> plug_a = OpenMaya.MFnDagNode(node_a).findPlug('tx', False)
        >>> plug_b = OpenMaya.MFnDagNode(node_b).findPlug('tx', False)
        >>> plug_c = OpenMaya.MFnDagNode(node_c).findPlug('tx', False)
        >>> modifier = modifier.connect(plug_a, plug_b).doIt()
        >>> modifier = modifier.connect(plug_b, plug_c).doIt()
        >>> # node_a.tx >> node_b.tx >> node_c.tx
        >>> list(connections(node_a)) == [node_a, node_b, node_c]
        True
        >>> list(connections(node_c, upstream=True)) == [node_c, node_b, node_a]
        True
        >>> list(connections(node_a, stoppers=[node_b])) == [node_a, node_b]
        True
    """
    stoppers = stoppers or []
    visited = set()

    def get_hash(mobject):
        """int: Returns ``mobject`` unique hash."""
        return OpenMaya.MObjectHandle(mobject).hashCode()

    def sources(node):
        """MObject: Yields sources nodes connected to ``node``."""
        return connected(node, sources=True, destinations=False)

    def destinations(node):
        """MObject: Yields destinations nodes connected to ``node``."""
        return connected(node, sources=False, destinations=True)

    def has_unvisited_connections(node):
        """bool: Returns True if ``node`` is connected to an unvisited node"""
        opposite_connections = destinations if upstream else sources
        if node != root:
            for src in opposite_connections(node):
                if src == node:
                    continue
                if get_hash(src) not in visited:
                    return True
        return False

    stack = deque([root])
    while stack:
        current = stack.pop() if depth_first else stack.popleft()
        current_hash = get_hash(current)

        if current_hash in visited:  # Cycle.
            continue

        # Can be visited too soon if breadth_first.
        if not depth_first and has_unvisited_connections(current):
            continue

        if not api_type or current.hasFn(api_type):
            yield current

        visited.add(current_hash)

        if current in stoppers:
            continue

        stack.extend(sources(current) if upstream else destinations(current))


def connected(node, sources=True, destinations=True):  # , api_type=None
    """Make an iterator returning nodes connected ``node``.

    Args:
        node (MObject): Node to find the connections of.
        sources (bool): Include ``node`` sources. Defaults to True.
        destinations (bool): Include ``node`` destinations. Defaults to True.

    Yields:
        MObject: Nodes directly connected to ``node``.

    Example:
        >>> modifier = OpenMaya.MDagModifier()
        >>> src = modifier.createNode('transform')
        >>> dst = modifier.createNode('transform')
        >>> modifier = modifier.doIt()
        >>> modifier = modifier.connect(
        ...     OpenMaya.MFnDagNode(src).findPlug('tx', False),
        ...     OpenMaya.MFnDagNode(dst).findPlug('tx', False)).doIt()
        >>> # src.tx >> dst.tx
        >>> list(connected(src, sources=False, destinations=True)) == [dst]
        True
        >>> list(connected(dst, sources=True, destinations=False)) == [src]
        True
    """
    # TODO add MFn filtering ?
    visited = set()
    if sources:
        for plug in plugs(node, connection=ConnectionStatus.kConnectedSources):
            node = plug.sourceWithConversion().node()
            node_hash = OpenMaya.MObjectHandle(node).hashCode()
            if node_hash not in visited:
                # if not api_type or node.hasFn(api_type):
                yield node
                visited.add(node_hash)

    if destinations:
        for plug in plugs(node, connection=ConnectionStatus.kConnectedDestinations):
            for dest in plug.destinationsWithConversions():
                node = dest.node()
                node_hash = OpenMaya.MObjectHandle(node).hashCode()
                if node_hash not in visited:
                    # if not api_type or node.hasFn(api_type):
                    yield node
                    visited.add(node_hash)


def plugs(node, connection=None):
    """Make an iterator returning plugs of ``node``.

    Args:
        node (MObject): Node we want the plugs of.
        connection (int, None): If specified, only yields nodes of this
            `.ConnectionStatus`. Defaults to None.

    Yields:
        MPlug: Plugs of ``node``.
    """
    # # Attributes Classes filter.  # TODO filter by attr_class ?
    # kAttrDynamic = OpenMaya.MFnDependencyNode.kLocalDynamicAttr  #: User attrs. 1
    # kAttrStatic = OpenMaya.MFnDependencyNode.kNormalAttr  #: Built-in attrs. 2
    # kAttrExtension = OpenMaya.MFnDependencyNode.kExtensionAttr  # 3
    # kAttrInvalid = OpenMaya.MFnDependencyNode.kInvalidAttr  # 4

    dep = OpenMaya.MFnDependencyNode(node)
    for index in range(dep.attributeCount()):
        # attr_mob = dep.attribute(index)
        # if attr_class and dep.attributeClass(attr_mob) != attr_class:
        #     continue

        plug = dep.findPlug(dep.attribute(index), False)

        # Maya sometime crash when we try to access [-1] indexes.
        if '[-1]' in plug.name():
            _LOG.debug('Ignoring placeholder index plug %s', plug.name())
            continue

        # Include children if is array (Compound children are already included).
        childplugs = plug_children(plug) if plug.isArray else []
        for plg in itertools.chain([plug], childplugs):
            if not connection or ConnectionStatus.has_status(plg, connection):
                yield plg


def plug_parent(plug):
    """Return ``plug`` parent, if it has one, None otherwise.

    Args:
        plug (MPlug): Plug we want the parent of.

    Returns:
        MPlug, None:

    Example:
        >>> modifier = OpenMaya.MDagModifier()
        >>> node = OpenMaya.MFnDagNode(modifier.createNode('transform'))
        >>> modifier = modifier.doIt()
        >>> translate = node.findPlug('translate', False)
        >>> translate_x = node.findPlug('translateX', False)
        >>> plug_parent(translate) == None
        True
        >>> plug_parent(translate_x) == translate
        True
    """
    if plug.isChild:
        return plug.parent()
    elif plug.isElement:
        return plug.array()
    return None


def plug_children(plug, reverse=False, physical_indexes=False):  # connection=None
    """Make an iterator returning children plugs of ``plug``.

    Iterator might be empty if ``plug`` is neither an array nor a compound, or
    is a non-physical plug (for example *animCurveUU.keyTanOutX*).

    Args:
        plug (MPlug): The plug we want chilren of.
        physical_indexes (bool): If ``mplug`` is an array, return the physical
            indexes if **True**, the logical indexes if **False**.
            Default to False.
        reverse (bool): Iter children
            in the correct order if **False** (``X, Y, Z or 0, 1, 2``)
            or in reverse order if **True** (``Z, Y, X or 2, 1, 0``).
            Default to False.

    Yields:
        MPlug: Children mplugs of ``plug``

    Raises:
        IndexError: Unknown error when trying to get a child plug.

    Example:
        >>> modifier = OpenMaya.MDagModifier()
        >>> node = OpenMaya.MFnDagNode(modifier.createNode('transform'))
        >>> modifier = modifier.doIt()
        >>> translate = node.findPlug('t', False)
        >>> children = [node.findPlug('t' + axis, False) for axis in 'xyz']
        >>> list(plug_children(translate)) == children
        True
        >>> children.reverse()
        >>> list(plug_children(translate, reverse=True)) == children
        True
    """
    # TODO add kwarg has_status (ConnectionStatus)

    # A plug can be array and compound at the same time. If this is the case, we
    # treat is as an array. Its children elements are the real compounds.
    if plug.isArray:

        # Some array plugs don't have physical indexes. For example:
        # {OpenMaya.MFn.kAnimCurve: (
        #     'keyTanLocked', 'keyWeightLocked', 'keyTanInX', 'keyTanInY',
        #     'keyTanOutX', 'keyTanOutY', 'keyTanInType', 'keyTanOutType',
        #     'keyBreakdown', 'keyTickDrawSpecial')}
        if not OpenMaya.MFnAttribute(plug.attribute()).connectable:
            _LOG.debug('Ignoring non-physical plug %s', plug.name())
            return

        if physical_indexes:
            get_child = plug.elementByPhysicalIndex
        else:
            get_child = plug.elementByLogicalIndex
        child_count = plug.evaluateNumElements()

    elif plug.isCompound:
        get_child = plug.child
        child_count = plug.numChildren()

    else:
        return

    indexes = range(child_count - 1, -1, -1) if reverse else range(child_count)
    for index in indexes:
        try:
            child = get_child(index)
        except RuntimeError:
            raise IndexError(
                "Internal Error trying to get child plug: {}[{}]"
                .format(plug.name(), index))
        # if not connection or ConnectionStatus.has_status(child, connection):
        yield child


def plug_has_source(plug, nested=False):
    """Return True if ``plug`` has any source connection, False otherwise.

    Args:
        nested (bool): If True, extend the check to all children in ``plug``
            hierarchy.

    Returns:
        bool:
    """
    stack = deque([plug])
    while stack:
        plug = stack.pop()
        if plug.isDestination:
            return True
        if nested:
            stack.extend(plug_children(plug))
    return False


def plug_has_destinations(plug, nested=False):
    """Return True if ``plug`` has any destination connection, False otherwise.

    Args:
        nested (bool): If True, extend the check to all children in ``plug``
            hierarchy.

    Returns:
        bool:
    """
    stack = deque([plug])
    while stack:
        plug = stack.pop()
        if plug.isSource:
            return True
        if nested:
            stack.extend(plug_children(plug))
    return False


def plug_has_connections(plug, nested=False):
    """Return True if ``plug`` has any source or destination connection.

    Convenience function that run both `.plug_has_source` and
    `.plug_has_destinations`.

    Args:
        nested (bool): If True, extend the check to all children in ``plug``
            hierarchy.

    Returns:
        bool:
    """
    return plug_has_source(plug, nested) or plug_has_destinations(plug, nested)
