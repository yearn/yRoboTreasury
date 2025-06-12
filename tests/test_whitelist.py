from ape import reverts
from pytest import fixture

DUMMY = '0x0000000000000000000000000000000000000001'
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'

@fixture
def whitelist(project, deployer, alice):
    return project.Whitelist.deploy(ZERO_ADDRESS, deployer, alice, sender=deployer)

def test_whitelist(deployer, alice, whitelist):
    with reverts():
        whitelist.set_whitelist(DUMMY, sender=alice)

    assert not whitelist.whitelist(DUMMY)
    whitelist.set_whitelist(DUMMY, sender=deployer)
    assert whitelist.whitelist(DUMMY)
    whitelist.set_whitelist(DUMMY, False, sender=deployer)
    assert not whitelist.whitelist(DUMMY)
