from ape import reverts
from pytest import fixture

DUMMY = '0x0000000000000000000000000000000000000001'
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'

@fixture
def guard(project, deployer, alice):
    return project.Guard.deploy(ZERO_ADDRESS, deployer, alice, sender=deployer)

def test_whitelist(deployer, alice, guard):
    with reverts():
        guard.set_whitelist(DUMMY, sender=alice)

    assert not guard.whitelist(DUMMY)
    guard.set_whitelist(DUMMY, sender=deployer)
    assert guard.whitelist(DUMMY)
    guard.set_whitelist(DUMMY, False, sender=deployer)
    assert not guard.whitelist(DUMMY)
