from ape import reverts, Contract
from pytest import fixture

SENTINEL = '0x1111111111111111111111111111111111111111'
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'
UNIT = 10**18

AUCTION_FACTORY = '0xCfA510188884F199fcC6e750764FAAbE6e56ec40'
WETH = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
DAI = '0x6B175474E89094C44Da98b954EedeAC495271d0F'

@fixture
def treasury(project, deployer):
    return project.Treasury.deploy(ZERO_ADDRESS, sender=deployer)

@fixture
def robo(project, deployer, ingress, treasury):
    return project.Robo.deploy(treasury, ingress, sender=deployer)

@fixture
def factory(project, deployer, treasury, robo):
    return project.Factory.deploy(treasury, robo, AUCTION_FACTORY, sender=deployer)

@fixture
def buckets(project, deployer, ychad, ingress, treasury, robo, factory, weth, dai):
    ingress.setOnesplit(robo, sender=ychad)
    ingress.setAuthorized(robo, sender=ychad)

    robo.set_factory(factory, sender=deployer)
    robo.set_factory_version_enabled(1, True, sender=deployer)

    provider = project.MockProvider.deploy(sender=deployer)
    provider.set_rate(dai, UNIT, sender=deployer)
    provider.set_rate(weth, UNIT, sender=deployer)

    # stables bucket
    bucket1 = project.GenericBucket.deploy(treasury, robo, sender=deployer)
    bucket1.set_provider(provider, sender=deployer)
    bucket1.set_reserves_floor(UNIT, sender=deployer)
    bucket1.add_token(dai, 1, sender=deployer)
    robo.add_bucket(bucket1, SENTINEL, sender=deployer)

    # eth bucket
    bucket2 = project.GenericBucket.deploy(treasury, robo, sender=deployer)
    bucket2.set_provider(provider, sender=deployer)
    bucket2.set_reserves_floor(UNIT, sender=deployer)
    bucket2.add_token(weth, 1, sender=deployer)
    robo.add_bucket(bucket2, bucket1, sender=deployer)

    return [bucket1, bucket2]

@fixture
def whitelist(project, deployer, alice, robo):
    return project.Whitelist.deploy(robo, deployer, alice, sender=deployer)

@fixture
def guard(project, deployer, alice, robo, whitelist):
    return project.Guard.deploy(robo, whitelist, alice, sender=deployer)

@fixture
def weth():
    return Contract(WETH)

@fixture
def dai():
    return Contract(DAI)

def test_add_bucket(project, deployer, robo):
    bucket = project.MockBucket.deploy(sender=deployer)

    assert robo.num_buckets() == 0
    assert robo.linked_buckets(SENTINEL) == SENTINEL
    assert robo.linked_buckets(bucket) == ZERO_ADDRESS
    assert robo.buckets() == []
    assert not robo.is_bucket(SENTINEL)

    robo.add_bucket(bucket, SENTINEL, sender=deployer)
    assert robo.num_buckets() == 1
    assert robo.linked_buckets(SENTINEL) == bucket
    assert robo.linked_buckets(bucket) == SENTINEL
    assert robo.buckets() == [bucket]
    assert robo.is_bucket(bucket)

def test_add_bucket_middle(project, deployer, robo):
    bucket1 = project.MockBucket.deploy(sender=deployer)
    bucket2 = project.MockBucket.deploy(sender=deployer)
    robo.add_bucket(bucket1, SENTINEL, sender=deployer)
    robo.add_bucket(bucket2, SENTINEL, sender=deployer)
    assert robo.num_buckets() == 2
    assert robo.linked_buckets(SENTINEL) == bucket2
    assert robo.linked_buckets(bucket2) == bucket1
    assert robo.linked_buckets(bucket1) == SENTINEL
    assert robo.buckets() == [bucket2, bucket1]
    assert robo.is_bucket(bucket1)
    assert robo.is_bucket(bucket2)

def test_add_bucket_end(project, deployer, robo):
    bucket1 = project.MockBucket.deploy(sender=deployer)
    bucket2 = project.MockBucket.deploy(sender=deployer)
    robo.add_bucket(bucket1, SENTINEL, sender=deployer)
    robo.add_bucket(bucket2, bucket1, sender=deployer)
    assert robo.num_buckets() == 2
    assert robo.linked_buckets(SENTINEL) == bucket1
    assert robo.linked_buckets(bucket1) == bucket2
    assert robo.linked_buckets(bucket2) == SENTINEL
    assert robo.buckets() == [bucket1, bucket2]

def test_add_bucket_wrong(project, deployer, robo):
    bucket1 = project.MockBucket.deploy(sender=deployer)
    bucket2 = project.MockBucket.deploy(sender=deployer)
    with reverts():
        robo.add_bucket(bucket2, bucket1, sender=deployer)

def test_add_bucket_sentinel(deployer, robo):
    with reverts():
        robo.add_bucket(SENTINEL, SENTINEL, sender=deployer)

def test_add_bucket_existing(project, deployer, robo):
    bucket = project.MockBucket.deploy(sender=deployer)
    robo.add_bucket(bucket, SENTINEL, sender=deployer)
    with reverts():
        robo.add_bucket(bucket, SENTINEL, sender=deployer)

def test_add_bucket_permission(project, deployer, alice, robo):
    bucket = project.MockBucket.deploy(sender=deployer)

    with reverts():
        robo.add_bucket(bucket, SENTINEL, sender=alice)
    robo.add_bucket(bucket, SENTINEL, sender=deployer)

def test_remove_bucket(project, deployer, robo):
    bucket = project.MockBucket.deploy(sender=deployer)

    robo.add_bucket(bucket, SENTINEL, sender=deployer)
    robo.remove_bucket(bucket, SENTINEL, sender=deployer)
    assert robo.num_buckets() == 0
    assert robo.linked_buckets(SENTINEL) == SENTINEL
    assert robo.linked_buckets(bucket) == ZERO_ADDRESS
    assert robo.buckets() == []
    assert not robo.is_bucket(bucket)

def test_remove_bucket_middle(project, deployer, robo):
    bucket1 = project.MockBucket.deploy(sender=deployer)
    bucket2 = project.MockBucket.deploy(sender=deployer)

    robo.add_bucket(bucket1, SENTINEL, sender=deployer)
    robo.add_bucket(bucket2, bucket1, sender=deployer)
    robo.remove_bucket(bucket1, SENTINEL, sender=deployer)
    assert robo.num_buckets() == 1
    assert robo.linked_buckets(SENTINEL) == bucket2
    assert robo.linked_buckets(bucket1) == ZERO_ADDRESS
    assert robo.linked_buckets(bucket2) == SENTINEL
    assert robo.buckets() == [bucket2]
    assert not robo.is_bucket(bucket1)
    assert robo.is_bucket(bucket2)

def test_remove_bucket_wrong(project, deployer, robo):
    bucket1 = project.MockBucket.deploy(sender=deployer)
    bucket2 = project.MockBucket.deploy(sender=deployer)

    robo.add_bucket(bucket1, SENTINEL, sender=deployer)
    robo.add_bucket(bucket2, bucket1, sender=deployer)
    with reverts():
        robo.remove_bucket(bucket2, SENTINEL, sender=deployer)

def test_remove_bucket_sentinel(project, deployer, robo):
    bucket = project.MockBucket.deploy(sender=deployer)

    with reverts():
        robo.remove_bucket(SENTINEL, SENTINEL, sender=deployer)

    robo.add_bucket(bucket, SENTINEL, sender=deployer)
    with reverts():
        robo.remove_bucket(SENTINEL, bucket, sender=deployer)

def test_remove_bucket_non_existing(project, deployer, robo):
    bucket1 = project.MockBucket.deploy(sender=deployer)
    bucket2 = project.MockBucket.deploy(sender=deployer)

    robo.add_bucket(bucket1, SENTINEL, sender=deployer)
    with reverts():
        robo.remove_bucket(bucket2, SENTINEL, sender=deployer)

def test_remove_bucket_permission(project, deployer, alice, robo):
    bucket = project.MockBucket.deploy(sender=deployer)

    robo.add_bucket(bucket, SENTINEL, sender=deployer)
    with reverts():
        robo.remove_bucket(bucket, SENTINEL, sender=alice)
    robo.remove_bucket(bucket, SENTINEL, sender=deployer)

def test_replace_bucket(project, deployer, robo):
    bucket1 = project.MockBucket.deploy(sender=deployer)
    bucket2 = project.MockBucket.deploy(sender=deployer)

    robo.add_bucket(bucket1, SENTINEL, sender=deployer)
    robo.replace_bucket(bucket1, bucket2, SENTINEL, sender=deployer)
    assert robo.num_buckets() == 1
    assert robo.linked_buckets(SENTINEL) == bucket2
    assert robo.linked_buckets(bucket1) == ZERO_ADDRESS
    assert robo.linked_buckets(bucket2) == SENTINEL
    assert not robo.is_bucket(bucket1)
    assert robo.is_bucket(bucket2)

def test_replace_bucket_wrong(project, deployer, robo):
    bucket1 = project.MockBucket.deploy(sender=deployer)
    bucket2 = project.MockBucket.deploy(sender=deployer)

    robo.add_bucket(bucket1, SENTINEL, sender=deployer)
    with reverts():
        robo.replace_bucket(bucket1, bucket2, bucket1, sender=deployer)

def test_replace_bucket_sentinel(project, deployer, robo):
    bucket1 = project.MockBucket.deploy(sender=deployer)
    bucket2 = project.MockBucket.deploy(sender=deployer)

    with reverts():
        robo.replace_bucket(SENTINEL, bucket1, SENTINEL, sender=deployer)

    robo.add_bucket(bucket1, SENTINEL, sender=deployer)
    with reverts():
        robo.replace_bucket(SENTINEL, bucket2, bucket1, sender=deployer)

def test_replace_bucket_existing(project, deployer, robo):
    bucket1 = project.MockBucket.deploy(sender=deployer)
    bucket2 = project.MockBucket.deploy(sender=deployer)

    robo.add_bucket(bucket1, SENTINEL, sender=deployer)
    robo.add_bucket(bucket2, bucket1, sender=deployer)

    with reverts():
        robo.replace_bucket(bucket2, bucket1, bucket1, sender=deployer)

def test_replace_bucket_permission(project, deployer, alice, robo):
    bucket1 = project.MockBucket.deploy(sender=deployer)
    bucket2 = project.MockBucket.deploy(sender=deployer)

    robo.add_bucket(bucket1, SENTINEL, sender=deployer)
    with reverts():
        robo.replace_bucket(bucket1, bucket2, SENTINEL, sender=alice)
    robo.replace_bucket(bucket1, bucket2, SENTINEL, sender=deployer)

def test_pull(project, deployer, alice, bob, treasury, robo, factory, buckets, weth, dai):
    dai_amt = 10 * UNIT
    robo.set_operator(alice, sender=deployer)
    with reverts():
        robo.pull(dai, dai_amt, sender=bob)

    # first pull, should fill up first bucket without triggering any conversions
    assert dai.balanceOf(treasury) == 0
    assert not buckets[0].above_floor(sender=deployer).return_value
    robo.pull(dai, dai_amt, sender=alice)

    assert dai.balanceOf(treasury) == dai_amt
    assert buckets[0].above_floor(sender=deployer).return_value

    # sercond pull, should trigger a conversion on the second bucket
    assert robo.converter(dai, weth) == ZERO_ADDRESS
    assert factory.auctions(weth) == ZERO_ADDRESS

    robo.pull(dai, dai_amt, sender=alice)
    assert robo.converter(dai, weth) == factory
    auction = project.MockAuction.at(factory.auctions(weth))
    assert dai.balanceOf(auction) == dai_amt
    assert auction.want() == weth
    assert auction.isActive(dai)
    assert auction.available(dai) == dai_amt
    assert auction.receiver() == treasury

def test_pull_whitelist(deployer, alice, bob, treasury, robo, buckets, whitelist, dai):
    robo.set_operator(whitelist, sender=deployer)
    
    with reverts():
        whitelist.pull(dai, UNIT, sender=alice)

    whitelist.set_whitelist(dai, sender=deployer)

    with reverts():
        whitelist.pull(dai, UNIT, sender=bob)

    whitelist.pull(dai, UNIT, sender=alice)
    assert dai.balanceOf(treasury) == UNIT

def test_pull_guard(deployer, alice, bob, treasury, robo, buckets, whitelist, guard, dai):
    robo.set_operator(guard, sender=deployer)
    
    with reverts():
        guard.pull(dai, UNIT, sender=alice)

    whitelist.set_whitelist(dai, sender=deployer)

    with reverts():
        guard.pull(dai, UNIT, sender=bob)

    guard.pull(dai, UNIT, sender=alice)
    assert dai.balanceOf(treasury) == UNIT

def test_sweep(project, deployer, alice, robo):
    token = project.MockToken.deploy(sender=deployer)
    token.mint(robo, UNIT, sender=deployer)

    with reverts():
        robo.sweep(token, sender=alice)

    assert token.balanceOf(deployer) == 0
    robo.sweep(token, sender=deployer)
    assert token.balanceOf(deployer) == UNIT

def test_set_converter(deployer, alice, robo, weth, dai):
    with reverts():
        robo.set_converter(weth, dai, SENTINEL, sender=alice)

    assert robo.converter(weth, dai) == ZERO_ADDRESS
    robo.set_converter(weth, dai, SENTINEL, sender=deployer)
    assert robo.converter(weth, dai) == SENTINEL

    # manually set converter does not get overwritten
    assert robo.deploy_converter(weth, dai, sender=deployer).return_value == SENTINEL

def test_deploy_converter(deployer, alice, robo, factory, weth, dai):
    robo.set_factory(factory, sender=deployer)
    robo.set_factory_version_enabled(1, True, sender=deployer)

    with reverts():
        robo.deploy_converter(weth, dai, sender=alice)

    robo.add_bucket(alice, SENTINEL, sender=deployer)
    assert robo.converter(weth, dai) == ZERO_ADDRESS
    converter = robo.deploy_converter(weth, dai, sender=alice).return_value
    assert converter != ZERO_ADDRESS
    assert robo.converter(weth, dai) == converter

def test_set_factory(deployer, alice, robo, factory):
    with reverts():
        robo.set_factory(factory, sender=alice)

    assert robo.factory() == (0, ZERO_ADDRESS, False)
    robo.set_factory(factory, sender=deployer)
    assert robo.factory() == (1, factory, False)

def test_unset_factory(deployer, robo, factory):
    robo.set_factory(factory, sender=deployer)
    robo.set_factory_version_enabled(1, True, sender=deployer)
    assert robo.factory() == (1, factory, True)
    robo.set_factory(ZERO_ADDRESS, sender=deployer)
    assert robo.factory() == (1, ZERO_ADDRESS, False)

def test_enable_factory(deployer, alice, robo, factory, weth, dai):
    robo.set_factory(factory, sender=deployer)

    with reverts():
        robo.deploy_converter(weth, dai, sender=deployer)

    with reverts():
        robo.set_factory_version_enabled(1, True, sender=alice)

    assert not robo.factory_version_enabled(1)
    robo.set_factory_version_enabled(1, True, sender=deployer)
    assert robo.factory_version_enabled(1)
    assert robo.factory() == (1, factory, True)

    converter = robo.deploy_converter(weth, dai, sender=deployer).return_value
    assert converter != ZERO_ADDRESS
    assert robo.converter(weth, dai) == converter

def test_disable_factory(project, deployer, treasury, robo, factory, weth, dai):
    robo.set_factory(factory, sender=deployer)
    robo.set_factory_version_enabled(1, True, sender=deployer)
    converter = robo.deploy_converter(weth, dai, sender=deployer).return_value

    # disable
    robo.set_factory_version_enabled(1, False, sender=deployer)
    assert robo.converter(weth, dai) == ZERO_ADDRESS
    assert robo.factory() == (1, factory, False)

    with reverts():
        robo.deploy_converter(weth, dai, sender=deployer)

    # re-enabling restores the converter
    robo.set_factory_version_enabled(1, True, sender=deployer)
    assert robo.converter(weth, dai) == converter
    assert robo.factory() == (1, factory, True)

    # deployments from disabled factories get overwritten
    factory2 = project.Factory.deploy(treasury, robo, AUCTION_FACTORY, sender=deployer)
    robo.set_factory(factory2, sender=deployer)
    assert robo.factory_version_enabled(1)
    robo.set_factory_version_enabled(1, False, sender=deployer)
    assert not robo.factory_version_enabled(1)
    robo.set_factory_version_enabled(2, True, sender=deployer)

    converter2 = robo.deploy_converter(weth, dai, sender=deployer).return_value
    assert converter2 not in [converter, ZERO_ADDRESS]
    assert robo.converter(weth, dai) == converter2

def test_set_operator(deployer, alice, robo, buckets, dai):
    with reverts():
        robo.set_operator(alice, sender=alice)

    with reverts():
        robo.pull(dai, UNIT, sender=alice)

    assert robo.operator() == deployer
    robo.set_operator(alice, sender=deployer)
    assert robo.operator() == alice

    robo.pull(dai, UNIT, sender=alice)

def test_set_ingress(deployer, alice, ingress, robo, buckets, dai):
    with reverts():
        robo.set_ingress(alice, sender=alice)

    assert robo.ingress() == ingress
    robo.set_ingress(alice, sender=deployer)
    assert robo.ingress() == alice

    with reverts():
        robo.pull(dai, UNIT, sender=deployer)

    robo.set_ingress(ingress, sender=deployer)
    robo.pull(dai, UNIT, sender=deployer)

def test_transfer_management(deployer, alice, bob, robo):
    assert robo.management() == deployer
    assert robo.pending_management() == ZERO_ADDRESS

    with reverts():
        robo.set_management(alice, sender=alice)
    with reverts():
        robo.accept_management(sender=alice)
 
    robo.set_management(alice, sender=deployer)
    assert robo.management() == deployer
    assert robo.pending_management() == alice

    with reverts():
        robo.accept_management(sender=bob)
    
    robo.accept_management(sender=alice)
    assert robo.management() == alice
    assert robo.pending_management() == ZERO_ADDRESS
