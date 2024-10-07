# pragma version 0.3.10

from vyper.interfaces import ERC20

interface Bucket:
    def whitelisted(_token: address) -> bool: view
    def above_floor() -> bool: nonpayable
    def convert(_token: address, _amount: uint256): nonpayable

robo: public(immutable(address))
management: public(address)
pending_management: public(address)
buckets: public(DynArray[address, MAX_NUM_BUCKETS])
total_points: public(uint256)
points: public(HashMap[address, uint256])

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

MAX_NUM_BUCKETS: constant(uint256) = 32
PRECISION: constant(uint256) = 10**18

implements: Bucket

@external
def __init__(_robo: address):
    robo = _robo
    self.management = msg.sender

@external
@view
def whitelisted(_token: address) -> bool:
    return False

@external
@view
def above_floor() -> bool:
    return False

@external
def convert(_token: address, _amount: uint256):
    assert msg.sender == robo
    total_points: uint256 = self.total_points
    assert total_points > 0

    for bucket in self.buckets:
        amount: uint256 = _amount * self.points[bucket] / total_points
        assert ERC20(_token).transfer(bucket, amount, default_return_value=True)
        Bucket(bucket).convert(_token, _amount)

@external
def sweep(_token: address, _amount: uint256 = max_value(uint256)):
    assert msg.sender == self.management
    amount: uint256 = _amount
    if _amount == max_value(uint256):
        amount = ERC20(_token).balanceOf(self)
    assert ERC20(_token).transfer(self.management, amount, default_return_value=True)

@external
def add_bucket(_bucket: address, _points: uint256) -> uint256:
    assert msg.sender == self.management
    assert _bucket != empty(address)
    assert _points > 0 and _points <= PRECISION
    assert self.points[_bucket] == 0
    num_buckets: uint256 = len(self.buckets)
    assert num_buckets < MAX_NUM_BUCKETS

    self.buckets.append(_bucket)
    self.total_points += _points
    self.points[_bucket] = _points
    
    return num_buckets

@external
def remove_bucket(_bucket: address, _index: uint256):
    assert msg.sender == self.management
    assert self.buckets[_index] == _bucket
    points: uint256 = self.points[_bucket]
    assert points > 0

    last_index: uint256 = len(self.buckets) - 1
    if _index < last_index:
        # swap with last entry
        self.buckets[_index] = self.buckets[last_index]
    self.buckets.pop()

    self.total_points -= points
    self.points[_bucket] = 0

@external
def set_points(_bucket: address, _points: uint256):
    assert msg.sender == self.management
    assert _points > 0 and _points <= PRECISION
    prev_points: uint256 = self.points[_bucket]
    assert prev_points > 0
    
    self.total_points = self.total_points - prev_points + _points
    self.points[_bucket] = _points

@external
def set_management(_management: address):
    """
    @notice 
        Set the pending management address.
        Needs to be accepted by that account separately to transfer management over
    @param _management New pending management address
    """
    assert msg.sender == self.management
    self.pending_management = _management
    log PendingManagement(_management)

@external
def accept_management():
    """
    @notice 
        Accept management role.
        Can only be called by account previously marked as pending management by current management
    """
    assert msg.sender == self.pending_management
    self.pending_management = empty(address)
    self.management = msg.sender
    log SetManagement(msg.sender)
