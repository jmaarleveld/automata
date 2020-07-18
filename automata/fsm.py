##############################################################################
##############################################################################
# Imports
##############################################################################

import typing

from . import constants
from .runners import Runner, RunnerState
from .state import State

from .util import FrozenDict
from . import util

##############################################################################
##############################################################################
# Runners
##############################################################################


class _FSMConfig(typing.NamedTuple):
    string: str
    state: State


class _DFSMRunner(Runner):

    def get_initial_config(self, word):
        return _FSMConfig(word, self.initial_state)

    def get_key(self, configuration):
        if configuration.string:
            return configuration.state, configuration.string[0]
        return configuration.state, constants.EPSILON

    def get_nondeterministic_key(self, configuration):
        return

    def get_next_config(self, config, key, new_state):
        return _FSMConfig(config.string[1:], new_state)

    def check_accept(self, config) -> RunnerState:
        if config.string:
            return RunnerState.CONTINUE
        return RunnerState.from_bool(config.state in self.accepting_states)


class _NeFSMRunner(_DFSMRunner):

    def get_nondeterministic_key(self, configuration):
        return configuration.state, constants.EPSILON

    def get_next_config(self, config, key, new_state):
        if key[1] == constants.EPSILON:
            return _FSMConfig(config.string, new_state)
        return super().get_next_config(config, key, new_state)

    def check_accept(self, config) -> RunnerState:
        result = super().check_accept(config)
        if result != RunnerState.REJECT:
            return result
        if (config.state, constants.EPSILON) in self.transitions:
            return RunnerState.CONTINUE
        return RunnerState.REJECT


##############################################################################
##############################################################################
# Deterministic machine
##############################################################################


class DFSM:

    def __init__(self, states, alphabet, transitions, initial, accepting):
        self.__states = frozenset(states)
        self.__alphabet = frozenset(alphabet)
        if util.is_multi_valued(transitions):
            self.__transitions = util.freeze_map(transitions)
        else:
            self.__transitions = util.to_multi_valued(transitions)  # is frozen
        self.__start = initial
        self.__accepting = frozenset(accepting)
        self.runner = _DFSMRunner(self.__start,
                                  self.__accepting,
                                  self.__transitions,
                                  multi_valued=True)

    ### Getter functions ###

    @property
    def states(self):
        return self.__states

    @property
    def alphabet(self):
        return self.__alphabet

    @property
    def transitions(self):
        return self.__transitions

    @property
    def start(self):
        return self.__start

    @property
    def accepting(self):
        return self.__accepting

    ### Running interface ###


    def run(self, word):
        return self.runner.run_with(word) == RunnerState.ACCEPT

    ### Conversion interface ###

    def __bool__(self):
        m = self.simplify()
        is_empty = len(m.accepting) == 0 and len(m.transitions) == 0
        return not is_empty

    ### Operational interface ###

    def complement(self):
        m = self.make_total()
        return self.__class__(states=m.__states,
                              alphabet=m.__alphabet,
                              transitions=m.__transitions,
                              initial=m.__start,
                              accepting=m.__states - m.__accepting)

    def __invert__(self):
        return self.complement()

    def __or__(self, other):
        return NeFSM.from_dfsm(self) | other

    def __ror__(self, other):
        return other | NeFSM.from_dfsm(self)

    def __and__(self, other):
        return NeFSM.from_dfsm(self) & other

    def __rand__(self, other):
        return other & NeFSM.from_dfsm(self)

    def __sub__(self, other):
        return self & ~other

    ### Comparison ###

    __hash__ = None

    def __eq__(self, other):
        if not isinstance(other, DFSM):
            return False
        return bool(self - other) and bool(other - self)

    def __ne__(self, other):
        return not (self == other)

    def is_subset(self, other):
        return not bool(self - other)

    def __le__(self, other):
        return self.is_subset(other)

    def is_proper_subset(self, other):
        return self <= other and bool(other - self)

    def __lt__(self, other):
        return self.is_proper_subset(other)

    def is_superset(self, other):
        return not bool(other - self)

    def is_proper_superset(self, other):
        return self >= other and bool(self - other)

    def __ge__(self, other):
        return self.is_superset(other)

    def __gt__(self, other):
        return self.is_proper_superset(other)

    ### Misc methods ###

    def simplify(self):
        useless = self._get_useless_states()
        if self.__start in useless:
            return self._empty_machine()
        transitions = self.__transitions.dictionary.copy()
        unreachable = self._get_unreachable_states()
        remove = unreachable | useless
        for key, new in list(transitions.items()):
            if new in remove:
                del transitions[key]
        return self.__class__(states=self.__states - remove,
                              alphabet=self.__alphabet,
                              transitions=util.freeze_map(transitions),
                              initial=self.__start,
                              accepting=self.__states - remove)

    def make_total(self):
        if self.is_total():
            return self
        trash_state = State()
        transitions = self.transitions.dictionary.copy()
        for state in self.states:
            for symbol in self.alphabet:
                if (state, symbol) not in self.transitions:
                    transitions[(state, symbol)] = {trash_state}
        for symbol in self.alphabet:
            transitions[(trash_state, symbol)] = {trash_state}
        return self.__class__(alphabet=self.alphabet,
                              states=self.states | {trash_state},
                              initial=self.start,
                              accepting=self.accepting,
                              transitions=util.freeze_map(transitions))

    def is_total(self):
        for state in self.states:
            for symbol in self.alphabet:
                if (state, symbol) not in self.transitions:
                    return False
        return True

    ### Helper methods -- Create machines ###

    def _empty_machine(self):
        state = State()
        return self.__class__(states={state},
                              alphabet=self.__alphabet,
                              transitions=FrozenDict({}),
                              accepting=set(),
                              initial=state)

    ### Helper methods -- Collect states ###

    def _get_unreachable_states(self):
        reachable = set()
        new = {self.__start}
        while new:
            reachable |= new
            old = new
            new = set()
            for state in old:
                for new_state in self._get_all_next_states(state):
                    new.add(new_state)
        return self.__states - reachable

    def _get_useless_states(self):
        useful = set()
        new = self.__accepting
        while new:
            useful |= new
            old = new
            new = set()
            for state in old:
                for new_state in self._get_all_prev_states(state):
                    new.add(new_state)
        return self.__states - useful

        ### Helper methods -- Collect states ###

    def _get_all_next_states(self, state):
        for char in self.alphabet:
            key = (state, char)
            if key in self.transitions:
                yield from self.transitions[key]

    def _get_all_prev_states(self, state):
        for (old, _), new in self.transitions.items():
            if state in new:
                yield old

    ### Debugging methods ###

    def dump(self):
        names = {}
        for i, state in enumerate(self.states):
            names[state] = chr(ord('A') + i)
        print('Start:', names[self.start])
        print('Accepting:', ', '.join(names[s] for s in self.accepting))
        for (old, symbol), news in self.transitions.items():
            for new in news:
                print(f'{names[old]} --> {names[new]}: {symbol!r}')

    def render(self):
        from graphviz import Digraph
        import string
        import random
        dot = Digraph()
        dot.attr('node', shape='circle')

        names = {}

        def name(x):
            if x not in names:
                y = random.choice(string.ascii_uppercase)
                while y in names.values():
                    y += random.choice(string.ascii_uppercase)
                names[x] = y
            return names[x]

        for state in self.states:
            if state in self.accepting:
                dot.attr('node', shape='doublecircle')
            elif state == self.start:
                dot.attr('node', shape='diamond')
            dot.node(str(state.uid), name(state.uid))
            dot.attr('node', shape='circle')

        for (old, symbol), news in self.transitions.items():
            for new in news:
                dot.edge(str(old.uid), str(new.uid), label=symbol)

        print(dot.source)
        dot.render('fsm.gv', view=True)


##############################################################################
##############################################################################
# Nondeterministic machines
##############################################################################


class NeFSM(DFSM):

    def __init__(self, states, alphabet, transitions, initial, accepting):
        super().__init__(states, alphabet, transitions, initial, accepting)
        assert util.is_multi_valued(transitions)
        self.runner = _NeFSMRunner(start=self.start,
                                   accepting=self.accepting,
                                   transitions=self.transitions,
                                   multi_valued=True)

    @classmethod
    def from_dfsm(cls, machine: DFSM):
        return cls(alphabet=machine.alphabet,
                   states=machine.states,
                   accepting=machine.accepting,
                   transitions=machine.transitions,
                   initial=machine.start)

    @classmethod
    def atom_matcher(cls, symbol):
        start = State()
        accept = State()
        transitions = {
            (start, symbol): {accept}
        }
        return cls(states={start, accept},
                   alphabet={symbol},
                   transitions=util.freeze_map(transitions),
                   initial=start,
                   accepting={accept})

    ### Operations ###

    def concat(self, other):
        a = self.to_normal_form()
        b = other.to_normal_form()
        transitions = {**a.transitions, **b.transitions}
        a_accept = next(iter(a.accepting))
        b_accept = next(iter(b.accepting))
        transitions[(a_accept, constants.EPSILON)] = {b.start}
        return self.__class__(states=a.states | b.states,
                              alphabet=a.alphabet | b.alphabet,
                              transitions=util.freeze_map(transitions),
                              initial=a.start,
                              accepting={b_accept})

    def union(self, other):
        a = self.to_normal_form()
        b = other.to_normal_form()
        transitions = {**a.transitions, **b.transitions}
        a_accept = next(iter(a.accepting))
        b_accept = next(iter(b.accepting))
        start = State()
        accept = State()
        transitions[(start, constants.EPSILON)] = {a.start, b.start}
        transitions[(a_accept, constants.EPSILON)] = {accept}
        transitions[(b_accept, constants.EPSILON)] = {accept}
        return self.__class__(states=a.states | b.states | {start, accept},
                              alphabet=a.alphabet | b.alphabet,
                              transitions=util.freeze_map(transitions),
                              initial=start,
                              accepting={accept})

    def __add__(self, other):
        return self.concat(other)

    def __or__(self, other):
        return self.union(other)

    def intersection(self, other):
        return ~(~self | ~other)

    def __and__(self, other):
        return self.intersection(other)

    def kleene_star(self):
        state = State()
        x = self.to_normal_form()
        accept = next(iter(x.accepting))
        transitions = x.transitions.dictionary.copy()
        transitions[(state, constants.EPSILON)] = {x.start}
        transitions[(accept, constants.EPSILON)] = {state}
        return self.__class__(states=x.states | {state},
                              alphabet=x.alphabet,
                              transitions=util.freeze_map(transitions),
                              initial=state,
                              accepting={state}).to_normal_form()

    def complement(self):
        # Complement requires a total, deterministic machine
        return self.to_deterministic_fsm().complement()

    ### misc methods ###

    def to_normal_form(self):
        transitions = self.transitions.dictionary.copy()
        prev = list(self._get_all_prev_states(self.start))
        if len(prev) > 0:
            start = State()
            transitions[(start, constants.EPSILON)] = {self.start}
        else:
            start = self.start
        if len(self.accepting) > 1:
            accept = State()
            for state in self.accepting:
                transitions[(state, constants.EPSILON)] = {accept}
        else:
            accept = next(iter(self.accepting))
        return self.__class__(states=self.states | {start, accept},
                              alphabet=self.alphabet,
                              transitions=util.freeze_map(transitions),
                              initial=start,
                              accepting={accept})

    def to_deterministic_fsm(self):
        transitions = {}
        accepting = set()
        initial = State()
        key = tuple(self._get_epsilon_closure(self.start))
        supersets = {
            key: initial
        }
        stack = [key]
        while stack:
            current = stack.pop()
            for symbol in self.alphabet:
                superstate = self._construct_superset(current, symbol)
                if not superstate:
                    continue
                if superstate not in supersets:
                    stack.append(superstate)
                try:
                    state = supersets[superstate]
                except KeyError:
                    state = State()
                supersets[superstate] = state
                transitions[(supersets[current], symbol)] = state
                if set(superstate) & self.accepting:
                    accepting.add(state)
        return DFSM(alphabet=self.alphabet,
                    states=frozenset(supersets.values()),
                    transitions=util.freeze_map(transitions),
                    initial=initial,
                    accepting=accepting)

    # TODO: implement cache
    def _get_epsilon_closure(self, state):
        closure = set()
        new = {state}
        while new:
            closure |= new
            old = new
            new = set()
            for node in old:
                key = (node, constants.EPSILON)
                if key in self.transitions:
                    for target in self.transitions[key]:
                        new.add(target)
        return closure

    def _construct_superset(self, old, symbol):
        states = set()
        for state in old:
            key = (state, symbol)
            if key in self.transitions:
                for new in self.transitions[key]:
                    states |= self._get_epsilon_closure(new)
        return tuple(states)
