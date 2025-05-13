# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version cancun

from vyper.interfaces import ERC4626

interface Provider:
    def rate(_token: address) -> uint256: view

USDC: constant(address)      = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
USDT: constant(address)      = 0xdAC17F958D2ee523a2206206994597C13D831ec7
USDS: constant(address)      = 0xdC035D45d973E3EC169d2276DDab16f1e407384F
DAI: constant(address)       = 0x6B175474E89094C44Da98b954EedeAC495271d0F
CRVUSD: constant(address)    = 0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E

YVUSDC1: constant(address)   = 0xBe53A109B494E5c9f97b9Cd39Fe969BE68BF6204
YVUSDT1: constant(address)   = 0x310B7Ea7475A0B449Cfd73bE81522F1B88eFAFaa
SUSDS: constant(address)     = 0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD
YVUSDS1: constant(address)   = 0x182863131F9a4630fF9E27830d945B1413e347E8
SDAI: constant(address)      = 0x83F20F44975D03b1b09e64809B757c47f942BEeA
YVDAI1: constant(address)    = 0x028eC7330ff87667b6dfb0D94b954c820195336c
YVCRVUSD2: constant(address) = 0xBF319dDC2Edc1Eb6FDf9910E39b37Be221C8805F

UNIT: constant(uint256) = 10**18
LOW_DECIMAL_FACTOR: constant(uint256) = 10**12
LOW_DECIMAL_PRODUCT: constant(uint256) = 10**30

implements: Provider

@external
@view
def rate(_token: address) -> uint256:
    if _token in [USDC, USDT]:
        return LOW_DECIMAL_PRODUCT
    if _token in [USDS, DAI, CRVUSD]:
        return UNIT
    if _token in [YVUSDC1, YVUSDT1]:
        return ERC4626(_token).convertToAssets(UNIT) * LOW_DECIMAL_FACTOR
    if _token in [SUSDS, YVUSDS1, SDAI, YVDAI1, YVCRVUSD2]:
        return ERC4626(_token).convertToAssets(UNIT)
    
    raise
