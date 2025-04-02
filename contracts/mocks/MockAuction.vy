struct Info:
    kicked: uint64
    scaler: uint64
    initial: uint128

interface Auction:
    def auctions(_from: address) -> (uint64, uint64, uint128): view
    def enable(_from: address): nonpayable
    def kickable(_from: address) -> uint256: view
    def kick(_from: address) -> uint256: nonpayable
    def getAmountNeeded(_from: address) -> uint256: view
    def available(_from: address) -> uint256: view
    def take(_from: address) -> uint256: nonpayable
    def startingPrice() -> uint256: view
    def setStartingPrice(_price: uint256): nonpayable

implements: Auction

@external
@view
def auctions(_from: address) -> (uint64, uint64, uint128):
    return (0, 0, 0)

@external
def enable(_from: address):
    return

@external
@view
def kickable(_from: address) -> uint256:
    return 0

@external
def kick(_from: address) -> uint256:
    return 0

@external
@view
def getAmountNeeded(_from: address) -> uint256:
    return 0

@external
@view
def available(_from: address) -> uint256:
    return 0

@external
def take(_from: address) -> uint256:
    return 0

@external
@view
def startingPrice() -> uint256:
    return 0

@external
def setStartingPrice(_price: uint256):
    return
