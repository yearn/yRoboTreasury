from ape import Contract
from pytest import fixture

YCHAD = '0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52'
INGRESS = '0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde' # treasury.ychad.eth

@fixture
def deployer(accounts):
    return accounts[0]

@fixture
def alice(accounts):
    return accounts[1]

@fixture
def bob(accounts):
    return accounts[2]

@fixture
def charlie(accounts):
    return accounts[3]

@fixture
def ychad(accounts):
    return accounts[YCHAD]

@fixture
def ingress():
    return Contract(INGRESS)
