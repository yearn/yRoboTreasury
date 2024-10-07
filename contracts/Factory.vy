# pragma version 0.3.10

from vyper.interfaces import ERC20

interface Factory:
    def deploy(_from: address, _to: address) -> address: nonpayable

interface Robo:
    def is_bucket(_bucket: address) -> bool: view

interface Converter:
    def convert(_from: address, _amount: uint256, _to: address): nonpayable

interface AuctionFactory:
    def createNewAuction(
        _to: address, _hook: address, _governance: address, _length: uint256, _cooldown: uint256
    ) -> Auction: nonpayable

interface Auction:
    def getAuctionId(_from: address) -> bytes32: view
    def auctionInfo(_id: bytes32) -> address: view
    def kickable(_id: bytes32) -> uint256: view
    def enable(_from: address, _receiver: address): nonpayable
    def kick(_id: bytes32) -> uint256: nonpayable
    def transferGovernance(_new: address): nonpayable

vault: public(immutable(address))
robo: public(immutable(Robo))
auction_factory: public(immutable(AuctionFactory))
management: public(address)
pending_management: public(address)
auctions: public(HashMap[address, Auction])

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

AUCTION_LENGTH: constant(uint256) = 24 * 60 * 60

implements: Factory
implements: Converter

@external
def __init__(_vault: address, _robo: address, _auction_factory: address):
    vault = _vault
    robo = Robo(_robo)
    auction_factory = AuctionFactory(_auction_factory)
    self.management = msg.sender

@external
def deploy(_from: address, _to: address) -> address:
    assert msg.sender == robo.address

    auction: Auction = self.auctions[_to]
    if auction.address == empty(address):
        auction = auction_factory.createNewAuction(_to, empty(address), self, AUCTION_LENGTH, 0)
        self.auctions[_to] = auction

    return self

@external
def convert(_from: address, _amount: uint256, _to: address):
    assert robo.is_bucket(msg.sender)

    auction: Auction = self.auctions[_to]
    assert auction.address != empty(address)

    # enable auction if necessary
    auction_id: bytes32 = auction.getAuctionId(_from)
    if auction.auctionInfo(auction_id) != _from:
        auction.enable(_from, vault)

    # transfer tokens to auction contract
    ERC20(_from).transfer(auction.address, _amount)

    # kick auction if possible
    if auction.kickable(auction_id) > 0:
        auction.kick(auction_id)

@external
def sweep(_token: address, _amount: uint256 = max_value(uint256)):
    assert msg.sender == self.management
    amount: uint256 = _amount
    if _amount == max_value(uint256):
        amount = ERC20(_token).balanceOf(self)
    assert ERC20(_token).transfer(self.management, amount, default_return_value=True)

@external
def transfer_auction_governance(_auction: address):
    assert msg.sender == self.management
    Auction(_auction).transferGovernance(msg.sender)

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
