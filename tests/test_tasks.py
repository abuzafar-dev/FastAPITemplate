def test_root(client):
    assert client.get('/').status_code == 200


def test_create_and_list(client):
    response = client.post('/tasks/', json={'title': 'FastAPI o\'rganish'})
    assert response.status_code == 201
    assert response.json()['is_done'] is False

    response = client.get('/tasks/')
    assert len(response.json()) == 1


def test_empty_title(client):
    response = client.post('/tasks/', json={'title': ''})
    assert response.status_code == 422


def test_update(client):
    task_id = client.post('/tasks/', json={'title': 'Dars'}).json()['id']
    response = client.patch(f'/tasks/{task_id}', json={'is_done': True})
    assert response.json()['is_done'] is True
    assert response.json()['title'] == 'Dars'


def test_filter(client):
    client.post('/tasks/', json={'title': 'Bir'})
    task_id = client.post('/tasks/', json={'title': 'Ikki'}).json()['id']
    client.patch(f'/tasks/{task_id}', json={'is_done': True})
    response = client.get('/tasks/?is_done=true')
    assert [task['title'] for task in response.json()] == ['Ikki']


def test_delete(client):
    task_id = client.post('/tasks/', json={'title': 'Dars'}).json()['id']
    assert client.delete(f'/tasks/{task_id}').status_code == 204
    assert client.get(f'/tasks/{task_id}').status_code == 404
