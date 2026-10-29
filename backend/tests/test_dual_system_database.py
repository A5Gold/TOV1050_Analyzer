"""Identity regressions use the isolated test database, never the product DB."""
import pytest
from fastapi.testclient import TestClient

from app.core.line_registry import LINE_CATALOG, normalize_context
from app.core.database import (
    DatabaseManager, get_line_counts, get_repeated_record_section_counts,
    query_repeated_records, save_repeated_records_batch,
)


@pytest.fixture
def test_client(tmp_path, monkeypatch):
    monkeypatch.setenv('TOV640_TEST_DB_PATH', str(tmp_path / 'identity.db'))
    DatabaseManager.reset_instance()
    db = DatabaseManager(str(tmp_path / 'identity.db'))
    from app.main import app
    with TestClient(app) as client:
        yield client
    db.close()
    DatabaseManager.reset_instance()


SCOPES = [(line, branch['branch'], direction)
          for line, item in LINE_CATALOG.items()
          for branch in item['branches']
          for direction in item['directions']]


@pytest.mark.parametrize('line,branch,direction', SCOPES)
def test_every_line_branch_direction_can_save(test_client, line, branch, direction):
    identity = normalize_context(line, branch=branch, direction=direction)
    response = test_client.post('/api/database/repeated-records', json={
        'line': line, 'track': direction, 'session': branch, 'date_str': '20261029',
        'repeated_exceptions': [{'id': f'{line}-{branch}-{direction}',
            'Line': line, 'Track': direction, 'Section': identity.legacy_session,
            'exception type': 'Low Height', 'level': 'L1', 'FromM': 1, 'ToM': 2}],
    })
    assert response.status_code == 200, response.text
    response = test_client.get('/api/database/repeated-records', params={
        'line': line, 'track': direction, 'session': branch,
    })
    assert response.status_code == 200, response.text
    assert response.json()['total'] == 1
    assert response.json()['records'][0]['line'] == line


@pytest.mark.parametrize('row,session', [
    ({'line': 'AEL', 'Section': 'Mainline'}, 'Mainline'),
    ({'line': 'EAL', 'Track': 'DT', 'Section': 'Mainline'}, 'Mainline'),
    ({'line': 'LMC', 'Section': 'LMC'}, 'Mainline'),
    ({'line': 'EAL', 'Section': 'LMC'}, 'Mainline'),
])
def test_mismatched_identity_rejected_before_write(test_client, row, session):
    response = test_client.post('/api/database/repeated-records', json={
        'line': 'EAL', 'track': 'UP', 'session': session, 'date_str': '20261029',
        'repeated_exceptions': [{'id': 'conflicting', 'FromM': 1, 'ToM': 2, **row}],
    })
    assert response.status_code == 422
    assert test_client.get('/api/database/repeated-records').json()['total'] == 0


def test_missing_identity_is_not_guessed(test_client):
    for line, track, section in [('UNKNOWN', 'UP', 'Mainline'), ('AEL', '', 'Mainline'), ('EAL', 'UP', '')]:
        response = test_client.post('/api/database/repeated-records', json={
            'line': line, 'track': track, 'date_str': '20261029',
            'repeated_exceptions': [{'id': 'missing', 'Section': section}],
        })
        assert response.status_code == 422


def test_legacy_branch_aliases_and_counts_remain_separate(test_client):
    db = DatabaseManager()
    with db.get_connection() as conn:
        for line, section, session in [('EAL', 'Mainline', 'Mainline'), ('LMC', '', 'Mainline'),
                                      ('TKL', 'Mainline', 'Mainline'), ('TKS', '', 'Mainline'),
                                      ('DRL', 'UT', 'Mainline'), ('DRL', 'PL', 'PL')]:
            save_repeated_records_batch(conn, line, 'UT', '20261029', [
                {'id': f'{line}-{section}', 'Section': section, 'FromM': 1, 'ToM': 2}], session=session)
        assert get_line_counts(conn)['EAL'] == 2
        assert get_line_counts(conn)['TKL'] == 2
        assert len(get_line_counts(conn)) == 9
        assert get_repeated_record_section_counts(conn, {'line': 'DRL'})['pl'] == 1
        assert get_repeated_record_section_counts(conn, {'line': 'TKL'})['tks'] == 1
        assert len(query_repeated_records(conn, {'line': 'EAL', 'section': 'LMC', 'track': 'UP'})) == 1
        assert len(query_repeated_records(conn, {'line': 'TKL', 'session': 'TKS'})) == 1


@pytest.mark.parametrize('section', ['UT', 'Shared station span'])
def test_recurrence_matches_same_branch_only(test_client, section):
    def save(branch, identifier):
        response = test_client.post('/api/database/repeated-records', json={
            'line': 'DRL', 'track': 'UT', 'session': branch, 'date_str': '20260901',
            'repeated_exceptions': [{'id': identifier, 'Section': section,
                'exception type': 'Stagger Left', 'level': 'L3',
                'FromM': 100, 'ToM': 120, 'maxLocation': 110}],
        })
        assert response.status_code == 200, response.text
    save('UT', 'mainline-target')
    current = {'id': 'current', 'section': section, 'exception_type': 'Stagger Right',
               'level': 'L3', 'max_location': 110, 'from_m': 100, 'to_m': 120,
               'task_run_date': '20261001'}
    def check(branch):
        response = test_client.post('/api/database/repeated-records/check-1-year', json={
            'line': 'DRL', 'track': 'UT', 'session': branch, 'current_date': '20261001',
            'exceptions': [current],
        })
        assert response.status_code == 200, response.text
        return response.json()
    assert check('UT')['auto_verified_count'] == 1
    if section == 'Shared station span':
        assert check('PL')['auto_verified_count'] == 0


def test_import_normalizes_duplicate_display_headers_and_drl_alias(test_client):
    response = test_client.post('/api/database/repeated-records/import', json={
        'line': 'DRL', 'track': 'UT', 'session': 'UT', 'date_str': '20261029',
        'records': [{'ID': 'import-drl', 'Line': 'DRL', 'Track': 'UT',
                     'Section': 'UT', 'Session': 'UT', 'FromM': 1, 'ToM': 2}],
    })
    assert response.status_code == 200, response.text
    data = test_client.get('/api/database/repeated-records', params={
        'line': 'DRL', 'session': 'Mainline',
    }).json()
    assert data['total'] == 1
    assert data['records'][0]['session'] == 'Mainline'
    assert data['records'][0]['section'] == 'Mainline'
    response = test_client.post('/api/database/repeated-records/import', json={
        'line': 'EAL', 'track': 'UP', 'session': 'LMC', 'date_str': '20261029',
        'records': [{'ID': 'import-lmc', 'line': 'EAL', 'Line': 'LMC',
                     'Section': 'LMC', 'FromM': 1, 'ToM': 2}],
    })
    assert response.status_code == 200, response.text
    data = test_client.get('/api/database/repeated-records', params={'line': 'EAL', 'session': 'LMC'}).json()
    assert data['total'] == 1
    assert data['records'][0]['line'] == 'EAL'


def test_geographical_section_is_visible_under_its_branch(test_client):
    response = test_client.post('/api/database/repeated-records', json={
        'line': 'DRL', 'track': 'UT', 'session': 'PL', 'date_str': '20261029',
        'repeated_exceptions': [{'id': 'geographical-pl', 'Section': 'Shared station span'}],
    })
    assert response.status_code == 200, response.text
    response = test_client.get('/api/database/repeated-records', params={'line': 'DRL', 'session': 'PL'})
    assert response.status_code == 200, response.text
    assert response.json()['total'] == 1
    assert response.json()['branch_counts']['PL'] == 1
    assert response.json()['records'][0]['section'] == 'Shared station span'
    assert test_client.get('/api/database/repeated-records', params={'line': 'UNKNOWN'}).status_code == 422
