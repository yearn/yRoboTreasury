# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun
"""
@title Split bucket
@author Yearn Finance
@license GNU AGPLv3
@notice
    A type of bucket that splits any incoming assets into a set of child buckets. 
    Assets are spread out proportional to the weight of each bucket.
"""

from vyper.interfaces import ERC20

interface Bucket:
    def whitelisted(_token: address) -> bool: view
    def above_floor() -> bool: nonpayable
    def convert(_token: address, _amount: uint256): nonpayable

robo: public(immutable(address))
management: public(address)
pending_management: public(address)
num_buckets: public(uint256)
buckets: public(DynArray[address, MAX_NUM_BUCKETS])
total_points: public(uint256)
points: public(HashMap[address, uint256])

event Convert:
    _from: indexed(address)
    _to: indexed(address)
    _amount: uint256

event Sweep:
    _token: indexed(address)
    _amount: uint256

event Points:
    _bucket: indexed(address)
    _points: uint256

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

MAX_NUM_BUCKETS: constant(uint256) = 32
PRECISION: constant(uint256) = 10**18

implements: Bucket

@external
def __init__(_robo: address):
    """
    @notice Constructor
    @param _robo Robo contract
    """
    robo = _robo
    self.management = msg.sender

@external
@view
def whitelisted(_token: address) -> bool:
    """
    @notice Query whether the address is a whitelisted token
    @param _token Token address
    @return True: address is a whitelisted token, False: address is not a whitelisted token
    """
    return False

@external
@view
def above_floor() -> bool:
    """
    @notice Query whether the bucket reserves are above its floor value
    @return True: reserves are at or above the floor, False: reserves are below the floor
    """
    return False

@external
def convert(_token: address, _amount: uint256):
    """
    @notice Start conversion of a token to whitelisted token(s)
    @param _token Token to convert from
    @param _amount Amount of tokens to convert
    @dev Can only be called by the Robo contract
    @dev Converts amounts evenly over the points allocated to each bucket
    @dev Expects tokens to be transfered into the contract prior to being called
    @dev Conversion can be async
    """
    assert msg.sender == robo
    total_points: uint256 = self.total_points
    assert total_points > 0

    for bucket in self.buckets:
        amount: uint256 = _amount * self.points[bucket] / total_points
        assert ERC20(_token).transfer(bucket, amount, default_return_value=True)
        log Convert(_token, empty(address), amount)
        Bucket(bucket).convert(_token, amount)

@external
def sweep(_token: address, _amount: uint256 = max_value(uint256)):
    """
    @notice Sweep any tokens left over in the contract
    @param _token The token to sweep
    @param _amount The amount to sweep. Defaults to contract balance
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    amount: uint256 = _amount
    if _amount == max_value(uint256):
        amount = ERC20(_token).balanceOf(self)
    assert ERC20(_token).transfer(self.management, amount, default_return_value=True)
    log Sweep(_token, amount)

@external
def add_bucket(_bucket: address, _points: uint256) -> uint256:
    """
    @notice Add a bucket to split between
    @param _bucket The bucket to add
    @param _points The amount of points to allocate
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    assert _bucket != empty(address)
    assert _points > 0 and _points <= PRECISION
    assert self.points[_bucket] == 0
    num_buckets: uint256 = len(self.buckets)
    assert num_buckets < MAX_NUM_BUCKETS

    self.num_buckets = num_buckets + 1
    self.buckets.append(_bucket)
    self.total_points += _points
    self.points[_bucket] = _points
    log Points(_bucket, _points)
    
    return num_buckets

@external
def remove_bucket(_bucket: address, _index: uint256):
    """
    @notice Remove a bucket to split between
    @param _bucket The bucket to remove
    @param _index The index of the bucket in the list
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    assert self.buckets[_index] == _bucket
    points: uint256 = self.points[_bucket]
    assert points > 0

    last_index: uint256 = len(self.buckets) - 1
    self.num_buckets = last_index
    if _index < last_index:
        # swap with last entry
        self.buckets[_index] = self.buckets[last_index]
    self.buckets.pop()

    self.total_points -= points
    self.points[_bucket] = 0
    log Points(_bucket, 0)

@external
def set_points(_bucket: address, _points: uint256):
    """
    @notice Change the points allocation of a bucket
    @param _bucket The bucket
    @param _points The amount of points to allocate
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    assert _points > 0 and _points <= PRECISION
    prev_points: uint256 = self.points[_bucket]
    assert prev_points > 0
    
    self.total_points = self.total_points - prev_points + _points
    self.points[_bucket] = _points
    log Points(_bucket, _points)

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
