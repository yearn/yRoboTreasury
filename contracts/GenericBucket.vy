# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun

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

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

MAX_NUM_TOKENS: constant(uint256) = 32
PRECISION: constant(uint256) = 10**18

implements: Bucket

@external
def __init__(_treasury: address, _robo: address):
    treasury = _treasury
    robo = Robo(_robo)
    self.management = msg.sender

@external
@view
def whitelisted(_token: address) -> bool:
    return self.points[_token] > 0

@external
def above_floor() -> bool:
    return self._cache()[0] >= self.reserves_floor

@external
def convert(_token: address, _amount: uint256):
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

    converter: address = robo.deploy_converter(_token, want)
    assert ERC20(_token).transfer(converter, _amount, default_return_value=True)
    Converter(converter).convert(_token, _amount, want)

@external
@view
def reserves() -> uint256:
    return self._reserves()[0]

@external
@view
def want() -> address:
    return self._reserves()[1]

@internal
@view
def _reserves() -> (uint256, address):
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
    assert msg.sender == self.management
    amount: uint256 = _amount
    if _amount == max_value(uint256):
        amount = ERC20(_token).balanceOf(self)
    assert ERC20(_token).transfer(self.management, amount, default_return_value=True)

@external
def add_token(_token: address, _points: uint256) -> uint256:
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
    
    return num_tokens

@external
def remove_token(_token: address, _index: uint256):
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

@external
def set_points(_token: address, _points: uint256):
    assert msg.sender == self.management
    assert _points > 0 and _points <= PRECISION
    prev_points: uint256 = self.points[_token]
    assert prev_points > 0
    
    self.total_points = self.total_points - prev_points + _points
    self.points[_token] = _points

@external
def set_split_bucket(_split: address):
    assert msg.sender == self.management
    self.split_bucket = _split

@external
def set_provider(_provider: address):
    assert msg.sender == self.management
    assert _provider != empty(address)

    provider: Provider = Provider(_provider)
    for token in self.tokens:
        assert provider.rate(token) > 0

    self.provider = provider

@external
def set_reserves_floor(_floor: uint256):
    assert msg.sender == self.management
    self.reserves_floor = _floor

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
