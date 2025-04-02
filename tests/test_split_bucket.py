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
def robo(accounts):
    return accounts[5]

@fixture
def tokens(project, deployer):
    return [project.MockToken.deploy(sender=deployer) for _ in range(2)]

@fixture
def auction_factory():
    return Contract(AUCTION_FACTORY)

@fixture
def factory(project, deployer, treasury, robo, auction_factory):
    return project.Factory.deploy(treasury, robo, auction_factory, sender=deployer)

@fixture
def provider(project, deployer):
    return project.MockProvider.deploy(sender=deployer)

@fixture
def buckets(project, deployer):
    return [project.MockBucket.deploy(sender=deployer) for _ in range(2)]

@fixture
def split(project, deployer, robo):
    return project.SplitBucket.deploy(robo, sender=deployer)

def test_add_bucket(deployer, buckets, split):
    assert split.num_buckets() == 0
    with reverts():
        split.buckets(0)
    assert split.total_points() == 0
    assert split.points(buckets[0]) == 0
    assert split.add_bucket(buckets[0], 1, sender=deployer).return_value == 0
    assert split.num_buckets() == 1
    assert split.buckets(0) == buckets[0]
    assert split.total_points() == 1
    assert split.points(buckets[0]) == 1

def test_add_buckets(deployer, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    assert split.add_bucket(buckets[1], 2, sender=deployer).return_value == 1
    assert split.num_buckets() == 2
    assert split.buckets(1) == buckets[1]
    assert split.total_points() == 3
    assert split.points(buckets[1]) == 2

def test_add_bucket_no_points(deployer, buckets, split):
    with reverts():
        split.add_bucket(buckets[0], 0, sender=deployer)
    split.add_bucket(buckets[0], 1, sender=deployer)

def test_add_bucket_excessive_points(deployer, buckets, split):
    with reverts():
        split.add_bucket(buckets[0], 2 * UNIT, sender=deployer)
    split.add_bucket(buckets[0], UNIT, sender=deployer)

def test_add_bucket_existing(deployer, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    with reverts():
        split.add_bucket(buckets[0], 2, sender=deployer)

def test_add_bucket_permission(deployer, alice, buckets, split):
    with reverts(): 
        split.add_bucket(buckets[0], 1, sender=alice)
    split.add_bucket(buckets[0], 1, sender=deployer)

def test_remove_bucket(deployer, buckets, split):
    split.add_bucket(buckets[0], 2, sender=deployer)
    split.add_bucket(buckets[1], 3, sender=deployer)

    split.remove_bucket(buckets[0], 0, sender=deployer)
    assert split.num_buckets() == 1
    assert split.buckets(0) == buckets[1]
    with reverts():
        split.buckets(1)
    assert split.total_points() == 3
    assert split.points(buckets[0]) == 0

def test_remove_bucket_end(deployer, buckets, split):
    split.add_bucket(buckets[0], 2, sender=deployer)
    split.add_bucket(buckets[1], 3, sender=deployer)

    split.remove_bucket(buckets[1], 1, sender=deployer)
    assert split.num_buckets() == 1
    assert split.buckets(0) == buckets[0]
    with reverts():
        split.buckets(1)
    assert split.total_points() == 2
    assert split.points(buckets[1]) == 0

def test_remove_bucket_not_added(deployer, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    with reverts():
        split.remove_bucket(buckets[1], 0, sender=deployer)
    split.remove_bucket(buckets[0], 0, sender=deployer)

def test_remove_bucket_wrong_index(deployer, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    split.add_bucket(buckets[1], 1, sender=deployer)
    with reverts():
        split.remove_bucket(buckets[1], 0, sender=deployer)
    split.remove_bucket(buckets[1], 1, sender=deployer)

def test_remove_bucket_permission(deployer, alice, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    with reverts():
        split.remove_bucket(buckets[0], 0, sender=alice)
    split.remove_bucket(buckets[0], 0, sender=deployer)

def test_set_points(deployer, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    split.add_bucket(buckets[1], 2, sender=deployer)
    assert split.total_points() == 3
    assert split.points(buckets[0]) == 1
    split.set_points(buckets[0], 3, sender=deployer)
    assert split.total_points() == 5
    assert split.points(buckets[0]) == 3
    split.set_points(buckets[0], 2, sender=deployer)
    assert split.total_points() == 4
    assert split.points(buckets[0]) == 2

def test_set_points_not_added(deployer, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    with reverts():
        split.set_points(buckets[1], 2, sender=deployer)
    split.set_points(buckets[0], 2, sender=deployer)

def test_set_points_zero(deployer, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    with reverts():
        split.set_points(buckets[0], 0, sender=deployer)
    split.set_points(buckets[0], 2, sender=deployer)

def test_set_points_excessive(deployer, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    with reverts():
        split.set_points(buckets[0], 2 * UNIT, sender=deployer)
    split.set_points(buckets[0], UNIT, sender=deployer)

def test_set_points_permission(deployer, alice, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    with reverts():
        split.set_points(buckets[0], 2, sender=alice)
    split.set_points(buckets[0], 2, sender=deployer)

def test_sweep(deployer, tokens, split):
    tokens[0].mint(split, 3 * UNIT, sender=deployer)
    
    split.sweep(tokens[0], UNIT, sender=deployer)
    assert tokens[0].balanceOf(split) == 2 * UNIT
    assert tokens[0].balanceOf(deployer) == UNIT

    split.sweep(tokens[0], sender=deployer)
    assert tokens[0].balanceOf(split) == 0
    assert tokens[0].balanceOf(deployer) == 3 * UNIT

def test_sweep_permission(deployer, alice, tokens, split):
    tokens[0].mint(split, UNIT, sender=deployer)
    with reverts():
        split.sweep(tokens[0], sender=alice)
    split.sweep(tokens[0], sender=deployer)

def test_convert(deployer, robo, tokens, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    split.add_bucket(buckets[1], 2, sender=deployer)
    tokens[0].mint(split, 6 * UNIT , sender=deployer)
    
    split.convert(tokens[0], 6 * UNIT, sender=robo)
    assert tokens[0].balanceOf(buckets[0]) == 2 * UNIT
    assert tokens[0].balanceOf(buckets[1]) == 4 * UNIT

def test_convert_permission(deployer, robo, tokens, buckets, split):
    split.add_bucket(buckets[0], 1, sender=deployer)
    split.add_bucket(buckets[1], 1, sender=deployer)
    tokens[0].mint(split, UNIT , sender=deployer)
    
    with reverts():
        split.convert(tokens[0], UNIT, sender=deployer)
    split.convert(tokens[0], UNIT, sender=robo)

def test_transfer_management(deployer, alice, bob, split):
    assert split.management() == deployer
    assert split.pending_management() == ZERO_ADDRESS

    with reverts():
        split.set_management(alice, sender=alice)
    with reverts():
        split.accept_management(sender=alice)
 
    split.set_management(alice, sender=deployer)
    assert split.management() == deployer
    assert split.pending_management() == alice

    with reverts():
        split.accept_management(sender=bob)
    
    split.accept_management(sender=alice)
    assert split.management() == alice
    assert split.pending_management() == ZERO_ADDRESS
