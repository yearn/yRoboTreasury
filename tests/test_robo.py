from ape import reverts, Contract
from pytest import fixture

SENTINEL = '0x1111111111111111111111111111111111111111'
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'
UNIT = 10**18

AUCTION_FACTORY = '0xa076c247AfA44f8F006CA7f21A4EF59f7e4dc605'
WETH = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
DAI = '0x6B175474E89094C44Da98b954EedeAC495271d0F'

@fixture
def treasury(project, deployer):
    return project.Treasury.deploy(sender=deployer)

@fixture
def robo(project, deployer, ingress, treasury):
    return project.Robo.deploy(treasury, ingress, sender=deployer)

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

def test_pull(project, deployer, ychad, ingress, treasury, robo, weth, dai):
    ingress.setOnesplit(robo, sender=ychad)
    ingress.setAuthorized(robo, sender=ychad)

    factory = project.Factory.deploy(treasury, robo, AUCTION_FACTORY, sender=deployer)
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

    # first pull, should fill up first bucket without triggering any conversions
    assert dai.balanceOf(treasury) == 0
    assert not bucket1.above_floor(sender=deployer).return_value

    dai_amt = 10 * UNIT
    robo.pull(dai, dai_amt, sender=deployer)

    assert dai.balanceOf(treasury) == dai_amt
    assert bucket1.above_floor(sender=deployer).return_value

    # sercond pull, should trigger a conversion on the second bucket
    assert robo.converter(dai, weth) == ZERO_ADDRESS
    assert factory.auctions(weth) == ZERO_ADDRESS

    robo.pull(dai, dai_amt, sender=deployer)
    assert robo.converter(dai, weth) == factory
    auction = project.MockAuction.at(factory.auctions(weth))
    assert dai.balanceOf(auction) == dai_amt
    assert auction.want() == weth
    assert auction.isActive(dai)
    assert auction.available(dai) == dai_amt
    assert auction.receiver() == treasury
