from ape import reverts, Contract
from pytest import fixture

AUCTION_FACTORY = '0xa076c247AfA44f8F006CA7f21A4EF59f7e4dc605'

SENTINEL = '0x1111111111111111111111111111111111111111'
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'
UNIT = 10**18

@fixture
def treasury(accounts):
    return accounts[4]

@fixture
def parent(accounts):
    return accounts[5]

@fixture
def tokens(project, deployer):
    return [project.MockToken.deploy(sender=deployer) for _ in range(2)]

@fixture
def robo(project, deployer):
    return project.MockRobo.deploy(sender=deployer)

@fixture
def auction_factory():
    return Contract(AUCTION_FACTORY)

@fixture
def factory(project, deployer, treasury, robo, auction_factory):
    return project.Factory.deploy(treasury, robo, auction_factory, sender=deployer)

@fixture
def bucket(project, deployer, treasury, parent, tokens, robo, factory):
    bucket = project.BuybackBucket.deploy(treasury, robo, tokens[0], sender=deployer)
    bucket.set_parent(parent, sender=deployer)
    robo.set_bucket(bucket, True, sender=deployer)
    robo.set_factory(factory, sender=deployer)
    return bucket

def test_sweep(deployer, tokens, bucket):
    tokens[0].mint(bucket, 3 * UNIT, sender=deployer)
    
    bucket.sweep(tokens[0], UNIT, sender=deployer)
    assert tokens[0].balanceOf(bucket) == 2 * UNIT
    assert tokens[0].balanceOf(deployer) == UNIT

    bucket.sweep(tokens[0], sender=deployer)
    assert tokens[0].balanceOf(bucket) == 0
    assert tokens[0].balanceOf(deployer) == 3 * UNIT

def test_sweep_permission(deployer, alice, tokens, bucket):
    tokens[0].mint(bucket, UNIT, sender=deployer)
    with reverts():
        bucket.sweep(tokens[0], sender=alice)
    bucket.sweep(tokens[0], sender=deployer)

def test_set_parent(deployer, alice, parent, bucket):
    assert bucket.parent() == parent
    bucket.set_parent(alice, sender=deployer)
    assert bucket.parent() == alice

def test_set_parent_permission(deployer, alice, bucket):
    with reverts():
        bucket.set_parent(alice, sender=alice)
    bucket.set_parent(alice, sender=deployer)

def test_convert(project, deployer, parent, tokens, factory, bucket):
    tokens[1].mint(bucket, UNIT, sender=deployer)
    bucket.convert(tokens[1], UNIT, sender=parent)
    assert tokens[1].balanceOf(bucket) == 0
    auction = project.MockAuction.at(factory.auctions(tokens[0]))
    assert auction.address != ZERO_ADDRESS
    assert auction.auctions(tokens[1])[0] > 0
    assert tokens[1].balanceOf(auction) == UNIT
    assert auction.getAmountNeeded(tokens[1]) == 1_000_000 * UNIT
    
def test_convert_self(deployer, treasury, parent, tokens, bucket):
    tokens[0].mint(bucket, UNIT, sender=deployer)
    bucket.convert(tokens[0], UNIT, sender=parent)
    assert tokens[0].balanceOf(bucket) == 0
    assert tokens[0].balanceOf(treasury) == UNIT

def test_convert_permission(deployer, alice, parent, tokens, bucket):
    tokens[1].mint(bucket, UNIT, sender=deployer)
    with reverts():
        bucket.convert(tokens[1], UNIT, sender=alice)
    bucket.convert(tokens[1], UNIT, sender=parent)

def test_transfer_management(deployer, alice, bob, bucket):
    assert bucket.management() == deployer
    assert bucket.pending_management() == ZERO_ADDRESS

    with reverts():
        bucket.set_management(alice, sender=alice)
    with reverts():
        bucket.accept_management(sender=alice)
 
    bucket.set_management(alice, sender=deployer)
    assert bucket.management() == deployer
    assert bucket.pending_management() == alice

    with reverts():
        bucket.accept_management(sender=bob)
    
    bucket.accept_management(sender=alice)
    assert bucket.management() == alice
    assert bucket.pending_management() == ZERO_ADDRESS
