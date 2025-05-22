# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun
"""
@title Treasury
@author Yearn Finance
@license GNU AGPLv3
@notice
    Treasury contract. Intentionally kept as simple as possible to improve auditability
"""

from vyper.interfaces import ERC20

management: public(address)
pending_management: public(address)
pending_management_time: public(uint256)

event ToManagement:
    token: indexed(address)
    amount: uint256

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

DELAY: constant(uint256) = 7 * 24 * 60 * 60

@external
def __init__(_pending: address):
    """
    @notice Constructor
    """
    self.management = msg.sender

    if _pending != empty(address):
        self.pending_management = _pending
        self.pending_management_time = block.timestamp

@external
def to_management(_token: address, _amount: uint256 = max_value(uint256)):
    """
    @notice Transfer tokens to management
    @param _token The token to transfer
    @param _amount The amount to transfer. Defaults to entire token balance
    @dev Can only be called by management
    """
    assert msg.sender == self.management

    amount: uint256 = _amount
    if _amount == max_value(uint256):
        amount = ERC20(_token).balanceOf(self)

    log ToManagement(_token, amount)
    assert ERC20(_token).transfer(msg.sender, amount, default_return_value=True)

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
    self.pending_management_time = block.timestamp + DELAY
    log PendingManagement(_management)

@external
def accept_management():
    """
    @notice 
        Accept management role.
        Can only be called by account previously marked as pending management by current management.
        Can only be called after the delay has expired
    """
    assert msg.sender == self.pending_management
    assert block.timestamp >= self.pending_management_time, "too early"
    self.pending_management = empty(address)
    self.management = msg.sender
    log SetManagement(msg.sender)
