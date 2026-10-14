"""The live citation inventory must keep its count and type-aware schema."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from reference_inventory import validate_reference_inventory


def rejected(references, verification):
    try:
        validate_reference_inventory(references, verification)
    except AssertionError:
        return
    raise AssertionError('invalid reference inventory was accepted')


def main():
    with (ROOT / 'reference-audit.csv').open(newline='') as handle:
        references = list(csv.DictReader(handle))
    with (ROOT / 'reference-verification.csv').open(newline='') as handle:
        verification = list(csv.DictReader(handle))
    validate_reference_inventory(references, verification)

    rejected(references[:-1], verification)
    rejected(references, verification[:-1])
    duplicate = [dict(row) for row in references]
    duplicate[-1]['key'] = duplicate[0]['key']
    rejected(duplicate, verification)
    wrong_verification_key = [dict(row) for row in verification]
    wrong_verification_key[-1]['key'] = 'not-a-cited-key'
    rejected(references, wrong_verification_key)

    unknown_kind = [dict(row) for row in references]
    unknown_kind[0]['kind'] = 'unknown'
    rejected(unknown_kind, verification)

    missing_venue = [dict(row) for row in references]
    next(row for row in missing_venue if row['kind'] == 'article')['venue'] = ''
    rejected(missing_venue, verification)
    missing_year = [dict(row) for row in references]
    next(row for row in missing_year if row['kind'] == 'inproceedings')['year'] = ''
    rejected(missing_year, verification)
    missing_source = [dict(row) for row in references]
    next(row for row in missing_source if row['kind'] == 'misc')['source'] = ''
    rejected(missing_source, verification)

    bad_verification = [dict(row) for row in verification]
    bad_verification[0]['citation_count'] = '0'
    rejected(references, bad_verification)
    print('reference inventory: 66 rows and type-aware count/schema regressions passed')


if __name__ == '__main__':
    main()
