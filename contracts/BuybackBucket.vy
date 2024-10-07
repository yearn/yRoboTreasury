# pragma version 0.3.10

from vyper.interfaces import ERC20

interface Robo:
    def deploy_converter(_from: address, _to: address) -> address: nonpayable

interface Converter:
    def convert(_from: address, _amount: uint256, _to: address): nonpayable

interface Bucket:
    def whitelisted(_token: address) -> bool: view
    def above_floor() -> bool: nonpayable
    def convert(_token: address, _amount: uint256): nonpayable

vault: public(immutable(address))
robo: public(immutable(Robo))
buyback_token: public(immutable(address))
parent: public(address)
management: public(address)
pending_management: public(address)

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

implements: Bucket

@external
def __init__(_vault: address, _robo: address, _token: address):
    vault = _vault
    robo = Robo(_robo)
    buyback_token = _token
    self.management = msg.sender

@external
@view
def whitelisted(_token: address) -> bool:
    return _token == buyback_token

@external
@view
def above_floor() -> bool:
    return False

@external
def convert(_token: address, _amount: uint256):
    assert msg.sender == self.parent

    if _token == buyback_token:
        assert ERC20(_token).transfer(vault, _amount, default_return_value=True)
        return

    converter: address = robo.deploy_converter(_token, buyback_token)
    assert ERC20(_token).transfer(converter, _amount, default_return_value=True)
    Converter(converter).convert(_token, _amount, buyback_token)

@external
def sweep(_token: address, _amount: uint256 = max_value(uint256)):
    assert msg.sender == self.management
    amount: uint256 = _amount
    if _amount == max_value(uint256):
        amount = ERC20(_token).balanceOf(self)
    assert ERC20(_token).transfer(self.management, amount, default_return_value=True)

@external
def set_parent(_parent: address):
    assert msg.sender == self.management
    self.parent = _parent

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
