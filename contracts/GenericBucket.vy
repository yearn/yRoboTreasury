# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun
"""
@title Generic bucket
@author Yearn Finance
@license GNU AGPLv3
@notice
    A bucket defines a set of whitelisted assets of the same underlying denomination, 
    e.g. ETH and staked derivatives, or different kinds of (staked) stablecoins.
    Each asset in the bucket has it's own weight, representing the target allocation
    of that particular asset inside the bucket. 
    Buckets are able to receive any kind of asset and convert them to a whitelisted asset,
    using the converter in the Robo contract. The bucket will prioritize conversion to 
    the asset that is the most underrepresented relative to its weight.

    Importantly, buckets don't hold assets long-term. Any assets in its contracts are
    only intended to pass-through, potentially being converted before ultimately ending
    up in the treasury contract.
"""

from vyper.interfaces import ERC20

interface Robo:
    def deploy_converter(_from: address, _to: address) -> address: nonpayable

interface Converter:
    def convert(_from: address, _amount: uint256, _to: address): nonpayable

interface Bucket:
    def whitelisted(_token: address) -> bool: view
    def above_floor() -> bool: nonpayable
    def convert(_token: address, _amount: uint256): nonpayable

interface Provider:
    def rate(_token: address) -> uint256: view

treasury: public(immutable(address))
robo: public(immutable(Robo))
management: public(address)
pending_management: public(address)
num_tokens: public(uint256)
tokens: public(DynArray[address, MAX_NUM_TOKENS])
total_points: public(uint256)
points: public(HashMap[address, uint256])
split_bucket: public(address)
provider: public(Provider)
reserves_floor: public(uint256)

cached_reserves: transient(uint256)
cached_want: transient(address)

event Convert:
    _from: indexed(address)
    _to: indexed(address)
    _amount: uint256

event Sweep:
    _token: indexed(address)
    _amount: uint256

event Points:
    _token: indexed(address)
    _points: uint256

event SetSplitBucket:
    _split: address

event SetProvider:
    _provider: address

event SetReservesFloor:
    _floor: uint256

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

MAX_NUM_TOKENS: constant(uint256) = 32
PRECISION: constant(uint256) = 10**18

implements: Bucket

@external
def __init__(_treasury: address, _robo: address):
    """
    @notice Constructor
    @param _treasury Treasury contract, ultimate destination of all assets
    @param _robo Robo contract
    """
    treasury = _treasury
    robo = Robo(_robo)
    self.management = msg.sender

@external
@view
def whitelisted(_token: address) -> bool:
    """
    @notice Query whether the address is a whitelisted token
    @param _token Token address
    @return True: address is a whitelisted token, False: address is not a whitelisted token
    """
    return self.points[_token] > 0

@external
def above_floor() -> bool:
    """
    @notice Query whether the bucket reserves are above its floor value
    @return True: reserves are at or above the floor, False: reserves are below the floor
    """
    return self._cache()[0] >= self.reserves_floor

@external
def convert(_token: address, _amount: uint256):
    """
    @notice Start conversion of a token to whitelisted token(s)
    @param _token Token to convert from
    @param _amount Amount of tokens to convert
    @dev Can only be called by the Robo contract or by the split bucket, if any is set
    @dev Expects tokens to be transfered into the contract prior to being called
    @dev Conversion can be async
    """
    assert msg.sender == robo.address or msg.sender == self.split_bucket
    want: address = self._cache()[1]
    assert want != empty(address)

    # invalidate cache
    self.cached_reserves = 0
    self.cached_want = empty(address)

    # whitelisted tokens are transfered into the treasury as is
    if self.points[_token] > 0:
        assert ERC20(_token).transfer(treasury, _amount, default_return_value=True)
        return

    log Convert(_token, want, _amount)
    converter: address = robo.deploy_converter(_token, want)
    assert ERC20(_token).transfer(converter, _amount, default_return_value=True)
    Converter(converter).convert(_token, _amount, want)

@external
@view
def reserves() -> uint256:
    """
    @notice Query the reserves
    @return Reserves
    """
    return self._reserves()[0]

@external
@view
def want() -> address:
    """
    @notice Query the want token
    @return Want token
    """
    return self._reserves()[1]

@internal
@view
def _reserves() -> (uint256, address):
    """
    @notice
        Calculate the current reserves and want token, which is based on the most 
        underrepresented token relative to its points allocation
    """
    provider: Provider = self.provider
    reserves: uint256 = 0
    want: address = empty(address)
    lowest: uint256 = max_value(uint256)

    for token in self.tokens:
        amount: uint256 = ERC20(token).balanceOf(treasury) * provider.rate(token) / PRECISION 
        reserves += amount

        # find most underrepresented token
        amount = amount * PRECISION / self.points[token]
        if amount < lowest:
            want = token
            lowest = amount
    
    return (reserves, want)

@internal
def _cache() -> (uint256, address):
    """
    @notice
        Query the current reserves and want token. If a previous call in the same
        transaction cached these values, load from cache. Otherwise, calculate
        the values and store them in the cache before returning them
    """
    reserves: uint256 = self.cached_reserves
    if reserves > 0:
        return (reserves, self.cached_want)

    want: address = empty(address)
    reserves, want = self._reserves()

    self.cached_reserves = reserves
    self.cached_want = want

    return (reserves, want)

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
def add_token(_token: address, _points: uint256) -> uint256:
    """
    @notice Add a token to the bucket
    @param _token The token to add
    @param _points The amount of points to allocate
    @return The amount of tokens in the bucket, after adding the token
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    assert _token != empty(address)
    assert _points > 0 and _points <= PRECISION
    assert self.points[_token] == 0
    num_tokens: uint256 = len(self.tokens)
    assert num_tokens < MAX_NUM_TOKENS
    assert self.provider.rate(_token) > 0

    self.num_tokens = num_tokens + 1
    self.tokens.append(_token)
    self.total_points += _points
    self.points[_token] = _points
    log Points(_token, _points)

    return num_tokens

@external
def remove_token(_token: address, _index: uint256):
    """
    @notice Remove a token from the bucket
    @param _token The token to remove
    @param _index The index of the token in the list
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    assert self.tokens[_index] == _token
    points: uint256 = self.points[_token]
    assert points > 0

    last_index: uint256 = len(self.tokens) - 1
    self.num_tokens = last_index
    if _index < last_index:
        # swap with last entry
        self.tokens[_index] = self.tokens[last_index]
    self.tokens.pop()

    self.total_points -= points
    self.points[_token] = 0
    log Points(_token, 0)

@external
def set_points(_token: address, _points: uint256):
    """
    @notice Change the points allocation of a token
    @param _token The token
    @param _points The amount of points to allocate
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    assert _points > 0 and _points <= PRECISION
    prev_points: uint256 = self.points[_token]
    assert prev_points > 0
    
    self.total_points = self.total_points - prev_points + _points
    self.points[_token] = _points
    log Points(_token, _points)

@external
def set_split_bucket(_split: address):
    """
    @notice Set a split bucket
    @param _split Address of the bucket. Set to zero for no split bucket
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    self.split_bucket = _split
    log SetSplitBucket(_split)

@external
def set_provider(_provider: address):
    """
    @notice Set the rate provider for this bucket
    @param _provider The new rate provider
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    assert _provider != empty(address)

    provider: Provider = Provider(_provider)
    for token in self.tokens:
        assert provider.rate(token) > 0

    self.provider = provider
    log SetProvider(_provider)

@external
def set_reserves_floor(_floor: uint256):
    """
    @notice Set the new reserves floor
    @param _floor New floor value
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    self.reserves_floor = _floor
    log SetReservesFloor(_floor)

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
