def test_page_renders(client):
    response = client.get('/pages/tasks')
    assert response.status_code == 200
    assert "Hozircha vazifa yo'q" in response.text


def test_form_creates_task_and_redirects(client):
    response = client.post('/pages/tasks', data={'title': 'Formadan'}, follow_redirects=False)
    assert response.status_code == 303
    assert 'Formadan' in client.get('/pages/tasks').text
    assert client.get('/tasks/').json()[0]['title'] == 'Formadan'


def test_form_empty_title_rejected(client):
    assert client.post('/pages/tasks', data={'title': ''}).status_code == 422


def test_toggle(client):
    client.post('/pages/tasks', data={'title': 'A'})
    task_id = client.get('/tasks/').json()[0]['id']
    client.post(f'/pages/tasks/{task_id}/toggle')
    assert client.get(f'/tasks/{task_id}').json()['is_done'] is True


def test_static(client):
    assert client.get('/static/style.css').status_code == 200
