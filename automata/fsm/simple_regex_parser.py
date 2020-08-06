import abc
import enum
import warnings

from automata.fsm.fsm import NeFSM

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


def tree_to_fsm(tree):
    return _tree_to_regex(tree)


def _tree_to_regex(tree):
    if isinstance(tree, Leaf):
        return NeFSM.atom_matcher(tree.symbol)
    assert isinstance(tree, Node), (type(tree), tree)
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


def parse_regex(pattern, alphabet=None):
    """Parse a regex into a parse tree."""
    alphabet = alphabet if alphabet is not None else frozenset()
    tokens = _tokenize(iter(pattern), alphabet)
    tokens = _apply_epsilon_fill(tokens)
    _recursive_to_postfix(tokens)
    return _build_tree(tokens)


class TokenType(enum.Enum):
    # Basic regex tokens
    UNION = enum.auto()
    STAR = enum.auto()
    GROUP = enum.auto()
    SYMBOL = enum.auto()


class Token:

    def __init__(self, token_type, payload=None):
        self.type = token_type
        self.payload = payload

    def __repr__(self):
        return f'{self.__class__.__qualname__}({self.type}, {self.payload})'


def _tokenize(stream, alphabet, recursive=False):
    tokens = []
    while True:
        try:
            c = next(stream)
        except StopIteration:
            if recursive:
                raise ValueError('Reached end of input')
            break
        if _is_star(c):
            tokens.append(Token(TokenType.STAR))
        elif _is_open(c):
            tok = Token(TokenType.GROUP, _tokenize(stream,
                                                   alphabet,
                                                   recursive=True))
            tokens.append(tok)
        elif _is_close(c):
            if not recursive:
                raise ValueError('Unexpected closing bracket')
            break
        elif _is_union(c):
            tokens.append(Token(TokenType.UNION))
        elif _is_escape(c):
            tokens.append(Token(TokenType.SYMBOL, next(stream)))
        else:
            tokens.append(Token(TokenType.SYMBOL, c))
    return tokens


def _apply_epsilon_fill(tokens):
    new_tokens = []
    epsilon = Token(TokenType.SYMBOL, '')
    for index, token in enumerate(tokens):
        if token.type == TokenType.GROUP:
            token.payload = _apply_epsilon_fill(token.payload)
            new_tokens.append(token)
        elif token.type == TokenType.STAR:
            if index == 0 or tokens[index-1].type == TokenType.UNION:
                # Of the form 'x|*' or '*'. Will match exactly
                # the empty string
                new_tokens.append(epsilon)
                warnings.warn('Apply epsilon fill on kleene star')
            else:
                new_tokens.append(token)
        elif token.type == TokenType.UNION:
            if index == 0 or tokens[index-1].type == TokenType.UNION:
                # '|x' or '||x'. Insert epsilon
                new_tokens.append(epsilon)
                warnings.warn('Apply epsilon fill on union')
            new_tokens.append(token)
        else:
            new_tokens.append(token)
    if not new_tokens or new_tokens[-1].type == TokenType.UNION:
        warnings.warn(f'Trailing epsilon fill (empty={not new_tokens})')
        new_tokens.append(epsilon)
    return new_tokens


def _recursive_to_postfix(tokens):
    _to_postfix(tokens)
    for tok in tokens:
        if tok.type == TokenType.GROUP:
            _recursive_to_postfix(tok.payload)


def _to_postfix(tokens):
    index = 0
    n = len(tokens)
    while index < n:
        if tokens[index].type == TokenType.UNION:
            original = index
            # For the conversion algorithm, we want the
            # union token to be moved after the right most
            # consecutive kleene star token directly succeeding
            # the right hand operand of the current union token.
            #
            # Step 1) Increment the pointer to point to the
            #           right hand side operand
            index += 1
            # Step 2) Find consecutive kleene star tokens
            while index + 1 < n and tokens[index + 1].type == TokenType.STAR:
                index += 1
            # Step 3) Let the union token "bubble up" to its new
            #           position
            for i in range(original, index):
                tokens[i], tokens[i+1] = tokens[i+1], tokens[i]
        index += 1


def _build_tree(tokens):
    stack = []
    for token in tokens:
        if token.type == TokenType.SYMBOL:
            stack.append(Leaf(token.payload))
        elif token.type == TokenType.STAR:
            stack.append(Node(NodeType.KLEENE_STAR, stack.pop()))
        elif token.type == TokenType.GROUP:
            stack.append(_build_tree(token.payload))
        elif token.type == TokenType.UNION:
            right = stack.pop()
            left = stack.pop()
            stack.append(Node(NodeType.UNION, left, right))
        else:
            raise ValueError(token.type)
    # Insert concatenation
    return _make_chain(stack)


def _make_chain(nodes):
    if len(nodes) == 1:
        return nodes[0]
    front = nodes.pop(0)
    return Node(NodeType.CONCAT, front, _make_chain(nodes))


def _is_special(char):
    return any(
        (_is_star(char), _is_union(char),
         _is_open(char), _is_close(char),
         _is_escape(char))
    )


def _is_star(char):
    return char == '*'


def _is_union(char):
    return char == '|'


def _is_open(char):
    return char == '('


def _is_close(char):
    return char == ')'


def _is_set_open(char):
    return char == '['


def _is_set_close(char):
    return char == ']'


def _is_counter_open(char):
    return char == '{'


def _is_counter_close(char):
    return char == '}'


def _is_escape(char):
    return char == '\\'


def _is_hat(char):
    return char == '^'
