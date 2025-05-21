# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun
"""
@title RoboTreasury
@author Yearn Finance
@license GNU AGPLv3
@notice
    Temporary guardrail for the RoboTreasury system. This contract maintains a 
    whitelist of tokens that can be pulled from the ingress into RoboTreasury
    by the operator.
"""

interface Robo:
    def pull(_token: address, _amount: uint256) -> address: nonpayable

robo: public(immutable(Robo))
management: public(immutable(address))
operator: public(immutable(address))
whitelist: public(HashMap[address, bool])

event SetWhitelist:
    token: indexed(address)
    whitelist: bool

implements: Robo

@external
def __init__(_robo: address, _management: address, _operator: address):
    robo = Robo(_robo)
    management = _management
    operator = _operator

@external
def set_whitelist(_token: address, _whitelist: bool = True):
    assert msg.sender == management
    self.whitelist[_token] = _whitelist
    log SetWhitelist(_token, _whitelist)

@external
def pull(_token: address, _amount: uint256 = max_value(uint256)) -> address:
    assert msg.sender == operator
    assert self.whitelist[_token]
    return robo.pull(_token, _amount)
