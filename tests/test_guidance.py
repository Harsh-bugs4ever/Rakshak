import base64
import pytest
from src.agents import model
from src.handlers.ai import handler
from tests.test_ai_handler import call
from tests.conftest import body_of, make_event

@pytest.mark.usefixtures('dynamodb')
def test_critical_message_overrides_context():
    result = body_of(call(payload={'message':'not breathing', 'context':{'scenario':'breathing_injured'}}))
    assert result['ok']
    data = result['data']
    assert data['protocol_id'] == 'not_breathing'
    assert data['steps']
    assert data['session_id']
    assert data['disclaimer']


def test_unknown_question_does_not_invent_medical_advice():
    data = body_of(call(payload={'message':'which medicine should I give?'}))['data']
    assert data['steps'] == []
    assert '112' in data['reply']


@pytest.mark.usefixtures('dynamodb')
def test_aftermath_cites_answer():
    data = body_of(call(path='/ai/aftermath', payload={'message':'What is MLC?'}))['data']
    assert data['citations'][0]['faq_id']
    assert 'MLC' in data['reply']


@pytest.mark.usefixtures('dynamodb')
def test_model_failure_falls_back(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama')
    def fail(*args):
        raise TimeoutError()
    monkeypatch.setattr(model,'select_record',fail)
    result = body_of(call(path='/ai/aftermath', payload={'message':'What is MLC?'}))
    assert result['ok']
    assert result['meta']['source'] == 'reference-fallback'
    assert result['data']['citations']


@pytest.mark.usefixtures('dynamodb')
def test_model_cannot_fabricate_citation(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama')
    monkeypatch.setattr(model,'select_record',lambda *args:'invented-faq')
    data = body_of(call(path='/ai/aftermath', payload={'message':'What is MLC?'}))['data']
    assert not data['citations']
    assert 'could not find' in data['reply']


def test_session_and_cors():
    response = call(payload={'message':'hi','session_id':'abc-123'})
    assert body_of(response)['data']['session_id'] == 'abc-123'
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    assert call(method='OPTIONS')['statusCode'] == 204


def test_base64_body():
    event = make_event(path='/ai/emergency',method='POST',body=base64.b64encode(b'{"message":"hi"}').decode())
    event['isBase64Encoded'] = True
    assert handler(event,None)['statusCode'] == 200

def test_ai_response_is_not_publicly_cacheable():
    response = call(payload={'message': 'hi'})
    assert response['headers']['Cache-Control'] == 'no-store'


@pytest.mark.usefixtures('dynamodb')
def test_model_selection_returns_only_retrieved_text(monkeypatch, seed_data):
    monkeypatch.setenv('AI_PROVIDER', 'ollama')
    selected_id = []
    def select(builder, message, candidates):
        selected_id.append(candidates[0]['record_id'])
        return candidates[0]['record_id']
    monkeypatch.setattr(model, 'select_record', select)
    response = body_of(call(path='/ai/aftermath', payload={'message': 'What is MLC?'}))
    record = next(faq for faq in seed_data['faqs'] if faq['faq_id'] == selected_id[0])
    assert response['data']['reply'] == record['answer']
    assert response['meta']['source'] == 'strands+reference'


def test_strands_uses_explicit_local_model(monkeypatch):
    pytest.importorskip('strands')
    from src.agents.aftermath_agent import build_agent
    monkeypatch.setenv('OLLAMA_MODEL_ID', 'test-local-model')
    agent = build_agent()
    assert type(agent.model).__name__ == 'OllamaModel'
