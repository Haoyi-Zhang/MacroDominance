"""Bounded exact pilot of the HPWL clipping identity; no numerical tolerances."""
from itertools import combinations_with_replacement, product
import json, resource, time
from pathlib import Path


def span(a, b):
    return max(a[1], b[1]) - min(a[0], b[0])


def normal(interval, envelope):
    lo, hi = interval
    a, b = envelope
    clipped = (min(b, max(a, lo)), min(b, max(a, hi)))
    offset = max(a-lo, 0) + max(hi-b, 0)
    return clipped, offset


def main():
    cpu = time.process_time()
    wall = time.perf_counter()
    intervals = list(combinations_with_replacement(range(-4, 5), 2))
    checks = 0
    for internal, envelope in product(intervals, repeat=2):
        canonical, offset = normal(internal, envelope)
        for outside in intervals:
            if envelope[0] <= outside[0] <= outside[1] <= envelope[1]:
                assert span(internal, outside) == offset + span(canonical, outside)
                checks += 1
    # Normalized response differences determine exactly the clipped interval
    # even on the integer grid. Absolute scores also include the offset.
    pairs = 0
    for envelope in intervals:
        coordinates = list(range(envelope[0], envelope[1]+1))
        response_to_key = {}
        for internal in intervals:
            key, offset = normal(internal, envelope)
            response = tuple(span(internal, (z,z)) for z in coordinates)
            shape = tuple(v-response[0] for v in response)
            if shape in response_to_key:
                assert response_to_key[shape] == key
            response_to_key[shape] = key
            pairs += 1
    # Counterexample: canonical intervals are NOT replacement geometries.
    left, right = (0, 0), (10, 10)
    ln, lc = normal(left, right)
    rn, rc = normal(right, left)
    true = span(left, right)
    naive = lc + rc + span(ln, rn)
    assert (true, naive) == (10, 30)
    # Independent marginal minima can be mutually unattainable.
    options = ((0, 2), (2, 0))
    real_min = min(sum(abs(x) for x in p) for p in options)
    marginal_min = sum(min(abs(p[i]) for p in options) for i in range(2))
    assert (real_min, marginal_min) == (2, 0)
    report = dict(identity_checks=checks, response_profiles=pairs,
                  naive_merge=dict(exact=true, incorrect=naive),
                  correlation=dict(exact=real_min, marginal=marginal_min),
                  cpu_seconds=time.process_time()-cpu,
                  wall_seconds=time.perf_counter()-wall,
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  status='passed_finite_checks_not_a_general_proof')
    out = Path(__file__).resolve().parents[1]/'results'/'pilot.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
