from ape import reverts
from pytest import fixture

ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'
UNIT = 10**18

@fixture
def token(project, deployer):
    return project.MockToken.deploy(sender=deployer)

@fixture
def treasury(project, deployer):
    return project.Treasury.deploy(sender=deployer)

def test_to_management(deployer, token, treasury):
    token.mint(treasury, 3 * UNIT, sender=deployer)
    
    treasury.to_management(token, UNIT, sender=deployer)
    assert token.balanceOf(treasury) == 2 * UNIT
    assert token.balanceOf(deployer) == UNIT

    treasury.to_management(token, sender=deployer)
    assert token.balanceOf(treasury) == 0
    assert token.balanceOf(deployer) == 3 * UNIT

def test_to_management_permission(deployer, alice, token, treasury):
    token.mint(treasury, UNIT, sender=deployer)
    with reverts():
        treasury.to_management(token, sender=alice)
    treasury.to_management(token, sender=deployer)

def test_transfer_management(deployer, alice, bob, treasury):
    assert treasury.management() == deployer
    assert treasury.pending_management() == ZERO_ADDRESS

    with reverts():
        treasury.set_management(alice, sender=alice)
    with reverts():
        treasury.accept_management(sender=alice)
 
    treasury.set_management(alice, sender=deployer)
    assert treasury.management() == deployer
    assert treasury.pending_management() == alice

    with reverts():
        treasury.accept_management(sender=bob)
    
    treasury.accept_management(sender=alice)
    assert treasury.management() == alice
    assert treasury.pending_management() == ZERO_ADDRESS
