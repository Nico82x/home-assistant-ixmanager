"""Offline tests: no account, tokens, device IDs or cloud requests required."""
import asyncio
from functools import partial
import importlib
import json
from pathlib import Path
import sys
import types
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError
from graphql import parse

ROOT = Path(__file__).resolve().parents[1]
# Load cloud/model modules independently of Home Assistant startup.
package = types.ModuleType('ixmanager_test')
package.__path__ = [str(ROOT / 'custom_components/ixmanager')]
sys.modules['ixmanager_test'] = package
api_module = importlib.import_module('ixmanager_test.api')
models = importlib.import_module('ixmanager_test.models')
queries = importlib.import_module('ixmanager_test.queries')
IxmanagerApi = api_module.IxmanagerApi


def fixture(name):
    return json.loads((Path(__file__).parent / 'fixtures' / (name+'.json')).read_text())

async def executor(fn):
    return fn()

class Response:
    def __init__(self, body, status=200):
        self.body, self.status = body, status
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def json(self): return self.body

class Session:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.requests = []
    def post(self, url, **kwargs):
        self.requests.append(kwargs)
        return next(self.responses)

def client(session=None):
    api = IxmanagerApi(session, executor, 'test-user', 'test-password')
    api._client = Mock()
    return api


def test_synthetic_metadata_and_reordered_values():
    raw = fixture('get_device')
    device = models.parse_device(raw)
    assert len(device.parameters) == 15
    assert device.parameters['operatingValues:poolTempWithSettings'].state() == 24.0
    assert device.parameters['operatingValues:targetpH'].state() == 7.1
    raw['liveDeviceData']['operatingValues'].reverse()
    assert models.parse_device(raw).parameters == device.parameters
    assert all('service' not in key for key in device.parameters)
    assert not any('protectionReset' in key for key in device.parameters)

@pytest.mark.parametrize('name', ['live_before', 'live_after'])
def test_anonymous_live_response_rejected(name):
    with pytest.raises(models.SchemaError): models.parse_device(fixture(name))

@pytest.mark.parametrize('value', [None, '', 'NaN', 'Infinity', 'n/a'])
def test_bad_numeric_value_is_unknown(value):
    raw = fixture('get_device')
    raw['liveDeviceData']['operatingValues'][0]['value'] = value
    assert models.parse_device(raw).parameters['operatingValues:poolTempWithSettings'].state() is None

def test_changed_target_and_missing_parameter():
    raw = fixture('get_device')
    # Synthetic anonymous samples are used only to verify historical values,
    # never to perform the integration's runtime mapping.
    for name in ['live_before', 'live_after']:
        value = fixture(name)['liveDeviceData']['operatingValues'][0]
        raw['liveDeviceData']['operatingValues'][0].update(value)
        p = models.parse_device(raw).parameters['operatingValues:poolTempWithSettings']
        assert p.state(desired=True) == float(value['desiredValue'])
    raw['liveDeviceData']['operatingValues'].pop(0)
    assert 'operatingValues:poolTempWithSettings' not in models.parse_device(raw).parameters

def test_queries_are_valid_read_only_graphql():
    for query in (queries.DISCOVER, queries.GET_DEVICE, queries.LIVE_DATA):
        document = parse(query)
        assert document.definitions[0].operation.value == 'query'
    assert 'name label type value' in queries.LIVE_DATA
    assert 'serviceSequences' not in queries.LIVE_DATA

@pytest.mark.asyncio
async def test_srp_login_and_cached_token():
    api = client()
    api._client.initiate_auth.return_value = {'ChallengeName':'PASSWORD_VERIFIER',
        'ChallengeParameters':{},'Session':'test-session'}
    api._client.respond_to_auth_challenge.return_value = {'AuthenticationResult':{
        'AccessToken':'access', 'RefreshToken':'refresh', 'ExpiresIn':3600}}
    with patch.object(api_module,'AWSSRP') as srp:
        srp.return_value.get_auth_params.return_value = {'USERNAME':'test-user','SRP_A':'ephemeral'}
        srp.return_value.process_challenge.return_value = {'proof':'test'}
        assert await api.async_token() == 'access'
        assert await api.async_token() == 'access'
    assert api._client.initiate_auth.call_count == 1
    assert api._client.initiate_auth.call_args.kwargs['AuthFlow'] == 'USER_SRP_AUTH'
    assert api._client.respond_to_auth_challenge.call_args.kwargs['Session'] == 'test-session'

@pytest.mark.asyncio
async def test_refresh_and_concurrent_rejection_only_refreshes_once():
    api = client()
    api._access_token='old'; api._refresh_token='refresh'
    api._client.initiate_auth.return_value={'AuthenticationResult':{'AccessToken':'new','ExpiresIn':3600}}
    result = await asyncio.gather(api.async_token('old'), api.async_token('old'))
    assert result == ['new','new']
    assert api._client.initiate_auth.call_count == 1
    assert api._client.initiate_auth.call_args.kwargs['AuthFlow'] == 'REFRESH_TOKEN_AUTH'
    assert api._refresh_token == 'refresh'

@pytest.mark.asyncio
async def test_expired_refresh_falls_back_to_login():
    api=client(); api._refresh_token='expired'
    api._client.initiate_auth.side_effect=[ClientError({'Error':{'Code':'NotAuthorizedException'}},'InitiateAuth'),
        {'AuthenticationResult':{'AccessToken':'new','RefreshToken':'new-refresh'}}]
    with patch.object(api_module,'AWSSRP'):
        assert await api.async_token() == 'new'
    assert api._refresh_token == 'new-refresh'

@pytest.mark.asyncio
async def test_challenge_and_wrong_password():
    api=client();api._client.initiate_auth.return_value={'ChallengeName':'SMS_MFA'}
    with patch.object(api_module,'AWSSRP'), pytest.raises(api_module.AuthError):
        await api.async_token()
    api._client.initiate_auth.side_effect=ClientError({'Error':{'Code':'NotAuthorizedException'}},'InitiateAuth')
    with patch.object(api_module,'AWSSRP'), pytest.raises(api_module.AuthError):
        await api.async_token()

@pytest.mark.asyncio
async def test_discovery_pagination_and_dynamic_ids():
    session=Session(Response({'data':{'me':{'id':'user','devices':[{'id':'pool-a'}]}}}),
        Response({'data':{'me':{'id':'user','devices':[{'id':'pool-b'}]}}}),
        Response({'data':{'me':{'id':'user','devices':[]}}}))
    api=client(session);api._access_token='a';api._expires=float('inf')
    assert await api.async_discover() == ['pool-a','pool-b']
    assert api.account_id == 'user'
    assert [r['json']['variables']['pageNumber'] for r in session.requests] == [1,2,3]

@pytest.mark.asyncio
async def test_http_401_refresh_and_retry():
    session=Session(Response({},401),Response({'data':{'ok':True}}))
    api=client(session);api._access_token='old';api._expires=float('inf');api._refresh_token='r'
    api._client.initiate_auth.return_value={'AuthenticationResult':{'AccessToken':'new'}}
    assert await api.async_query('query X { x }','X',{}) == {'ok':True}
    assert [r['headers']['Authorization'] for r in session.requests] == ['Bearer old','Bearer new']
    assert all(r['allow_redirects'] is False for r in session.requests)

@pytest.mark.asyncio
@pytest.mark.parametrize('response', [Response({},500),Response({'errors':[{'message':'secret'}]}),Response([])])
async def test_errors_are_sanitized(response):
    api=client(Session(response));api._access_token='a';api._expires=float('inf')
    with pytest.raises(api_module.ApiError) as err:
        await api.async_query('query X { x }','X',{})
    assert 'secret' not in str(err.value)

@pytest.mark.asyncio
async def test_mismatched_device_id_rejected():
    api=client(Session(Response({'data':{'device':fixture('get_device')}})))
    api._access_token='a';api._expires=float('inf')
    with pytest.raises(api_module.ApiError): await api.async_device('different')

@pytest.mark.asyncio
async def test_no_devices_and_repeating_pagination():
    empty=Response({'data':{'me':{'id':'user','devices':[]}}})
    api=client(Session(empty));api._access_token='a';api._expires=float('inf')
    with pytest.raises(api_module.NoDevicesError): await api.async_discover()
    page=Response({'data':{'me':{'id':'user','devices':[{'id':'same'}]}}})
    api.session=Session(page,page)
    with pytest.raises(api_module.ApiError,match='pagination'): await api.async_discover()

@pytest.mark.asyncio
async def test_persistent_auth_failure_stops_after_one_retry():
    api=client(Session(Response({},401),Response({},401)))
    api._access_token='old';api._refresh_token='r';api._expires=float('inf')
    api._client.initiate_auth.return_value={'AuthenticationResult':{'AccessToken':'new'}}
    with pytest.raises(api_module.AuthError): await api.async_query('query X { x }','X',{})
    assert len(api.session.requests)==2

@pytest.mark.asyncio
async def test_cognito_pool_closed_tokens_cleared():
    api=client();sdk=api._client
    api._access_token='a';api._refresh_token='r'
    await api.async_close()
    sdk.close.assert_called_once()
    assert api._access_token is api._refresh_token is api._client is None
