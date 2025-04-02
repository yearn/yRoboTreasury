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
def provider(project, deployer):
    return project.MockProvider.deploy(sender=deployer)

@fixture
def bucket(project, deployer, treasury, robo, factory, provider):
    bucket = project.GenericBucket.deploy(treasury, robo, sender=deployer)
    bucket.set_provider(provider, sender=deployer)
    robo.set_factory(factory, sender=deployer)
    return bucket

def test_add_token(deployer, tokens, provider, bucket):
    assert bucket.num_tokens() == 0
    with reverts():
        bucket.tokens(0)
    assert not bucket.whitelisted(tokens[0])
    assert bucket.total_points() == 0
    assert bucket.points(tokens[0]) == 0
    assert bucket.want() == ZERO_ADDRESS
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    assert bucket.add_token(tokens[0], 1, sender=deployer).return_value == 0
    assert bucket.num_tokens() == 1
    assert bucket.tokens(0) == tokens[0]
    assert bucket.whitelisted(tokens[0])
    assert bucket.total_points() == 1
    assert bucket.points(tokens[0]) == 1
    assert bucket.want() == tokens[0]

def test_add_tokens(deployer, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    provider.set_rate(tokens[1], 2 * UNIT, sender=deployer)
    assert bucket.add_token(tokens[1], 2, sender=deployer).return_value == 1
    assert bucket.num_tokens() == 2
    assert bucket.tokens(1) == tokens[1]
    assert bucket.total_points() == 3
    assert bucket.points(tokens[1]) == 2
    assert bucket.want() == tokens[0]

def test_add_token_no_points(deployer, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    with reverts():
        bucket.add_token(tokens[0], 0, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)

def test_add_token_excessive_points(deployer, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    with reverts():
        bucket.add_token(tokens[0], 2 * UNIT, sender=deployer)
    bucket.add_token(tokens[0], UNIT, sender=deployer)

def test_add_token_no_rate(deployer, tokens, provider, bucket):
    with reverts():
        bucket.add_token(tokens[0], 1, sender=deployer)
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)

def test_add_token_existing(deployer, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    with reverts():
        bucket.add_token(tokens[0], 2, sender=deployer)

def test_add_token_permission(deployer, alice, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    with reverts():
        bucket.add_token(tokens[0], 1, sender=alice)
    bucket.add_token(tokens[0], 1, sender=deployer)

def test_remove_token(deployer, treasury, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    provider.set_rate(tokens[1], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 2, sender=deployer)
    bucket.add_token(tokens[1], 3, sender=deployer)
    tokens[0].mint(treasury, UNIT, sender=deployer)
    tokens[1].mint(treasury, 2 * UNIT, sender=deployer)

    bucket.remove_token(tokens[0], 0, sender=deployer)
    assert bucket.num_tokens() == 1
    assert bucket.tokens(0) == tokens[1]
    with reverts():
        bucket.tokens(1)
    assert not bucket.whitelisted(tokens[0])
    assert bucket.total_points() == 3
    assert bucket.points(tokens[0]) == 0
    assert bucket.want() == tokens[1]
    assert bucket.reserves() == 2 * UNIT

def test_remove_token_end(deployer, treasury, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    provider.set_rate(tokens[1], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 2, sender=deployer)
    bucket.add_token(tokens[1], 3, sender=deployer)
    tokens[0].mint(treasury, UNIT, sender=deployer)
    tokens[1].mint(treasury, 2 * UNIT, sender=deployer)

    bucket.remove_token(tokens[1], 1, sender=deployer)
    assert bucket.num_tokens() == 1
    assert bucket.tokens(0) == tokens[0]
    with reverts():
        bucket.tokens(1)
    assert bucket.total_points() == 2
    assert bucket.points(tokens[1]) == 0
    assert bucket.want() == tokens[0]
    assert bucket.reserves() == UNIT

def test_remove_token_not_added(deployer, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    provider.set_rate(tokens[1], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    with reverts():
        bucket.remove_token(tokens[1], 0, sender=deployer)
    bucket.remove_token(tokens[0], 0, sender=deployer)

def test_remove_token_wrong_index(deployer, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    provider.set_rate(tokens[1], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    bucket.add_token(tokens[1], 1, sender=deployer)
    with reverts():
        bucket.remove_token(tokens[1], 0, sender=deployer)
    bucket.remove_token(tokens[1], 1, sender=deployer)

def test_remove_token_permission(deployer, alice, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    with reverts():
        bucket.remove_token(tokens[0], 0, sender=alice)
    bucket.remove_token(tokens[0], 0, sender=deployer)

def test_set_points(deployer, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    provider.set_rate(tokens[1], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    bucket.add_token(tokens[1], 2, sender=deployer)
    assert bucket.total_points() == 3
    assert bucket.points(tokens[0]) == 1
    bucket.set_points(tokens[0], 3, sender=deployer)
    assert bucket.total_points() == 5
    assert bucket.points(tokens[0]) == 3
    bucket.set_points(tokens[0], 2, sender=deployer)
    assert bucket.total_points() == 4
    assert bucket.points(tokens[0]) == 2

def test_set_points_not_added(deployer, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)

    with reverts():
        bucket.set_points(tokens[1], 2, sender=deployer)
    bucket.set_points(tokens[0], 2, sender=deployer)

def test_set_points_zero(deployer, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)

    with reverts():
        bucket.set_points(tokens[0], 0, sender=deployer)
    bucket.set_points(tokens[0], 2, sender=deployer)

def test_set_points_excessive(deployer, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)

    with reverts():
        bucket.set_points(tokens[0], 2 * UNIT, sender=deployer)
    bucket.set_points(tokens[0], UNIT, sender=deployer)

def test_set_points_permission(deployer, alice, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)

    with reverts():
        bucket.set_points(tokens[0], 2, sender=alice)
    bucket.set_points(tokens[0], 2, sender=deployer)

def test_set_provider(project, deployer, treasury, tokens, provider, bucket):
    tokens[0].mint(treasury, UNIT, sender=deployer)
    tokens[1].mint(treasury, UNIT, sender=deployer)

    provider.set_rate(tokens[0], UNIT, sender=deployer)
    provider.set_rate(tokens[1], 2 * UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    bucket.add_token(tokens[1], 1, sender=deployer)

    provider2 = project.MockProvider.deploy(sender=deployer)
    provider2.set_rate(tokens[0], 3 * UNIT, sender=deployer)
    provider2.set_rate(tokens[1], 2 * UNIT, sender=deployer)

    assert bucket.call_view_method('provider') == provider.address
    assert bucket.reserves() == 3 * UNIT
    bucket.set_provider(provider2, sender=deployer)
    assert bucket.call_view_method('provider') == provider2.address
    assert bucket.reserves() == 5 * UNIT

def test_set_provider_no_rate(project, deployer, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    provider.set_rate(tokens[1], 2 * UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    bucket.add_token(tokens[1], 1, sender=deployer)

    provider2 = project.MockProvider.deploy(sender=deployer)
    provider2.set_rate(tokens[0], 3 * UNIT, sender=deployer)

    with reverts():
        bucket.set_provider(provider2, sender=deployer)

    provider2.set_rate(tokens[1], 2 * UNIT, sender=deployer)
    bucket.set_provider(provider2, sender=deployer)

def test_set_provider_permission(project, deployer, alice, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)

    provider2 = project.MockProvider.deploy(sender=deployer)
    provider2.set_rate(tokens[0], 3 * UNIT, sender=deployer)

    with reverts():
        bucket.set_provider(provider2, sender=alice)
    bucket.set_provider(provider2, sender=deployer)

def test_reserves(deployer, treasury, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)

    assert bucket.reserves() == 0
    tokens[0].mint(treasury, UNIT, sender=deployer)
    assert bucket.reserves() == UNIT
    provider.set_rate(tokens[0], 2 * UNIT, sender=deployer)
    assert bucket.reserves() == 2 * UNIT
    tokens[0].mint(treasury, UNIT, sender=deployer)
    assert bucket.reserves() == 4 * UNIT

def test_reserves_sum(deployer, treasury, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    provider.set_rate(tokens[1], 2 * UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    bucket.add_token(tokens[1], 1, sender=deployer)
    tokens[0].mint(treasury, 2 * UNIT, sender=deployer)
    tokens[1].mint(treasury, 3 * UNIT, sender=deployer)
    assert bucket.reserves() == 8 * UNIT

def test_want(deployer, treasury, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    provider.set_rate(tokens[1], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    bucket.add_token(tokens[1], 2, sender=deployer)
    tokens[0].mint(treasury, UNIT, sender=deployer)
    tokens[1].mint(treasury, UNIT, sender=deployer)

    assert bucket.want() == tokens[1]
    provider.set_rate(tokens[1], 3 * UNIT, sender=deployer)
    assert bucket.want() == tokens[0]
    tokens[0].mint(treasury, UNIT, sender=deployer)
    assert bucket.want() == tokens[1]

def test_set_reserves_floor(deployer, treasury, tokens, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    tokens[0].mint(treasury, UNIT - 1, sender=deployer)

    assert bucket.reserves_floor() == 0
    bucket.set_reserves_floor(UNIT, sender=deployer)
    assert bucket.reserves_floor() == UNIT
    assert not bucket.above_floor(sender=deployer).return_value
    tokens[0].mint(treasury, 1, sender=deployer)
    assert bucket.above_floor(sender=deployer).return_value

def test_set_reserves_floor_permission(deployer, alice, bucket):
    with reverts():
        bucket.set_reserves_floor(UNIT, sender=alice)
    bucket.set_reserves_floor(UNIT, sender=deployer)

def test_set_split_bucket(deployer, alice, bucket):
    assert bucket.split_bucket() == ZERO_ADDRESS
    bucket.set_split_bucket(alice, sender=deployer)
    assert bucket.split_bucket() == alice

def test_set_split_bucket_permission(deployer, alice, bucket):
    with reverts():
        bucket.set_split_bucket(alice, sender=alice)
    bucket.set_split_bucket(alice, sender=deployer)

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

def test_convert(project, deployer, alice, tokens, robo, factory, provider, bucket):
    provider.set_rate(tokens[1], UNIT, sender=deployer)
    bucket.add_token(tokens[1], 1, sender=deployer)
    bucket.set_split_bucket(alice, sender=deployer)
    robo.set_bucket(bucket, True, sender=deployer)
    tokens[0].mint(bucket, UNIT, sender=deployer)

    bucket.convert(tokens[0], UNIT, sender=alice)
    assert tokens[0].balanceOf(bucket) == 0
    
    auction = project.MockAuction.at(factory.auctions(tokens[1]))
    assert auction.address != ZERO_ADDRESS
    assert auction.auctions(tokens[0])[0] > 0
    assert tokens[0].balanceOf(auction) == UNIT
    assert auction.getAmountNeeded(tokens[0]) == 1_000_000 * UNIT

def test_convert_whitelisted(deployer, alice, treasury, tokens, robo, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.add_token(tokens[0], 1, sender=deployer)
    bucket.set_split_bucket(alice, sender=deployer)
    robo.set_bucket(bucket, True, sender=deployer)
    tokens[0].mint(bucket, UNIT, sender=deployer)

    bucket.convert(tokens[0], UNIT, sender=alice)
    assert tokens[0].balanceOf(bucket) == 0
    assert tokens[0].balanceOf(treasury) == UNIT

def test_convert_empty(deployer, alice, treasury, tokens, robo, provider, bucket):
    provider.set_rate(tokens[0], UNIT, sender=deployer)
    bucket.set_split_bucket(alice, sender=deployer)
    robo.set_bucket(bucket, True, sender=deployer)
    tokens[0].mint(bucket, UNIT, sender=deployer)

    with reverts():
        bucket.convert(tokens[0], UNIT, sender=alice)
    bucket.add_token(tokens[0], 1, sender=deployer)
    bucket.convert(tokens[0], UNIT, sender=alice)

def test_convert_permission(deployer, alice, tokens, robo, provider, bucket):
    provider.set_rate(tokens[1], UNIT, sender=deployer)
    bucket.add_token(tokens[1], 1, sender=deployer)
    robo.set_bucket(bucket, True, sender=deployer)
    tokens[0].mint(bucket, UNIT, sender=deployer)

    with reverts():
        bucket.convert(tokens[0], UNIT, sender=alice)
    bucket.set_split_bucket(alice, sender=deployer)
    bucket.convert(tokens[0], UNIT, sender=alice)

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
