from ape import project, Contract
from json import load

YCHAD = '0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52'
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
    guard = project.Guard.at(d['GUARD'])

    cs = [factory, stables_reserve, stables_buffer, ether_buffer, yfi_buyback, yvyfilp_buyback, splitter, guard]
    assert all([c.robo() == robo for c in cs])

    assert cs.pop().management() == YCHAD # guard management is immutable
    cs.extend([treasury, robo])
    assert all([c.pending_management() == YCHAD for c in cs])

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
