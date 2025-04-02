from ape import reverts
from pytest import fixture

SENTINEL = '0x1111111111111111111111111111111111111111'
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'
UNIT = 10**18

@fixture
def treasury(project, deployer):
    return project.Treasury.deploy(sender=deployer)

@fixture
def robo(project, deployer, ingress, treasury):
    return project.Robo.deploy(treasury, ingress, sender=deployer)

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
