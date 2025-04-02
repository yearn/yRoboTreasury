# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun

interface Bucket:
    def whitelisted(_token: address) -> bool: view
    def above_floor() -> bool: nonpayable
    def convert(_token: address, _amount: uint256): nonpayable

implements: Bucket

whitelisted: public(HashMap[address, bool])
above_floor: public(bool)

@external
def convert(_token: address, _amount: uint256):
    pass

@external
def set_whitelisted(_token: address, _flag: bool):
    self.whitelisted[_token] = _flag

@external
def set_above_floor(_above_floor: bool):
    self.above_floor = _above_floor
