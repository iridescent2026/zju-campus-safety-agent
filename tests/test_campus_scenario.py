import json
import httpx
from test_device_workflow import system, login, order_action
from gis import workflow_language


def test_campus_context_is_conditional_and_scoped_to_drainage(system, monkeypatch):
    monkeypatch.setenv('WORKFLOW_MODEL_ENABLED', '0')
    _, client = system
    status = client.post('/factory/workflow/chat', json={'query': 'Ｂ０５状态'}).json()
    impact = client.post('/factory/workflow/chat', json={'query': '排水泵坏了有什么影响'}).json()
    assert status['intent'] == 'status' and impact['intent'] == 'impact'
    assert status['answer'] != impact['answer']
    assert '校园服务核查（设计场景）' in impact['answer']
    assert '备用泵' in impact['answer']
    assert impact['case']['campusService']['status'] == 'design_assumption'
    assert client.get('/factory/workflow/case/B-01').json()['campusService'] is None
    assert not client.get('/factory/analysis').json()['orders']
    edges = client.get('/factory/analysis').json()['graph']['edges']
    assert all(not e['verified'] and e['condition'] for e in edges)
    power = next(e for e in edges if e['relationKind'] == 'power')
    assert (power['source'], power['target'], power['direction']) == ('B-01', 'B-05', 'forward')


def test_grounded_model_receives_design_context_only_for_service_questions(system, monkeypatch):
    _, client = system
    captured = []
    monkeypatch.setenv('WORKFLOW_MODEL_ENABLED', '1')
    monkeypatch.setenv('WORKFLOW_MODEL_PROVIDER', 'aliyun')
    monkeypatch.setenv('WORKFLOW_MODEL_API_KEY', 'fixture-not-a-live-key')
    monkeypatch.setenv('WORKFLOW_TEMPLATE_FIRST', '1')
    def post(url, **kwargs):
        evidence = json.loads(kwargs['json']['messages'][-1]['content'])['backendEvidence']
        captured.append(evidence)
        text = '可能影响：设计场景中的排水保障需核对备用能力与实际管路。' if evidence['intents'] == ['impact'] else '当前状态：按后台有效观测核对，工程适用规则需复核。'
        return httpx.Response(200, json={'choices': [{'message': {'content': text}}]}, request=httpx.Request('POST', url))
    monkeypatch.setattr(workflow_language.httpx, 'post', post)
    headers = login(client, 'observer')
    for query in ['B05状态', 'B05坏了有什么影响']:
        response = client.post('/factory/workflow/chat', headers=headers, json={'query': query, 'answerMode': 'grounded'})
        assert response.status_code == 200 and response.json()['engine'] == 'aliyun-grounded-chat'
    assert 'campusService' not in captured[0]
    assert captured[1]['campusService']['status'] == 'design_assumption'
    assert 'measurements' not in captured[1]['observation']


def test_campus_demonstration_requires_confirmation_and_independent_review(system, monkeypatch):
    monkeypatch.setenv('WORKFLOW_MODEL_ENABLED', '0')
    _, client = system
    safety, maintenance, reviewer = [login(client, role) for role in ['safety', 'maintenance', 'reviewer']]
    response = client.post('/factory/workflow/chat', headers=safety, json={'query': '为B05安排核查任务', 'answerMode': 'template'})
    assert response.status_code == 200 and response.json()['intent'] == 'draft'
    draft = response.json()['draft']
    assert not client.get('/factory/analysis').json()['orders']
    confirmed = client.post('/factory/workflow/drafts/' + draft['id'] + '/confirm', headers=safety, json={'assignee': 'demo-maintenance'})
    assert confirmed.status_code == 200, confirmed.text
    order = confirmed.json()['order']
    started = order_action(client, order, 'start', maintenance)
    assert started.status_code == 200, started.text
    submitted = order_action(client, started.json(), 'complete', maintenance, note='演示核查：记录仪表及备用泵检查，提交复核')
    assert submitted.status_code == 200, submitted.text
    pending = submitted.json()
    assert order_action(client, pending, 'approve', maintenance, note='本人关闭').status_code == 403
    closed = order_action(client, pending, 'approve', reviewer, note='独立账号复核核查记录与凭证')
    assert closed.status_code == 200 and closed.json()['status'] == 'closed', closed.text
