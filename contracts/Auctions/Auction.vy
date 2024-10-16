# @version 0.3.10

from vyper.interfaces import ERC20
from vyper.interfaces import ERC20Detailed

event AuctionEnabled:
    auctionId: indexed(bytes32)
    fromToken: indexed(address)
    wantToken: indexed(address)
    auctionContract: address

event AuctionDisabled:
    auctionId: indexed(bytes32)
    fromToken: indexed(address)
    wantToken: indexed(address)
    auctionContract: address

event AuctionKicked:
    auctionId: indexed(bytes32)
    available: uint256

event GovernanceTransferred:
    previousGovernance: indexed(address)
    newGovernance: indexed(address)

event UpdatePendingGovernance:
    newPendingGovernance: indexed(address)

struct TokenInfo:
    tokenAddress: address
    scaler: uint256

struct AuctionInfo:
    tokenInfo: TokenInfo
    kicked: uint256
    receiver: address
    initialAvailable: uint256

struct GPv2Order_Data:
    sellToken: ERC20  # token to sell
    buyToken: ERC20  # token to buy
    receiver: address  # receiver of the token to buy
    sellAmount: uint256
    buyAmount: uint256
    validTo: uint32  # timestamp until order is valid
    appData: bytes32  # extra info about the order
    feeAmount: uint256  # amount of fees in sellToken
    kind: bytes32  # buy or sell
    partiallyFillable: bool  # partially fillable (True) or fill-or-kill (False)
    sellTokenBalance: bytes32  # From where the sellToken balance is withdrawn
    buyTokenBalance: bytes32  # Where the buyToken is deposited

WAD: constant(uint256) = 10 ** 18
MAX_COINS_LEN: constant(uint256) = 20
ERC1271_MAGIC_VALUE: constant(bytes4) = 0x1626ba7e
ETH_ADDRESS: constant(address) = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE
COW_SETTLEMENT: public(constant(address)) = 0x9008D19f58AAbD9eD0D60971565AA8510560ab41

PAYMENT_TOKEN: public(immutable(address))

PAYMENT_SCALER: immutable(uint256)

PAYMENT_RECEIVER: public(immutable(address))

governance: public(address)
pendingGovernance: public(address)

auctionLength: public(uint256)
startingPrice: public(uint256)
auctions: public(HashMap[bytes32, AuctionInfo])

@external
def __init__(
    _governance: address, 
    _payment_token: address,
    _payment_receiver: address,
    _auction_length: uint256,
    _starting_price: uint256
):
    """
    @notice Contract constructor
    """
    self.governance = _governance
    PAYMENT_TOKEN = _payment_token
    PAYMENT_SCALER = WAD / pow_mod256(10, convert(ERC20Detailed(_payment_token).decimals(), uint256))
    PAYMENT_RECEIVER = _payment_receiver
    self.auctionLength = _auction_length
    self.startingPrice = _starting_price

@view
@external
def want() -> address:
    return PAYMENT_TOKEN

@view
@external
def getAuctionId(_token: address) -> bytes32:
    return self._get_auction_id(_token)

@view
@internal
def _get_auction_id(_token: address) -> bytes32:
    return keccak256(_abi_encode(_token))

@view
@external
def isEnabled(token_from: address) -> bool:
    return self.auctions[self._get_auction_id(token_from)].tokenInfo.tokenAddress != empty(address)

@view
@external
def kickable(_auction_id: bytes32) -> uint256:
    """
    @notice Determines the amount of tokens that can be kicked for a given auction
    @param _auction_id The unique identifier of the auction
    @return The amount of tokens that can be kicked
    """
    # If not enough time has passed then `kickable` is 0.
    if self.auctions[_auction_id].kicked + self.auctionLength > block.timestamp:
        return 0

    # Else just use the full balance of this contract.
    return ERC20(self.auctions[_auction_id].tokenInfo.tokenAddress).balanceOf(self)

@view
@external
def getAmountNeeded(token_from: address) -> uint256:
    return self._get_amount_needed(token_from)

@view
@internal
def _get_amount_needed(token_from: address) -> uint256:
    _id: bytes32 = self._get_auction_id(token_from)
    return self.auctions[_id].initialAvailable * self.auctions[_id].tokenInfo.scaler * self._price(token_from) / WAD
    
@view
@external
def price(token_from: address) -> uint256:
    return self._price(token_from)
    

@view
@internal
def _price(token_from: address) -> uint256:
    _id: bytes32 = self._get_auction_id(token_from)
    kicked: uint256 = self.auctions[_id].kicked
    length: uint256 = self.auctionLength
    if kicked + length > block.timestamp:
        return 0

    balance: uint256 = self.auctions[_id].initialAvailable

    if balance == 0:
        return 0

    starting_price: uint256 = self.startingPrice * WAD * WAD / (balance * self.auctions[_id].tokenInfo.scaler)
 
    return starting_price - (starting_price * (block.timestamp - kicked) / length) / PAYMENT_SCALER


@external
@nonreentrant('lock')
def kick(_auction_id: bytes32) -> uint256:
    """
    @notice Kick-starts an auction
    @param _auction_id The unique identifier of the auction
    @return available The amount of tokens available for the auction
    """
    _from_token: address = self.auctions[_auction_id].tokenInfo.tokenAddress
    assert _from_token != empty(address), "not enabled"
    assert block.timestamp > self.auctions[_auction_id].kicked + self.auctionLength, "too soon"

    available: uint256 = ERC20(_from_token).balanceOf(self)

    assert available != 0, "nothing to kick"

    # Update the auctions status.
    self.auctions[_auction_id].kicked = block.timestamp
    self.auctions[_auction_id].initialAvailable = available

    log AuctionKicked(_auction_id, available)

    return available

@external
def take(token_from: address) -> uint256:
    payment_amount: uint256 = self._get_amount_needed(token_from)
    assert payment_amount != 0, "zero amount"

    balance: uint256 = self.auctions[self._get_auction_id(token_from)].initialAvailable

    assert ERC20(token_from).transfer(msg.sender, balance, default_return_value=True)

    ERC20(PAYMENT_TOKEN).transferFrom(msg.sender, PAYMENT_RECEIVER, payment_amount, default_return_value=True)

    return balance
    

@view
@external
def isValidSignature(_hash: bytes32, signature: Bytes[1792]) -> bytes4:
    """
    @notice ERC1271 signature verifier method
    @param _hash Hash of signed object. Ignored here
    @param signature Signature for the object. (GPv2Order.Data) here
    @return `ERC1271_MAGIC_VALUE` if signature is OK
    """
    order: GPv2Order_Data =  _abi_decode(signature, (GPv2Order_Data))
    # Verify's the auction is valid
    payment_amount: uint256 = self._get_amount_needed(order.sellToken.address)

    # Verify order details
    assert payment_amount > 0, "zero amount"
    assert order.buyAmount >= payment_amount, "bad price"
    assert order.buyToken.address == PAYMENT_TOKEN, "bad token"
    assert order.receiver == PAYMENT_RECEIVER, "bad receiver"
    assert order.sellAmount <= self.auctions[self._get_auction_id(order.sellToken.address)].initialAvailable, "bad amount"

    return ERC1271_MAGIC_VALUE


@external
def enable(
    _from: address,
    _receiver: address = msg.sender
) -> bytes32:
    """
    @notice Enables a new auction.
    @param _from The address of the token to be auctioned.
    @param _receiver The address that will receive the funds in the auction.
    @return The unique identifier of the enabled auction.
    """
    assert msg.sender == self.governance, "!governance"
    assert _from != empty(address) and _from != PAYMENT_TOKEN, "ZERO ADDRESS"
    assert _receiver != empty(address) and _receiver != self, "receiver"

    # Cannot have more than 18 decimals.
    decimals: uint8 = ERC20Detailed(_from).decimals()
    assert decimals <= 18, "unsupported decimals"

    # Calculate the id.
    _auction_id: bytes32 = self._get_auction_id(_from)
    assert self.auctions[_auction_id].tokenInfo.tokenAddress == empty(address), "already enabled"

    # Store all needed info.
    self.auctions[_auction_id].tokenInfo = TokenInfo({
        tokenAddress: _from,
        scaler: WAD / pow_mod256(10, convert(decimals, uint256))
    })
    self.auctions[_auction_id].receiver = _receiver

    assert ERC20(_from).approve(COW_SETTLEMENT, max_value(uint256), default_return_value=True)

    log AuctionEnabled(_auction_id, _from, PAYMENT_TOKEN, self)

    return _auction_id

@external
def disable(_from: address):
    """
    @notice Disables an auction
    @param _from The address of the token being auctioned
    """
    assert msg.sender == self.governance, "!governance"
    
    _auction_id: bytes32 = self._get_auction_id(_from)

    # Make sure the auction was enabled.
    assert self.auctions[_auction_id].tokenInfo.tokenAddress != empty(address), "not enabled"

    # Remove the struct.
    self.auctions[_auction_id] = empty(AuctionInfo)

    log AuctionDisabled(_auction_id, _from, PAYMENT_TOKEN, self)

@external
def transferGovernance(new_governance: address):
    """
    @notice Set the governance address
    @param new_governance The new governance address
    """
    assert msg.sender == self.governance, "not governance"
    self.pendingGovernance = new_governance

    log UpdatePendingGovernance(new_governance)

@external
def acceptGovernance():
    """
    @notice Accept the governance address
    """
    assert msg.sender == self.pendingGovernance, "not pending governance"

    old_governance: address = self.governance

    self.governance = msg.sender
    self.pendingGovernance = empty(address)

    log GovernanceTransferred(old_governance, msg.sender)

@external
def recover(_coins: DynArray[ERC20, MAX_COINS_LEN]):
    """
    @notice Recover ERC20 tokens or Ether from this contract
    @dev Callable only by owner and emergency owner
    @param _coins Token addresses
    """
    _governance: address = self.governance
    assert msg.sender == _governance, "!governance"

    for coin in _coins:
        assert coin.transfer(_governance, coin.balanceOf(self), default_return_value=True)
