from pytest import fixture

USDC      = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
USDT      = '0xdAC17F958D2ee523a2206206994597C13D831ec7'
USDS      = '0xdC035D45d973E3EC169d2276DDab16f1e407384F'
DAI       = '0x6B175474E89094C44Da98b954EedeAC495271d0F'
CRVUSD    = '0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'
YVUSDC1   = '0xBe53A109B494E5c9f97b9Cd39Fe969BE68BF6204'
YVUSDT1   = '0x310B7Ea7475A0B449Cfd73bE81522F1B88eFAFaa'
SUSDS     = '0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD'
YVUSDS1   = '0x182863131F9a4630fF9E27830d945B1413e347E8'
SDAI      = '0x83F20F44975D03b1b09e64809B757c47f942BEeA'
YVDAI1    = '0x028eC7330ff87667b6dfb0D94b954c820195336c'
YVCRVUSD2 = '0xBF319dDC2Edc1Eb6FDf9910E39b37Be221C8805F'

LOW_DECIMAL_STABLES = [USDC, USDT]
STABLES = [USDS, DAI, CRVUSD]
LOW_DECIMAL_VAULTS = [YVUSDC1, YVUSDT1]
VAULTS = [SUSDS, YVUSDS1, SDAI, YVDAI1, YVCRVUSD2]

UNIT = 10**18

@fixture
def provider(project, accounts):
    return project.StablesProvider.deploy(sender=accounts[0])

def value(provider, asset, amount):
    return amount * provider.rate(asset) // UNIT

def test_low_decimal_stables(provider):
    for asset in LOW_DECIMAL_STABLES:
        assert value(provider, asset, 10**6) == UNIT

def test_stables(provider):
    for asset in STABLES:
        assert value(provider, asset, UNIT) == UNIT

def test_low_decimal_vaults(provider):
    for asset in LOW_DECIMAL_VAULTS:
        v = value(provider, asset, 10**6)
        assert v > UNIT and v < UNIT * 12 // 10

def test_vaults(provider):
    for asset in VAULTS:
        v = value(provider, asset, 10**18)
        assert v > UNIT and v < UNIT * 12 // 10
