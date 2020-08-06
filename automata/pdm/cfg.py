##############################################################################
##############################################################################
# Imports
##############################################################################

import string

from .. import constants


##############################################################################
##############################################################################
# Grammar Builder
##############################################################################


class CFGBuilder:
    """Class used for building context free grammar objects.

    This class can be used in multiple manners.
    You will always have to instantiate the class. Next,
    you can add rules using the add_rule and add_rules methods.

    This class was designed for use with the builder pattern,
    meaning you can declare a grammar in the following manner:

    >>> grammar = (CFGBuilder()
    ...     .add_rules('S', 'AS', 'BS', '')
    ...     .add_rules('A', 'aA', '')
    ...     .add_rules('B', 'bB', 'C')
    ...     .add_rule('C', 'c')
    ...     .finalize(start='S'))
    """

    def __init__(self):
        self.__nonterminals = set()
        self.__terminals = set()
        self.__rules = set()
        self.__start = None

    @classmethod
    def from_grammar(cls, grammar):
        self = cls()
        for nonterminal, expansion in grammar.rules:
            self.add_rule(nonterminal, expansion)
        return self

    def add_rules(self, nonterminal, *expansions):
        """Add a set of rules to the grammar.

        :param nonterminal: Nonterminal to be expanded
        :param expansions: Possible expansions for the nonterminal
        """
        self.__check_not_finalized()
        for expansion in expansions:
            self.add_rule(nonterminal, expansion)
        return self

    def add_rule(self, nonterminal, expansion):
        """Add a single rule to the grammar.

        :param nonterminal: Nonterminal to be expanded
        :param expansion: Expansion of the nonterminal
        """
        self.__check_not_finalized()
        assert len(nonterminal) == 1
        self.__nonterminals.add(nonterminal)
        self.__rules.add((nonterminal, expansion))
        return self

    def finalize(self, *, start):
        """Finalize grammar creation and build the actual
        grammar object

        :param start: Starting symbol of the grammar
        :return: The created context free grammar
        """
        self.__check_not_finalized()
        assert start in self.__nonterminals
        self.__start = start
        for a, w in self.__rules:
            self.__nonterminals.add(a)
            for x in w:
                self.__terminals.add(x)
        self.__terminals -= self.__nonterminals
        return ContextFreeGrammar(nonterminals=self.__nonterminals,
                                  terminals=self.__terminals,
                                  rules=self.__rules,
                                  start=self.__start)

    def __check_not_finalized(self):
        if self.__start is None:
            return
        raise ValueError('Grammar already finalized')


##############################################################################
##############################################################################
# Helper classes
##############################################################################


class Nonterminal:

    def __init__(self, symbol, children=()):
        self.symbol = symbol
        self.children = list(children)


class Terminal:

    def __init__(self, symbol):
        self.symbol = symbol


##############################################################################
##############################################################################
# Grammar class
##############################################################################


class ContextFreeGrammar:

    def __init__(self, nonterminals, terminals, rules, start):
        self.__nonterminals = frozenset(nonterminals)
        self.__terminals = frozenset(terminals)
        self.__rules = frozenset(rules)
        self.__start = start

    @property
    def nonterminals(self):
        return self.__nonterminals

    @property
    def terminals(self):
        return self.__terminals

    @property
    def rules(self):
        return self.__rules

    @property
    def start(self):
        return self.__start

    ### Helper functions ###

    @staticmethod
    def _get_rules_for(nonterminal, rules):
        return {(x, y) for x, y in rules if x == nonterminal}

    ### Form checking ###

    def _start_is_recursive(self):
        generated = self._collect_generated(self.nonterminals,
                                            self.terminals,
                                            self.rules,
                                            self.start)
        for a, w in self.rules:
            if a in generated and self.start in w:
                return True
        return False

    def is_essentially_noncontracting(self):
        # No nullable nonterminals
        nullables = self._collect_nullables(self.nonterminals, self.rules)
        if not nullables.issubset({self.start}):
            return False
        return not self._start_is_recursive()

    def is_productive(self):
        if not self.is_essentially_noncontracting():
            return False
        # No chain rules
        for x in self.nonterminals:
            if x == self.start:
                continue
            for y in self.nonterminals:
                if (x, y) in self.rules:
                    return False
        return True

    def _collect_generating(self, nonterminals, terminals, rules):
        generating = set()
        while True:
            prev = generating.copy()
            generating |= {v
                           for v in (nonterminals - generating)
                           for _, expansion in self._get_rules_for(v, rules)
                           if set(expansion).issubset(generating | terminals)}
            if prev == generating:
                break
        return generating

    @staticmethod
    def _collect_generated(nonterminals, terminals, rules, start):
        generated = {start}
        while True:
            prev = generated.copy()
            generated |= {x
                          for x in ((nonterminals | terminals) - generated)
                          for a, w in rules
                          if a in generated and w.count(x) >= 1}
            if prev == generated:
                break
        return generated

    def _collect_nullables(self, nonterminals, rules):
        nullables = set()
        while True:
            prev = nullables.copy()
            nullables |= {v
                          for v in (nonterminals - nullables)
                          for _, expansion in self._get_rules_for(v, rules)
                          if set(expansion).issubset(nullables)}
            if prev == nullables:
                break
        return nullables

    def _expand_nullables(self, expansion, nullables):
        if not expansion:
            yield ''
        elif expansion[0] not in nullables:
            for suffix in self._expand_nullables(expansion[1:], nullables):
                yield expansion[0] + suffix
        else:
            for suffix in self._expand_nullables(expansion[1:], nullables):
                yield expansion[0] + suffix
                yield suffix

    def _expand_chain_rules(self, expansion, chain_rules):
        if not expansion:
            yield ''
            return
        expansions = list(
            self._expand_chain_rules(expansion[1:], chain_rules))
        for suffix in expansions:
            yield expansion[0] + suffix
        if expansion[0] in self.nonterminals:
            for a, b in chain_rules:
                if expansion[0] == a:
                    for suffix in expansions:
                        yield b + suffix

    ### Grammar conversion ###

    def remove_useless_symbols(self):
        generating = self._collect_generating(self.nonterminals,
                                              self.terminals,
                                              self.rules)
        nonterminals = self.nonterminals & (generating | {self.start})
        sententials = nonterminals | self.terminals
        rules = {(a, w)
                 for a, w in self.rules
                 if set(w).issubset(sententials)}
        generated = self._collect_generated(nonterminals,
                                            self.terminals,
                                            rules,
                                            self.start)
        nonterminals &= generated
        terminals = self.terminals & generated
        sententials = nonterminals | terminals
        rules = {(a, w) for a, w in rules if set(w).issubset(sententials)}
        return self.__class__(nonterminals=nonterminals,
                              terminals=terminals,
                              rules=rules,
                              start=self.start)

    def make_essentially_noncontracting(self):
        if self._start_is_recursive():
            for name in string.ascii_uppercase:
                if not (name in self.nonterminals or name in self.terminals):
                    new = self.__class__(
                        nonterminals=self.nonterminals | {name},
                        terminals=self.terminals,
                        rules=self.rules | {(name, self.start)},
                        start=name
                    )
                    return new.make_essentially_noncontracting()
            raise ValueError('Could not find new start symbol name')
        nullables = self._collect_nullables(self.nonterminals, self.rules)
        rules = set()
        for nonterminal, expansion in self.rules:
            for new_expansion in self._expand_nullables(expansion, nullables):
                if new_expansion == '' and nonterminal != self.start:
                    continue
                rules.add((nonterminal, new_expansion))
        new = self.__class__(nonterminals=self.nonterminals,
                             terminals=self.terminals,
                             rules=rules,
                             start=self.start)
        return new.remove_useless_symbols()

    def make_productive(self):
        if not self.is_essentially_noncontracting():
            new = self.make_essentially_noncontracting()
            return new.make_productive()
        chain_rules = {(a, w)
                       for a, w in self.rules
                       if len(w) == 1 and w in self.nonterminals}
        for i in range(len(self.nonterminals)):
            rules = chain_rules.copy()
            for a, b in chain_rules:
                for c, d in chain_rules:
                    if b == c:
                        rules.add((a, d))
            chain_rules = rules
        rules = set()
        for nonterminal, expansion in self.rules:
            expansions = self._expand_chain_rules(expansion, chain_rules)
            for new_expansion in expansions:
                rules.add((nonterminal, new_expansion))
        rules = {(a, b)
                 for a, b in rules
                 if a == self.start or b not in self.nonterminals}
        new = self.__class__(nonterminals=self.nonterminals,
                             terminals=self.terminals,
                             rules=rules,
                             start=self.start)
        return new.remove_useless_symbols()

    ### Parsing ###

    def derive(self, word: str):
        pass

    ### Debugging ###

    def print_rules(self):
        todo = set(self.nonterminals)
        self._print_rules(self.start)
        todo.remove(self.start)
        while todo:
            self._print_rules(todo.pop())

    def _print_rules(self, nonterminal):
        print(nonterminal, '->', end=' ')
        expansions = [repr(w) for a, w in self.rules if a == nonterminal]
        suffix = ' | '.join(expansions)
        print(suffix)


class Node:

    def __init__(self, name, *children):
        self.name = name
        self.children = list(children)


class Leaf:

    def __init__(self, symbol):
        self.symbol = symbol
