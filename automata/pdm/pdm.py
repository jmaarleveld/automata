##############################################################################
##############################################################################
# Imports
##############################################################################

import typing

from .. import runners
from .. import constants
from .. import util
from automata.match import SimpleMatch
from ..runners import RunnerState
from ..state import State
from .cfg import ContextFreeGrammar

##############################################################################
##############################################################################
# Runner
##############################################################################


class _PDMConfig(typing.NamedTuple):
    string: str
    stack: str
    state: State


class _PDMRunner(runners.Runner):

    def get_initial_config(self, word):
        return _PDMConfig(word, '', self.initial_state)

    def get_keys(self, configuration):
        yield configuration.state, constants.EPSILON, constants.EPSILON
        if configuration.string:
            yield (configuration.state,
                   configuration.string[0],
                   constants.EPSILON)
            if configuration.stack:
                yield (configuration.state,
                       configuration.string[0],
                       configuration.stack[-1])
        if configuration.stack:
            yield (configuration.state,
                   constants.EPSILON,
                   configuration.stack[-1])

    def get_next_config(self, config, key, new_state):
        symbol, pop = key
        state, push = new_state
        stack = (config.stack[:-1]
                 if pop != constants.EPSILON else config.stack)
        string = (config.string[1:]
                  if symbol != constants.EPSILON else config.string)
        stack = (stack + push) if push != constants.EPSILON else stack
        return _PDMConfig(string, stack, state)

    def check_accept(self, config) -> RunnerState:
        if (not config.string) and (not config.stack):
            if config.state in self.accepting_states:
                return RunnerState.ACCEPT
        return RunnerState.CONTINUE

    def check_accept_sliding(self, config) -> RunnerState:
        return self.check_accept(config)

    def make_match(self, word, config) -> SimpleMatch:
        stop = len(word) - len(config.string)
        return SimpleMatch(0, stop, word[:stop])


##############################################################################
##############################################################################
# PDM class
##############################################################################


class PDM:

    def __init__(self, states, alphabet, stack_alphabet,
                 transitions, initial, accepting):
        self.__states = frozenset(states)
        self.__alphabet = frozenset(alphabet)
        self.__stack_alphabet = frozenset(stack_alphabet)
        self.__transitions = util.freeze_map(transitions)
        self.__start = initial
        self.__accepting = frozenset(accepting)
        self.runner = _PDMRunner(start=self.start,
                                 transitions=self.transitions,
                                 accepting=self.accepting,
                                 multi_valued=True)

    @classmethod
    def from_cfg(cls, grammar: ContextFreeGrammar):
        start = State()
        accept = State()
        key = (start, constants.EPSILON, constants.EPSILON)
        transitions = {key: (accept, grammar.start)}

    def run(self, word):
        return self.runner.run_with(word) == RunnerState.ACCEPT

    @property
    def states(self):
        return self.__states

    @property
    def alphabet(self):
        return self.__alphabet

    @property
    def stack_alphabet(self):
        return self.__stack_alphabet

    @property
    def transitions(self):
        return self.__transitions

    @property
    def start(self):
        return self.__start

    @property
    def accepting(self):
        return self.__accepting

    ### Operational interface ###

    def __or__(self, other):
        if not isinstance(other, PDM):
            return NotImplemented
        return self.union(other)

    def __add__(self, other):
        if not isinstance(other, PDM):
            return NotImplemented
        return self.concat(other)

    def concat(self, other):
        a = self.to_normal_form()
        b = other.to_normal_form()
        transitions = {**a.transitions, **b.transitions}
        self._add_epsilon_transition(transitions,
                                     next(iter(a.accepting)),
                                     b.start)
        return self.__class__(alphabet=a.alphabet | b.alphabet,
                              stack_alphabet=a.stack_alphabet | b.stack_alphabet,
                              states=a.states | b.states,
                              transitions=transitions,
                              initial=a.start,
                              accepting=b.accepting)

    def union(self, other):
        a = self.to_normal_form()
        b = other.to_normal_form()
        transitions = {**a.transitions, **b.transitions}
        start = State()
        accept = State()
        self._add_epsilon_transition(transitions, start, a.start)
        self._add_epsilon_transition(transitions, start, b.start)
        for x in a.accepting:
            self._add_epsilon_transition(transitions, x, accept)
        for x in b.accepting:
            self._add_epsilon_transition(transitions, x, accept)
        return self.__class__(alphabet=a.alphabet | b.alphabet,
                              stack_alphabet=a.stack_alphabet | b.stack_alphabet,
                              states=a.states | b.start | {start, accept},
                              transitions=transitions,
                              initial=start,
                              accepting={accept})

    def kleene_star(self):
        x = self.to_normal_form()
        start = State()
        accept = State()
        transitions = x.transitions.dictionary.copy()
        self._add_epsilon_transition(transitions, start, x.start)
        for end in x.accepting:
            self._add_epsilon_transition(transitions, end, start)
        self._add_epsilon_transition(transitions, start, accept)
        return self.__class__(alphabet=x.alphabet,
                              stack_alphabet=x.stack_alphabet,
                              states=x.states | {start, accept},
                              transitions=transitions,
                              initial=start,
                              accepting={accept})

    ### Normal form support ###

    def to_normal_form(self):
        transitions = self.transitions.dictionary.copy()
        prev = list(self._get_all_prev_states(self.start))
        if len(prev) > 0:
            start = State()
            transitions[(start, constants.EPSILON)] = {self.start}
        else:
            start = self.start
        if not self._accepting_states_in_normal_form():
            accept = State()
            for state in self.accepting:
                self._add_epsilon_transition(transitions, state, accept)
        else:
            accept = next(iter(self.accepting))
        return self.__class__(states=self.states | {start, accept},
                              alphabet=self.alphabet,
                              stack_alphabet=self.stack_alphabet,
                              transitions=util.freeze_map(transitions),
                              initial=start,
                              accepting={accept})

    def _accepting_states_in_normal_form(self):
        if len(self.accepting) != 1:
            # Need to add a final state if we have none
            return False
        accept = next(iter(self.accepting))
        for symbol in self.alphabet | {constants.EPSILON}:
            for stack in self.stack_alphabet | {constants.EPSILON}:
                if (accept, symbol, stack) in self.transitions:
                    return False
        return True

    ### Utility methods ###

    def _get_all_prev_states(self, state):
        states = []
        for (old, _, _), (news, _) in self.transitions.items():
            if state in news:
                states.append(old)
        return tuple(states)

    @staticmethod
    def _add_epsilon_transition(transitions, old, new):
        key = (old, constants.EPSILON, constants.EPSILON)
        if key in transitions:
            transitions[key] |= {new}
        else:
            transitions[key] = {new}

    ### Debugging ###

    def render(self):
        from .. import debug

        class PDMFormatter(debug.Formatter):

            @staticmethod
            def get_source_uid(key):
                old, _, _ = key
                return str(old.uid)

            @staticmethod
            def get_target_uid(value):
                new, _ = value
                return str(new.uid)

            @staticmethod
            def get_label(key, value):
                _, symbol, pop = key
                _, push = value
                return f'{symbol}{pop}/{push}'

        debug.render(states=self.states,
                     transitions=self.transitions,
                     start=self.start,
                     accepting=self.accepting,
                     formatter=PDMFormatter)