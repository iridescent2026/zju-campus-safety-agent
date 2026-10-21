import json
import httpx
import pytest
from test_device_workflow import system, login
from gis import workflow_language as language


@pytest.fixture
def deepseek(monkeypatch, tmp_path):
    for name, value in {
        'WORKFLOW_MODEL_PROVIDER': 'deepseek', 'WORKFLOW_MODEL_ENABLED': '1',
        'WORKFLOW_MODEL_NAME': 'deepseek-flash', 'DEEPSEEK_API_KEY': 'fixture-only',
        'WORKFLOW_RESPONSE_POLICY': 'classified-template', 'WORKFLOW_TEMPLATE_FIRST': '1',
        'WORKFLOW_QUOTA_DB_PATH': str(tmp_path / 'quota.db'),
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv('WORKFLOW_MODEL_BASE_URL', raising=False)
    calls = []
    def post(url, **kwargs):
        assert url == 'https://api.deepseek.com/chat/completions'
        payload = kwargs['json']; calls.append(payload)
        assert payload['thinking'] == {'type': 'disabled'}
        if 'response_format' in payload:
            query = payload['messages'][-1]['content']
            if '坏了' in query:
                decision = {'matchesTemplate': True, 'intents': ['impact']}
            elif '派单' in query:
                decision = {'matchesTemplate': True, 'intents': ['draft', 'status']}
            elif '是什么' in query or '解释' in query:
                decision = {'matchesTemplate': False, 'intents': ['general']}
            else:
                decision = {'matchesTemplate': True, 'intents': ['status']}
            text = json.dumps(decision)
        else:
            text = '这是通用知识回答，没有查询现场读数，也没有创建工单。'
        return httpx.Response(200, json={'choices': [{'message': {'content': text}}]}, request=httpx.Request('POST', url))
    monkeypatch.setattr(language.httpx, 'post', post)
    return calls


@pytest.mark.parametrize('query', ['B05状态', 'b-05 STATUS', 'Ｂ－０５\n状态', 'b 05 状态', 'b—05状态'])
def test_model_classifies_then_template_answers_normalized_id(system, deepseek, query):
    _, client = system
    result = client.post('/factory/workflow/chat', headers=login(client, 'observer'), json={'query': query, 'answerMode': 'grounded', 'history': [{'role': 'assistant', 'content': '内部观测和人员位置不应发送给模型'}]}).json()
    assert result['success'] and result['entityId'] == 'B-05'
    assert result['engine'] == 'deepseek-classified-template'
    assert result['intent'] == 'status' and '当前状态' in result['answer']
    assert len(deepseek) == 1 and deepseek[0]['response_format'] == {'type': 'json_object'}
    assert result['tool_results'][0]['output']['matchesTemplate'] is True
    assert not client.get('/factory/analysis').json()['orders']


def test_status_and_impact_use_distinct_templates(system, deepseek):
    _, client = system; headers = login(client, 'observer')
    status, impact = [client.post('/factory/workflow/chat', headers=headers, json={'query': q, 'answerMode': 'grounded'}).json() for q in ['B05状态', 'B05坏了有什么影响']]
    assert status['intent'] == 'status' and impact['intent'] == 'impact'
    assert status['answer'] != impact['answer']
    assert '当前状态' not in impact['answer'] and '校园服务核查' in impact['answer']
    assert len(deepseek) == 2  # Classification only, no model-generated answer.


def test_api_defaults_to_classification_unless_shortcut_is_explicit(system, deepseek):
    _, client = system
    result = client.post('/factory/workflow/chat', headers=login(client, 'observer'), json={'query': 'B05状态'}).json()
    assert result['engine'] == 'deepseek-classified-template' and len(deepseek) == 1


@pytest.mark.parametrize('query', ['排水泵是什么', '压力是什么', '解释校园雨污分流'])
def test_non_template_uses_model_answer_without_device_snapshot(system, deepseek, query):
    _, client = system
    result = client.post('/factory/workflow/chat', headers=login(client, 'observer'), json={'query': query, 'answerMode': 'grounded', 'history': [{'role': 'assistant', 'content': '内部观测和人员位置不应发送给模型'}]}).json()
    assert result['success'] and result['intent'] == 'general'
    assert result['engine'] == 'deepseek-general-chat' and not result.get('case')
    assert len(deepseek) == 2 and 'response_format' not in deepseek[1]
    assert len(deepseek[1]['messages']) == 2
    assert '内部观测' not in json.dumps(deepseek[1]['messages'], ensure_ascii=False)
    assert not result.get('draft') and not client.get('/factory/analysis').json()['orders']


def test_shortcuts_skip_classification_and_negated_drafts_cannot_create_tasks(system, deepseek):
    _, client = system; headers = login(client, 'safety')
    shortcut = client.post('/factory/workflow/chat', headers=headers, json={'query': 'B05状态', 'answerMode': 'template'}).json()
    assert shortcut['success'] and deepseek == []
    result = client.post('/factory/workflow/chat', headers=headers, json={'query': 'B05状态，不要派单', 'answerMode': 'grounded'}).json()
    assert result['intent'] == 'status' and not result.get('draft')
    assert not client.get('/factory/analysis').json()['orders']


def test_classifier_failure_is_visible_and_uses_local_status(system, deepseek, monkeypatch):
    _, client = system
    def fail(*args, **kwargs):
        raise httpx.ConnectError('fixture offline')
    monkeypatch.setattr(language.httpx, 'post', fail)
    result = client.post('/factory/workflow/chat', headers=login(client, 'observer'), json={'query': 'B05状态', 'answerMode': 'grounded'}).json()
    assert result['intent'] == 'status' and result['engine'] == 'rule-tool-orchestrator'
    assert result['tool_results'][0]['status'] == 'fallback'
    assert '当前状态' in result['answer']


def test_model_cannot_invent_a_draft_request(system, deepseek, monkeypatch):
    _, client = system
    def post(url, **kwargs):
        text = json.dumps({'matchesTemplate': True, 'intents': ['draft']}) if 'response_format' in kwargs['json'] else '你好，请问需要什么帮助？'
        return httpx.Response(200, json={'choices': [{'message': {'content': text}}]}, request=httpx.Request('POST', url))
    monkeypatch.setattr(language.httpx, 'post', post)
    result = client.post('/factory/workflow/chat', headers=login(client, 'safety'), json={'query': '你好', 'answerMode': 'grounded'}).json()
    assert result['intent'] == 'general' and not result.get('draft')
    assert not client.get('/factory/analysis').json()['orders']


def test_local_key_is_provider_bound_and_deepseek_environment_wins(monkeypatch):
    from gis import local_model_settings
    monkeypatch.setattr(local_model_settings, 'local_model_settings', lambda: {'provider': 'deepseek', 'key': 'local-fixture', 'model': 'deepseek-flash', 'enabled': True, 'responsePolicy': 'classified-template'})
    for name in ['WORKFLOW_MODEL_API_KEY', 'DEEPSEEK_API_KEY', 'DASHSCOPE_API_KEY', 'WORKFLOW_MODEL_ENABLED', 'WORKFLOW_MODEL_NAME', 'WORKFLOW_RESPONSE_POLICY']:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('WORKFLOW_MODEL_PROVIDER', 'deepseek')
    assert language.model_config()['key'] == 'local-fixture' and language.model_enabled()
    monkeypatch.setenv('WORKFLOW_MODEL_PROVIDER', 'aliyun')
    assert not language.model_config()['key']  # Never send the DS key to Aliyun.
    monkeypatch.setenv('WORKFLOW_MODEL_PROVIDER', 'deepseek')
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'environment-fixture')
    assert language.model_config()['key'] == 'environment-fixture'
