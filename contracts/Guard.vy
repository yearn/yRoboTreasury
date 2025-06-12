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

interface Whitelist:
    def whitelist(_token: address) -> bool: view

robo: public(immutable(Robo))
whitelist: public(immutable(Whitelist))
operator: public(immutable(address))

implements: Robo

@external
def __init__(_robo: address, _whitelist: address, _operator: address):
    robo = Robo(_robo)
    whitelist = Whitelist(_whitelist)
    operator = _operator

@external
def pull(_token: address, _amount: uint256 = max_value(uint256)) -> address:
    assert msg.sender == operator
    assert whitelist.whitelist(_token)
    return robo.pull(_token, _amount)
