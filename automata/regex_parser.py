import abc
import enum

from .fsm import NeFSM

##############################################################################
##############################################################################
# AST components
##############################################################################


class NodeType(enum.Enum):
    """Enum used to denote the type of Node objects.
    """
    UNION = enum.auto()
    CONCAT = enum.auto()
    KLEENE_STAR = enum.auto()


class Node:
    """Node type. Part of Regex Syntax Tree representation.

    :param typ: type of the Node. Is of type NodeType
    :param left: Left node of union and concat nodes.
                    Target of kleene star
    :param right: Right node of union and concat nodes.
                    None for kleene star.
    """

    def __init__(self, typ, left, right=None):
        self.type = typ
        self.left = left
        self.right = right


class Leaf:
    """Leaf of a regex syntax tree
    """

    def __init__(self, symbol):
        self.symbol = symbol


##############################################################################
##############################################################################
# AST Traversal
##############################################################################


def compile_regex(pattern):
    tree = parse_regex(pattern)
    return _tree_to_regex(tree)


def _tree_to_regex(tree):
    if isinstance(tree, Leaf):
        return NeFSM.atom_matcher(tree.symbol)
    assert isinstance(tree, Node)
    if tree.type == NodeType.UNION:
        return _tree_to_regex(tree.left) | _tree_to_regex(tree.right)
    elif tree.type == NodeType.CONCAT:
        return _tree_to_regex(tree.left) + _tree_to_regex(tree.right)
    elif tree.type == NodeType.KLEENE_STAR:
        return _tree_to_regex(tree.left).kleene_star()
    else:
        raise ValueError(tree.type)


def print_tree(tree, indent=0, indent_symbol=' '):
    if isinstance(tree, Leaf):
        print(indent*indent_symbol + f'Leaf: {tree.symbol}')
        return
    assert isinstance(tree, Node)
    if tree.type == NodeType.UNION:
        print(indent*indent_symbol + 'UNION:')
        print_tree(tree.left, indent+1, indent_symbol)
        print_tree(tree.right, indent+1, indent_symbol)
    elif tree.type == NodeType.CONCAT:
        print(indent*indent_symbol + 'CONCAT:')
        print_tree(tree.left, indent+1, indent_symbol)
        print_tree(tree.right, indent+1, indent_symbol)
    elif tree.type == NodeType.KLEENE_STAR:
        print(indent*indent_symbol + 'KLEENE_STAR:')
        print_tree(tree.left, indent+1, indent_symbol)
    else:
        raise ValueError(tree.type)


##############################################################################
##############################################################################
# Low-level regex parsing
##############################################################################


def parse_regex(pattern):
    """Parse a regex into a parse tree."""
    return _parse(iter(pattern))


def _parse(stream, recursive=False):
    current = []
    perform_union = False
    while True:
        try:
            c = next(stream)
        except StopIteration:
            if recursive:
                raise ValueError('End of input reached')
            break
        if _is_star(c):
            if perform_union:
                raise ValueError('Invalid syntax (1)')
            _fix_kleene_star(current)
        elif _is_union(c):
            if perform_union:
                raise ValueError('Invalid syntax (2)')
            perform_union = 2
        elif _is_close(c):
            if perform_union:
                raise ValueError('Invalid syntax (3)')
            if not recursive:
                raise ValueError('Unbalanced parentheses')
            break
        elif _is_open(c):
            current.append(_parse(stream, recursive=True))
        else:
            current.append(Leaf(c))
        if perform_union == 2:
            perform_union = 1
        elif perform_union == 1:
            a = current.pop()
            b = current.pop()
            current.append(Node(NodeType.UNION, b, a))
            perform_union = 0
    return _make_chain(current)


def _fix_kleene_star(nodes):
    if isinstance(nodes[-1], Node) and nodes[-1].type == NodeType.UNION:
        nodes[-1].right = Node(NodeType.KLEENE_STAR, nodes[-1].right)
    else:
        return nodes.append(Node(NodeType.KLEENE_STAR, nodes.pop()))


def _make_chain(nodes):
    if len(nodes) == 1:
        return nodes[0]
    front = nodes.pop(0)
    return Node(NodeType.CONCAT, front, _make_chain(nodes))


def _is_special(char):
    return any(
        (_is_star(char), _is_union(char), _is_open(char), _is_close(char))
    )


def _is_star(char):
    return char == '*'


def _is_union(char):
    return char == '|'


def _is_open(char):
    return char == '('


def _is_close(char):
    return char == ')'
