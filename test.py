from automata.regex_parser import *

regexes = (
    'abc',
    'a|b',
    'a*',
    '(a)',
    '(ab)*',
    'a|b*',
    'a|(ab)*',
    'a|(ab*)*',
    'a|bc*',
    'a|(bc)d*'
)

k = compile_regex('a')
assert k.run('a'), k.dump()
assert not k.run('b'), k.dump()
assert not k.run(''), k.dump()
assert not k.run('ab'), k.dump()
assert not k.run('ba'), k.dump()
assert not k.run('aa'), k.dump()

k = compile_regex('ab')
assert not k.run(''), k.dump()
assert not k.run('a'), k.dump()
assert not k.run('b'), k.dump()
assert not k.run('ba'), k.dump()
assert not k.run('aab'), k.dump()
assert k.run('ab'), k.dump()

k = compile_regex('a*')
assert k.run(''), k.dump()
assert k.run('aa'), k.dump()
assert k.run('aaa'), k.dump()
assert not k.run('ab'), k.dump()
assert not k.run('baa'), k.dump()

k = compile_regex('a|b')
assert not k.run(''), k.dump()
assert k.run('a'), k.dump()
assert k.run('b'), k.dump()
assert not k.run('ba'), k.dump()
assert not k.run('ab'), k.dump()
assert not k.run('aa'), k.dump()
assert not k.run('bb'), k.dump()


# Test loop detection

from automata.state import State
from automata.fsm import NeFSM
s = State()
k = NeFSM(states={s}, alphabet={'a'}, transitions={(s, ''): {s}}, initial=s, accepting={})
assert not k.run('a'), k.dump()


regex = '(a|b)*'
print_tree(parse_regex(regex))
k = compile_regex(regex)
#k.render()


k = compile_regex('(aa)|(ab)')
l = k.to_deterministic_fsm()

k = compile_regex('a')
l = k.to_deterministic_fsm()

k = compile_regex('a*')
l = k.to_deterministic_fsm()
l.render()


k = compile_regex('abc')
k.complement().render()
