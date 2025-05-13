from pytest import fixture

WETH     = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
STETH    = '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
YVWETH1  = '0xc56413869c6CDf96496f2b1eF801fEDBdFA7dDB0'
STYETH   = '0x583019fF0f430721aDa9cfb4fac8F06cA104d0B4'
YVYETHLP = '0x58900d761Ae3765B75DDFc235c1536B527F25d8F'

ETHERS = [WETH, STETH]
VAULTS = [YVWETH1, STYETH, YVYETHLP]

UNIT = 10**18

@fixture
def provider(project, accounts):
    return project.EtherProvider.deploy(sender=accounts[0])

def value(provider, asset, amount):
    return amount * provider.rate(asset) // UNIT

def test_ethers(provider):
    for asset in ETHERS:
        assert value(provider, asset, UNIT) == UNIT

def test_vaults(provider):
    for asset in VAULTS:
        v = value(provider, asset, 10**18)
        assert v > UNIT and v < UNIT * 12 // 10
