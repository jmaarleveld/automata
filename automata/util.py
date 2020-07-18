##############################################################################
##############################################################################
# Imports
##############################################################################

import collections


##############################################################################
##############################################################################
# Dict classes
##############################################################################


class FrozenDict(collections.Mapping):

    def __new__(cls, mapping):
        if isinstance(mapping, FrozenDict):
            return mapping
        self = super().__new__(cls)
        self.__mapping = mapping.copy()
        return self

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__mapping})'

    def __getitem__(self, key):
        return self.__mapping[key]

    def __len__(self):
        return len(self.__mapping)

    def __iter__(self):
        yield from self.__mapping

    @property
    def dictionary(self):
        return self.__mapping


##############################################################################
##############################################################################
# Utility functions for transition functions
##############################################################################


def is_single_valued(mapping):
    return not any(isinstance(x, (set, frozenset)) for x in mapping.values())


def is_multi_valued(mapping):
    return all(isinstance(x, (set, frozenset)) for x in mapping.values())


def is_consistent(mapping):
    return is_single_valued(mapping) or is_multi_valued(mapping)


def to_multi_valued(mapping):
    assert is_single_valued(mapping)
    new_map = {key: {value} for key, value in mapping.items()}
    return freeze_map(new_map)


def freeze_map(mapping):
    new_map = {}
    for key, value in mapping.items():
        if isinstance(value, set):
            new_map[key] = frozenset(value)
        else:
            new_map[key] = value
    return FrozenDict(new_map)



