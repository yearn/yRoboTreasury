# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun
"""
@title Guard
@author Yearn Finance
@license GNU AGPLv3
@notice
    Temporary guardrail for the RoboTreasury system. This contract queries a 
    whitelist of tokens that can be pulled from the ingress into RoboTreasury
    by the operator.
"""

interface Robo:
    def pull(_token: address, _amount: uint256) -> address: nonpayable

interface Guard:
    def whitelist(_token: address) -> bool: view

robo: public(immutable(Robo))
guard: public(immutable(Guard))
operator: public(immutable(address))

event SetWhitelist:
    token: indexed(address)
    whitelist: bool

implements: Robo

@external
def __init__(_robo: address, _guard: address, _operator: address):
    robo = Robo(_robo)
    guard = Guard(_guard)
    operator = _operator

@external
def pull(_token: address, _amount: uint256 = max_value(uint256)) -> address:
    assert msg.sender == operator
    assert guard.whitelist(_token)
    return robo.pull(_token, _amount)
