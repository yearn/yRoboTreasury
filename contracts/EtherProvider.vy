# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun

from vyper.interfaces import ERC4626

interface Provider:
    def rate(_token: address) -> uint256: view

interface YearnVaultV2:
    def pricePerShare() -> uint256: view

WETH: constant(address)     = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
STETH: constant(address)    = 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84
YVWETH1: constant(address)  = 0xc56413869c6CDf96496f2b1eF801fEDBdFA7dDB0
STYETH: constant(address)   = 0x583019fF0f430721aDa9cfb4fac8F06cA104d0B4
YVYETHLP: constant(address) = 0x58900d761Ae3765B75DDFc235c1536B527F25d8F

UNIT: constant(uint256) = 10**18
LOW_DECIMAL_FACTOR: constant(uint256) = 10**12
LOW_DECIMAL_PRODUCT: constant(uint256) = 10**30

implements: Provider

@external
@view
def rate(_token: address) -> uint256:
    if _token in [WETH, STETH]:
        return UNIT
    if _token in [YVWETH1, STYETH]:
        return ERC4626(_token).convertToAssets(UNIT)
    if _token == YVYETHLP:
        return YearnVaultV2(YVYETHLP).pricePerShare()
    raise
