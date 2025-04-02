# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun

interface Provider:
    def rate(_token: address) -> uint256: view

implements: Provider

rate: public(HashMap[address, uint256])

@external
def set_rate(_token: address, _rate: uint256):
    self.rate[_token] = _rate
