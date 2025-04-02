# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun
"""
@title RoboTreasury
@author Yearn Finance
@license GNU AGPLv3
@notice
    The main entrypoint for the RoboTreasury system. This contract's responsibility 
    is to pull funds from the ingress and deposit them into buckets. The buckets are 
    sorted by priority, and are filled in order until their floor is reached.
    Since buckets are allowed to convert the incoming assets to their liking,
    this contract maintains a list of canocnical conversion contracts. These are
    deployed by a factory but can be overwritten by management to allow for more 
    efficient implementations for specific pairs.
"""

from vyper.interfaces import ERC20

interface Ingress:
    def convert(_token: address, _dummy: uint256): nonpayable

interface Bucket:
    def whitelisted(_token: address) -> bool: view
    def above_floor() -> bool: nonpayable
    def convert(_token: address, _amount: uint256): nonpayable

interface Factory:
    def deploy(_from: address, _to: address) -> address: nonpayable

interface Robo:
    def is_bucket(_bucket: address) -> bool: view
    def deploy_converter(_from: address, _to: address) -> address: nonpayable

interface OneSplit:
    def getExpectedReturn(
        _a: address, _b: address, _c: uint256, _d: uint256, _e: uint256
    ) -> (uint256, uint256[1]): view
    def swap(
        _a: address, _b: address, _c: uint256, _d: uint256, _e: uint256[1], _f: uint256
    ): nonpayable

treasury: public(immutable(address))
management: public(address)
pending_management: public(address)
operator: public(address)
ingress: public(Ingress)
num_buckets: public(uint256)
linked_buckets: public(HashMap[address, address])
packed_factory: public(uint256) # version | factory
packed_factory_versions: public(HashMap[uint256, uint256])
packed_converters: public(HashMap[address, HashMap[address, uint256]]) # from => to => (version | converter)

event Pull:
    _token: indexed(address)
    _amount: uint256

event SetOperator:
    operator: indexed(address)

event DeployConverter:
    _from: indexed(address)
    _to: indexed(address)
    _converter: address

event Sweep:
    _token: indexed(address)
    _amount: uint256

event AddBucket:
    _bucket: indexed(address)
    _after: address

event RemoveBucket:
    _bucket: indexed(address)

event ReplaceBucket:
    _old: indexed(address)
    _new: indexed(address)

event SetConverter:
    _from: indexed(address)
    _to: indexed(address)
    _converter: address

event SetFactory:
    _factory: indexed(address)
    _version: uint256

event SetFactoryVersionEnabled:
    _version: indexed(uint256)
    _enabled: bool

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

MAX_NUM_BUCKETS: constant(uint256) = 64
MASK: constant(uint256) = (1 << 96) - 1
SENTINEL: constant(address) = 0x1111111111111111111111111111111111111111

implements: Robo
implements: OneSplit

@external
def __init__(_treasury: address, _ingress: address):
    """
    @notice Constructor
    @param _treasury Treasury contract, ultimate destination of all assets
    @param _ingress Ingress contract, where assets get pulled from
    """
    treasury = _treasury
    self.management = msg.sender
    self.operator = msg.sender
    self.ingress = Ingress(_ingress)
    self.linked_buckets[SENTINEL] = SENTINEL
    self.packed_factory_versions[0] = 1

@external
@view
def is_bucket(_bucket: address) -> bool:
    """
    @notice Query whether the address is a valid bucket
    @param _bucket Bucket address
    @return True: address is a valid bucket, False: address is not a valid bucket
    """
    return _bucket != SENTINEL and self.linked_buckets[_bucket] != empty(address)

@external
@view
def buckets() -> DynArray[address, MAX_NUM_BUCKETS]:
    """
    @notice Query list of configured buckets
    @return Array of buckets
    """
    buckets: DynArray[address, MAX_NUM_BUCKETS] = []
    bucket: address = SENTINEL
    for _ in range(MAX_NUM_BUCKETS):
        bucket = self.linked_buckets[bucket]
        if bucket == SENTINEL:
            break
        buckets.append(bucket)
    return buckets

@external
@view
def whitelisted(_token: address) -> bool:
    """
    @notice Query whether a token is whitelisted in any of the buckets
    @param _token Token address
    @return True: token is whitelisted in a bucket, False: token is not whitelisted
        in a bucket
    """
    bucket: address = SENTINEL
    for _ in range(MAX_NUM_BUCKETS):
        bucket = self.linked_buckets[bucket]
        if bucket == SENTINEL:
            break
        if Bucket(bucket).whitelisted(_token):
            return True
    return False

@external
@view
def factory() -> (uint256, address, bool):
    """
    @notice Query current factory details
    @return Tuple with factory version, factory address and a flag representing
        the enable status of this factory version
    """
    version: uint256 = 0
    factory: address = empty(address)
    (version, factory) = self._unpack(self.packed_factory)
    return (version, factory, self._enabled(version))

@external
@view
def factory_version_enabled(_version: uint256) -> bool:
    """
    @notice Query whether a specific factory version is enabled
    @param _version Factory version
    @return True: factory version enabled, False: factory version disabled
    """
    return self._enabled(_version)

@external
def pull(_token: address, _amount: uint256 = max_value(uint256)) -> address:
    """
    @notice Pull a token from the ingress into a bucket
    @param _token Token to pull
    @param _amount Amount of token to pull. Defaults to current ingress balance
    @return The bucket the funds were sent to
    @dev Can only be called by the operator
    """
    assert msg.sender == self.operator
    assert _token != empty(address)
    assert _amount > 0

    bucket: address = SENTINEL
    for _ in range(MAX_NUM_BUCKETS):
        bucket = self.linked_buckets[bucket]
        if bucket == SENTINEL:
            break

        if Bucket(bucket).above_floor():
            continue

        # obtain an allowance to transfer from the ingress
        ingress: Ingress = self.ingress
        ingress.convert(_token, 0)

        amount: uint256 = _amount
        if _amount == max_value(uint256):
            amount = ERC20(_token).balanceOf(ingress.address)

        # handle conversion inside bucket
        assert ERC20(_token).transferFrom(ingress.address, bucket, amount, default_return_value=True)
        Bucket(bucket).convert(_token, amount)
        log Pull(_token, amount)

        return bucket

    raise "no bucket available"

@external
@view
def converter(_from: address, _to: address) -> address:
    """
    @notice Query converter contract for a pair, if any is known
    @param _from The token to convert from
    @param _to The token to convert to
    @return The converter contract, if any
    """
    return self._converter(_from, _to)

@external
def deploy_converter(_from: address, _to: address) -> address:
    """
    @notice Deploy a converter for a pair, if none is known
    @param _from The token to convert from
    @param _to The token to convert to
    @return The converter contract
    @dev Can only be called by an existing bucket
    """
    assert self.linked_buckets[msg.sender] != empty(address)

    converter: address = self._converter(_from, _to)
    if converter == empty(address):
        version: uint256 = 0
        factory: address = empty(address)
        (version, factory) = self._unpack(self.packed_factory)
        assert factory != empty(address)
        assert self._enabled(version)
        converter = Factory(factory).deploy(_from, _to)
        self.packed_converters[_from][_to] = self._pack(version, converter)
        log DeployConverter(_from, _to, converter)

    return converter

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
def add_bucket(_bucket: address, _after: address):
    """
    @notice Add a bucket
    @param _bucket Address of the bucket
    @param _after Address of the bucket to add it after in the list
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    assert _bucket != empty(address)
    assert self.linked_buckets[_bucket] == empty(address)
    next: address = self.linked_buckets[_after]
    assert next != empty(address)
    num_buckets: uint256 = self.num_buckets
    assert num_buckets < MAX_NUM_BUCKETS

    self.num_buckets = num_buckets + 1
    self.linked_buckets[_after] = _bucket
    self.linked_buckets[_bucket] = next
    log AddBucket(_bucket, _after)

@external
def remove_bucket(_bucket: address, _previous: address):
    """
    @notice Remove a bucket
    @param _bucket Address of the bucket
    @param _previous Address of the bucket before the target in the list
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    assert _bucket != SENTINEL
    next: address = self.linked_buckets[_bucket]
    assert next != empty(address)
    assert self.linked_buckets[_previous] == _bucket

    self.num_buckets -= 1
    self.linked_buckets[_previous] = next
    self.linked_buckets[_bucket] = empty(address)
    log RemoveBucket(_bucket)

@external
def replace_bucket(_old: address, _new: address, _previous: address):
    """
    @notice Replace a bucket
    @param _old Address of the old bucket
    @param _new Address of the new bucket
    @param _previous Address of the bucket before the target in the list
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    assert _old != SENTINEL
    next: address = self.linked_buckets[_old]
    assert next != empty(address)
    assert _new != empty(address)
    assert self.linked_buckets[_new] == empty(address)
    assert self.linked_buckets[_previous] == _old

    self.linked_buckets[_previous] = _new
    self.linked_buckets[_old] = empty(address)
    self.linked_buckets[_new] = next
    log ReplaceBucket(_old, _new)

@external
def set_converter(_from: address, _to: address, _converter: address):
    """
    @notice Set a converter for a specific pair
    @param _from The token converted from
    @param _to The token converted to
    @param _converter Address of the converter
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    self.packed_converters[_from][_to] = self._pack(0, _converter)
    log SetConverter(_from, _to, _converter)

@external
def set_factory(_factory: address):
    """
    @notice Set a new factory for converters
    @param _factory The factory address, if any
    @dev Can only be called by management
    @dev Increments the factory version if a factory is set
    """
    assert msg.sender == self.management
    version: uint256 = self._unpack(self.packed_factory)[0]
    if _factory != empty(address):
        version += 1
    self.packed_factory = self._pack(version, _factory)
    log SetFactory(_factory, version)

@external
def set_factory_version_enabled(_version: uint256, _enabled: bool):
    """
    @notice Toggle all conversion contracts deployed by a specific factory
    @param _version The version of the factory
    @param _enabled True: enable all conversions, False: disable all conversions
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    latest: uint256 = self._unpack(self.packed_factory)[0]
    assert _version > 0 and _version <= latest
    flags: uint256 = self.packed_factory_versions[_version / 256]
    mask: uint256 = 1 << (_version % 256)
    if _enabled:
        flags |= mask
    else:
        flags &= ~mask
    self.packed_factory_versions[_version / 256] = flags
    log SetFactoryVersionEnabled(_version, _enabled)

@external
def set_operator(_operator: address):
    """
    @notice Set the new operator address
    @param _operator New operator address
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    self.operator = _operator
    log SetOperator(_operator)

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


##### Compatibility with ingress contract #####

@external
@view
def getExpectedReturn(
    _a: address, _b: address, _c: uint256, _d: uint256, _e: uint256
) -> (uint256, uint256[1]):
    return (0, [0])

@external
def swap(
    _a: address, _b: address, _c: uint256, _d: uint256, _e: uint256[1], _f: uint256
):
    pass

##### Internal utility functions #####

@internal
@view
def _converter(_from: address, _to: address) -> address:
    version: uint256 = 0
    converter: address = empty(address)
    (version, converter) = self._unpack(self.packed_converters[_from][_to])
    if not self._enabled(version):
        return empty(address)
    return converter

@internal
@view
def _enabled(_version: uint256) -> bool:
    return self.packed_factory_versions[_version / 256] & (1 << (_version % 256)) > 0

@internal
@pure
def _unpack(_packed: uint256) -> (uint256, address):
    return (_packed & MASK, convert(_packed >> 96, address))

@internal
@pure
def _pack(_version: uint256, _target: address) -> uint256:
    assert _version <= MASK
    return _version | (convert(_target, uint256) << 96)
