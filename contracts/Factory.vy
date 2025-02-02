# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun

from vyper.interfaces import ERC20

interface Factory:
    def deploy(_from: address, _to: address) -> address: nonpayable

interface Robo:
    def is_bucket(_bucket: address) -> bool: view

interface Converter:
    def convert(_from: address, _amount: uint256, _to: address): nonpayable

interface AuctionFactory:
    def createNewAuction(_want: address, _receiver: address) -> Auction: nonpayable

interface Auction:
    def auctions(_from: address) -> (uint64, uint64, uint128): view
    def enable(_from: address): nonpayable
    def kickable(_from: address) -> uint256: view
    def kick(_from: address) -> uint256: nonpayable

treasury: public(immutable(address))
robo: public(immutable(Robo))
auction_factory: public(immutable(AuctionFactory))
management: public(address)
pending_management: public(address)
auctions: public(HashMap[address, Auction])

event Deploy:
    to: indexed(address)
    auction: address

event Convert:
    have: indexed(address)
    amount: uint256
    want: indexed(address)

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

implements: Factory
implements: Converter

@external
def __init__(_treasury: address, _robo: address, _auction_factory: address):
    treasury = _treasury
    robo = Robo(_robo)
    auction_factory = AuctionFactory(_auction_factory)
    self.management = msg.sender

@external
def deploy(_from: address, _to: address) -> address:
    assert msg.sender == robo.address

    if self.auctions[_to].address == empty(address):
        auction: Auction = auction_factory.createNewAuction(_to, treasury)
        self.auctions[_to] = auction
        log Deploy(_to, auction.address)

    return self

@external
def convert(_from: address, _amount: uint256, _to: address):
    assert robo.is_bucket(msg.sender)

    auction: Auction = self.auctions[_to]
    assert auction.address != empty(address)

    # enable auction if necessary
    if auction.auctions(_from)[1] == 0:
        auction.enable(_from)

    # transfer tokens to auction contract
    ERC20(_from).transfer(auction.address, _amount)

    # kick auction if possible
    if auction.kickable(_from) > 0:
        auction.kick(_from)
    log Convert(_from, _amount, _to)

@external
def sweep(_token: address, _amount: uint256 = max_value(uint256)):
    assert msg.sender == self.management
    amount: uint256 = _amount
    if _amount == max_value(uint256):
        amount = ERC20(_token).balanceOf(self)
    assert ERC20(_token).transfer(self.management, amount, default_return_value=True)

@external
def call(_to: address, _data: Bytes[2048]):
    assert msg.sender == self.management
    auction: Auction = self.auctions[_to]
    assert auction.address != empty(address)
    raw_call(auction.address, _data)

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
