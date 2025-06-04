# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun
"""
@title Conversion factory
@author Yearn Finance
@license GNU AGPLv3
@notice
    Factory to deploy new conversion contracts.
    This specific instance deploys auctions to perform the conversion.
"""

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
operator: public(address)
auctions: public(HashMap[address, Auction])

event Deploy:
    _to: indexed(address)
    _auction: address

event Convert:
    _from: indexed(address)
    _to: indexed(address)
    _amount: uint256

event Sweep:
    _token: indexed(address)
    _amount: uint256

event Call:
    _want: indexed(address)
    _to: indexed(address)
    _data: Bytes[2048]

event SetOperator:
    operator: indexed(address)

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

implements: Factory
implements: Converter

@external
def __init__(_treasury: address, _robo: address, _auction_factory: address):
    """
    @notice Constructor
    @param _treasury Treasury contract, ultimate destination of all assets
    @param _robo Robo contract
    @param _auction_factory Factory for auction contracts
    """
    treasury = _treasury
    robo = Robo(_robo)
    auction_factory = AuctionFactory(_auction_factory)
    self.management = msg.sender
    self.operator = msg.sender

@external
def deploy(_from: address, _to: address) -> address:
    """
    @notice Deploy a new conversion contract
    @param _from Token to convert from
    @param _to Token to convert to
    @dev Can only be called by the Robo contract
    @dev Re-uses already deployed auction contracts for the 'to' token
    """
    assert msg.sender == robo.address

    if self.auctions[_to].address == empty(address):
        auction: Auction = auction_factory.createNewAuction(_to, treasury)
        self.auctions[_to] = auction
        log Deploy(_to, auction.address)

    return self

@external
def convert(_from: address, _amount: uint256, _to: address):
    """
    @notice Start conversion of a token by auctioning them off
    @param _from Token to convert from
    @param _amount Amount of tokens to convert
    @param _to Token to convert to
    @dev Can only be called by a whitelisted bucket
    @dev Expects tokens to be transfered into the contract prior to being called
    """
    assert robo.is_bucket(msg.sender)

    auction: Auction = self.auctions[_to]
    assert auction.address != empty(address)

    # enable auction if necessary
    if auction.auctions(_from)[1] == 0:
        auction.enable(_from)

    # transfer tokens to auction contract
    assert ERC20(_from).transfer(auction.address, _amount, default_return_value=True)

    # kick auction if possible
    if auction.kickable(_from) > 0:
        auction.kick(_from)
    log Convert(_from, _to, _amount)

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
def call(_want: address, _data: Bytes[2048]):
    """
    @notice Low level call to an auction contract
    @param _want Want token of the auction contract
    @param _data Calldata
    @dev Can only be called by operator
    """
    assert msg.sender == self.operator
    auction: Auction = self.auctions[_want]
    assert auction.address != empty(address)
    raw_call(auction.address, _data)
    log Call(_want, auction.address, _data)

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
