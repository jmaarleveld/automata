import collections.abc
import itertools
import math
import operator
import warnings

from .regex_parser import *
from . import fsm


class RegularSet(collections.abc.Set):

    def __init__(self, regex):
        self.__regex = regex
        self.__tree = parse_regex(self.__regex)
        self.__fsm = tree_to_fsm(self.__tree)

    @property
    def fsm(self):
        return self.__fsm

    @property
    def regex(self):
        return self.__regex

    @property
    def tree(self):
        return self.__tree

    def __contains__(self, x: object) -> bool:
        if not isinstance(x, str):
            method = f'{self.__class__.__qualname__}.__contains__'
            warnings.warn(f'{method} called with non-string type')
            return False
        return self.__fsm.run(x)

    def _cmp(self, other, op):
        if not isinstance(other, RegularSet):
            return NotImplemented
        return op(self.fsm, other.fsm)

    def __lt__(self, other):
        return self._cmp(other, operator.lt)

    def __le__(self, other):
        return self._cmp(other, operator.le)

    def __gt__(self, other):
        return self._cmp(other, operator.gt)

    def __ge__(self, other):
        return self._cmp(other, operator.ge)

    is_subset = __le__
    is_proper_subset = __lt__
    is_superset = __ge__
    is_proper_superset = __gt__

    def _op(self, other, op):
        if not isinstance(other, RegularSet):
            return NotImplemented
        return self.__class__(op(self, other))

    def __add__(self, other):
        return self._op(other, lambda x, y: f'({x.regex})({y.regex})')

    def __sub__(self, other):
        return self._op(other, lambda x, y: (x.fsm - y.fsm).to_regex())

    def __or__(self, other):
        return self._op(other, lambda x, y: f'({x.regex})|({y.regex})')

    def __and__(self, other):
        return self._op(other, lambda x, y: (x.fsm & y.fsm).to_regex())

    def __invert__(self):
        return self.__class__((~self.fsm).to_regex())

    concat = __add__
    union = __or__
    intersection = __and__
    complement = __invert__

    def __len__(self) -> int:
        size = self._calc_tree_size(self.__tree)
        if math.isinf(size):
            raise ValueError('Cannot compute length of infinite set')
        return size

    def cardinality(self):
        return self._calc_tree_size(self.__tree)

    def _calc_tree_size(self, tree):
        if isinstance(tree, Leaf):
            return 1
        assert isinstance(tree, Node)
        if tree.type == NodeType.CONCAT:
            left = self._calc_tree_size(tree.left)
            right = self._calc_tree_size(tree.right)
            return left*right
        elif tree.type == NodeType.UNION:
            left = self._calc_tree_size(tree.left)
            right = self._calc_tree_size(tree.right)
            return left + right
        elif tree.type == NodeType.KLEENE_STAR:
            return float('inf')
        else:
            raise ValueError(tree.type)

    def __iter__(self):
        return _RegularSetIterator(self.__tree)


class _RegularSetIterator(collections.abc.Iterator):

    def __init__(self, tree):
        self.__tree = tree
        self.__it = self._tree_iterator(self.__tree)

    def _tree_iterator(self, tree):
        if isinstance(tree, Leaf):
            yield tree.symbol
        else:
            assert isinstance(tree, Node)
            if tree.type == NodeType.CONCAT:
                for left in self._tree_iterator(tree.left):
                    for right in self._tree_iterator(tree.right):
                        yield left + right
            elif tree.type == NodeType.UNION:
                yield from self._tree_iterator(tree.left)
                yield from self._tree_iterator(tree.right)
            elif tree.type == NodeType.KLEENE_STAR:
                yield ''
                for i in itertools.count(start=1):
                    for x in self._tree_iterator(tree.left):
                        yield i*x
            else:
                raise ValueError(tree.type)

    def __next__(self):
        return next(self.__it)
