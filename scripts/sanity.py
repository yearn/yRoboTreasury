from ape import project, Contract
from json import load

YCHAD = '0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52'
INGRESS = '0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde'
OPS_SAFE = '0xABCDEF0028B6Cc3539C2397aCab017519f8744c8'

def main():
    d = load(open('deployment.json'))

    treasury = project.Treasury.at(d['TREASURY'])
    robo = project.Robo.at(d['ROBO'])
    factory = project.Factory.at(d['FACTORY'])
    stables_reserve = project.GenericBucket.at(d['STABLES_RESERVE'])
    stables_buffer = project.GenericBucket.at(d['STABLES_BUFFER'])
    ether_buffer = project.GenericBucket.at(d['ETHER_BUFFER'])
    yfi_buyback = project.BuybackBucket.at(d['YFI_BUYBACK'])
    yvyfilp_buyback = project.BuybackBucket.at(d['YVYFILP_BUYBACK'])
    splitter = project.SplitBucket.at(d['SPLITTER'])
    whitelist = project.Whitelist.at(d['WHITELIST'])
    guard = project.Guard.at(d['GUARD'])

    assert robo.ingress() == INGRESS
    assert guard.whitelist() == whitelist
    assert whitelist.management() == YCHAD
    cs = [factory, stables_reserve, stables_buffer, ether_buffer, yfi_buyback, yvyfilp_buyback, splitter, guard]
    assert all([c.robo() == robo for c in cs])

    cs.pop()
    cs.append(robo)
    assert all([c.treasury() == treasury for c in cs if c != splitter])
    cs.append(treasury)
    assert all([YCHAD in [c.management(), c.pending_management()] for c in cs])

    cs = [guard, factory]
    assert all([c.operator() == OPS_SAFE for c in cs])
    assert robo.operator() == guard

    print('✔ sanity checks passed')

    bs = ['stables_reserve', 'stables_buffer', 'ether_buffer', 'splitter', 'yfi_buyback', 'yvyfilp_buyback']

    print('\nrobo buckets:')
    for b in robo.buckets():
        s = '???'
        for x in bs:
            if locals()[x] == b:
                s = x
                break
        print(f'  {s}')

    for v in bs[:3]:
        b = locals()[v]
        n = b.num_tokens()
        p = b.total_points()
        print(f'\n{v}:')
        for i in range(n):
            t = Contract(b.tokens(i))
            print(f'  {b.points(t)*100//p}% {t.symbol()}')

    for v in bs[4:]:
        b = locals()[v]
        print(f'\n{v}:')
        t = Contract(b.buyback_token())
        print(f'  100% {t.symbol()}')

    n = splitter.num_buckets()
    p = splitter.total_points()
    print(f'\nsplitter:')
    for i in range(n):
        b = splitter.buckets(i)
        s = '???'
        for x in bs:
            if locals()[x] == b:
                s = x
                break
        print(f'  {splitter.points(b)*100//p}% {s}')
