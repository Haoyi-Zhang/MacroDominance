"""Exact constant-net preprocessing, a null baseline rather than a new contribution.

A net is removed only when both global extrema on both axes are fixed across
all original portfolio combinations. Producer/replay derive this separately.
"""
import copy
import time
from producer import Model, solve
from checker import Replay, verify, need, enc


def solve_reduced(data, seconds=30):
    start = time.perf_counter()
    cpu = time.process_time()
    model = Model(data)
    removed = []
    constant = 0
    for net, owners in sorted(model.owners.items()):
        spans = []
        for li, ui in ((0, 1), (2, 3)):
            rs = [[c[net] for c in model.leaves[r]] for r in sorted(owners)]
            amin = min(min(b[li] for b in cc) for cc in rs)
            amax = min(max(b[li] for b in cc) for cc in rs)
            bmin = max(min(b[ui] for b in cc) for cc in rs)
            bmax = max(max(b[ui] for b in cc) for cc in rs)
            if amin != amax or bmin != bmax:
                break
            spans.append(bmax - amin)
        if len(spans) == 2:
            removed.append(net)
            constant += model.weights[net] * sum(spans)
    reduced = copy.deepcopy(data)
    for region in reduced['regions']:
        for macro in region['macros']:
            macro['pins'] = [p for p in macro['pins'] if p['net'] not in removed]
    reduced['weights'] = {e: w for e, w in reduced['weights'].items() if e not in removed}
    cert, stats = solve(reduced, 'raw', seconds=max(1e-9, seconds - (time.perf_counter() - start)))
    packet = {'method': 'constant_raw', 'removed': removed, 'constant': constant,
              'reduced_certificate': cert, 'optimum': cert['optimum'] + constant,
              'placement': cert['placement']}
    stats.update(method='constant_raw', removed_net_count=len(removed),
                 constant_net_hpwl=constant, cpu_seconds=time.process_time() - cpu,
                 wall_seconds=time.perf_counter() - start)
    return packet, stats


def verify_reduced(data, packet, seconds=30):
    start = time.perf_counter()
    cpu = time.process_time()
    need(type(packet) is dict and set(packet) == {'method', 'removed', 'constant', 'reduced_certificate', 'optimum', 'placement'}, 'baseline fields')
    need(packet['method'] == 'constant_raw', 'baseline mode')
    model = Replay(data)
    fixed = {}
    for net, regions in sorted(model.netregions.items()):
        extrema = []
        for axis in (0, 1):
            lower_ranges = []
            upper_ranges = []
            for r in sorted(regions):
                local_lows = []
                local_highs = []
                for alternative in model.points[r]:
                    values = sorted(p[axis] for p in alternative[net])
                    local_lows.append(values[0])
                    local_highs.append(values[-1])
                lower_ranges.append((min(local_lows), max(local_lows)))
                upper_ranges.append((min(local_highs), max(local_highs)))
            low = (min(x[0] for x in lower_ranges), min(x[1] for x in lower_ranges))
            high = (max(x[0] for x in upper_ranges), max(x[1] for x in upper_ranges))
            if low[0] != low[1] or high[0] != high[1]:
                break
            extrema.append(high[1] - low[0])
        if len(extrema) == 2:
            fixed[net] = model.weights[net] * sum(extrema)
    need(enc(packet['removed']) == enc(sorted(fixed)), 'baseline removed nets')
    need(type(packet['constant']) is int and packet['constant'] == sum(fixed.values()), 'baseline offset')
    reduced = copy.deepcopy(data)
    for region in reduced['regions']:
        for macro in region['macros']:
            macro['pins'] = [p for p in macro['pins'] if p['net'] not in fixed]
    for net in fixed:
        del reduced['weights'][net]
    cert = packet['reduced_certificate']
    need(type(cert) is dict, 'baseline reduced certificate type')
    need(cert.get('method') == 'raw', 'baseline reduced mode')
    replay = verify(reduced, cert, seconds=max(1e-9, seconds - (time.perf_counter() - start)))
    need(type(packet['optimum']) is int and packet['optimum'] == replay['optimum'] + sum(fixed.values()), 'baseline optimum')
    need(enc(packet['placement']) == enc(cert['placement']), 'baseline placement')
    witness = tuple((model.names.index(r), c) for r, c in packet['placement'])
    original_row = model.evaluate('', witness, 'raw')
    need(original_row['cost'] == packet['optimum'], 'baseline original geometry')
    need(time.perf_counter() - start <= seconds, 'baseline replay time')
    return {'accepted': True, 'optimum': packet['optimum'],
            'replayed_transitions': replay['replayed_transitions'],
            'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - start}
