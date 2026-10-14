"""Validate the current cited-reference inventory without a manuscript build."""

EXPECTED_REFERENCES = 66
EXPECTED_SCHOLARLY = 63
SOURCE_KEYS = {'openroadmacrofiles', 'coreinputfiles', 'scipymilp2023'}
SCHOLARLY_KINDS = {'article', 'inproceedings', 'incollection'}


def validate_reference_inventory(references, verification):
    reference_keys = [row['key'] for row in references]
    verification_keys = [row['key'] for row in verification]
    assert len(references) == EXPECTED_REFERENCES == len(set(reference_keys))
    assert len(verification) == EXPECTED_REFERENCES == len(set(verification_keys))
    assert set(reference_keys) == set(verification_keys)

    scholarly = [row for row in references if row['kind'] in SCHOLARLY_KINDS]
    sources = [row for row in references if row['kind'] == 'misc']
    assert len(scholarly) == EXPECTED_SCHOLARLY
    assert {row['key'] for row in sources} == SOURCE_KEYS
    assert len(scholarly) + len(sources) == EXPECTED_REFERENCES
    assert all(row['author'] and row['title'] and row['source'].startswith('http')
               and row['basis'] and row['claim'] for row in references)
    assert all(row['venue'] and row['year'].isdigit() for row in scholarly)
    assert all(not row['year'] or row['year'].isdigit() for row in sources)

    dois = [row['doi'].lower() for row in references if row['doi']]
    assert len(dois) == len(set(dois))
    assert all(int(row['citation_count']) > 0 and row['manuscript_lines']
               and row['metadata_status'] and row['identifier_status']
               and row['citation_context_status']
               and row['scholarly_source'].startswith('http')
               and row['supported_clause'] for row in verification)
