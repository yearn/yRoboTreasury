from ape import reverts, Contract
from pytest import fixture

AUCTION_FACTORY = '0xa076c247AfA44f8F006CA7f21A4EF59f7e4dc605'

ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'
UNIT = 10**18

@fixture
def treasury(accounts):
    return accounts[4]

@fixture
def robo(project, deployer):
    return project.MockRobo.deploy(sender=deployer)

@fixture
def auction_factory():
    return Contract(AUCTION_FACTORY)

@fixture
def factory(project, deployer, treasury, robo, auction_factory):
    factory = project.Factory.deploy(treasury, robo, auction_factory, sender=deployer)
    robo.set_factory(factory, sender=deployer)
    return factory

def test_deploy(project, deployer, robo, factory):
    token1 = project.MockToken.deploy(sender=deployer)
    token2 = project.MockToken.deploy(sender=deployer)
    token3 = project.MockToken.deploy(sender=deployer)

    assert factory.auctions(token2) == ZERO_ADDRESS
    assert robo.deploy_converter(token1, token2, sender=deployer).return_value == factory
    auction = factory.auctions(token2)
    assert auction != ZERO_ADDRESS

    # deploy for same pair again, should return same auction contract
    robo.deploy_converter(token1, token2, sender=deployer)
    assert factory.auctions(token2) == auction

    # deploy for different from token, should return same auction contract
    robo.deploy_converter(token3, token2, sender=deployer)
    assert factory.auctions(token2) == auction

def test_deploy_permission(project, deployer, robo, factory):
    token1 = project.MockToken.deploy(sender=deployer)
    token2 = project.MockToken.deploy(sender=deployer)
    with reverts():
        factory.deploy(token1, token2, sender=deployer)
    robo.deploy_converter(token1, token2, sender=deployer)

def test_convert(project, chain, deployer, alice, treasury, robo, factory):
    token1 = project.MockToken.deploy(sender=deployer)
    token2 = project.MockToken.deploy(sender=deployer)

    robo.deploy_converter(token1, token2, sender=deployer)
    auction = project.MockAuction.at(factory.auctions(token2))
    token2.mint(alice, 3_000_000 * UNIT, sender=alice)
    token2.approve(auction, 3_000_000 * UNIT, sender=alice)

    token1.mint(factory, UNIT, sender=deployer)
    info = auction.auctions(token1)
    assert info[0] == 0 and info[1] == 0

    with reverts():
        factory.convert(token1, UNIT, token2, sender=deployer)

    robo.set_bucket(deployer, True, sender=deployer)
    ts = chain.pending_timestamp
    factory.convert(token1, UNIT, token2, sender=deployer)
    info = auction.auctions(token1)
    assert info[0] == ts and info[1] == 1
    assert token1.balanceOf(auction) == UNIT
    assert auction.available(token1) == UNIT
    assert auction.getAmountNeeded(token1) == 1_000_000 * UNIT

    auction.take(token1, sender=alice)
    assert token1.balanceOf(auction) == 0
    assert token1.balanceOf(alice) == UNIT
    assert token2.balanceOf(treasury) == 1_000_000 * UNIT
    assert token2.balanceOf(alice) == 2_000_000 * UNIT

def test_sweep(project, deployer, factory):
    token = project.MockToken.deploy(sender=deployer)
    token.mint(factory, 3 * UNIT, sender=deployer)
    
    factory.sweep(token, UNIT, sender=deployer)
    assert token.balanceOf(factory) == 2 * UNIT
    assert token.balanceOf(deployer) == UNIT

    factory.sweep(token, sender=deployer)
    assert token.balanceOf(factory) == 0
    assert token.balanceOf(deployer) == 3 * UNIT

def test_sweep_permission(project, deployer, alice, factory):
    token = project.MockToken.deploy(sender=deployer)
    token.mint(factory, UNIT, sender=deployer)
    with reverts():
        factory.sweep(token, sender=alice)
    factory.sweep(token, sender=deployer)

def test_call(project, deployer, alice, bob, robo, factory):
    token1 = project.MockToken.deploy(sender=deployer)
    token2 = project.MockToken.deploy(sender=deployer)

    robo.deploy_converter(token1, token2, sender=deployer)
    auction = project.MockAuction.at(factory.auctions(token2))

    assert auction.startingPrice() == 1_000_000
    data = auction.setStartingPrice.encode_input(1_000)

    factory.set_operator(alice, sender=deployer)
    with reverts():
        factory.call(token2, data, sender=bob)

    factory.call(token2, data, sender=alice)
    assert auction.startingPrice() == 1_000

def test_set_operator(deployer, alice, factory):
    with reverts():
        factory.set_operator(alice, sender=alice)

    assert factory.operator() == deployer
    factory.set_operator(alice, sender=deployer)
    assert factory.operator() == alice

def test_transfer_management(deployer, alice, bob, factory):
    assert factory.management() == deployer
    assert factory.pending_management() == ZERO_ADDRESS

    with reverts():
        factory.set_management(alice, sender=alice)
    with reverts():
        factory.accept_management(sender=alice)
 
    factory.set_management(alice, sender=deployer)
    assert factory.management() == deployer
    assert factory.pending_management() == alice

    with reverts():
        factory.accept_management(sender=bob)
    
    factory.accept_management(sender=alice)
    assert factory.management() == alice
    assert factory.pending_management() == ZERO_ADDRESS
