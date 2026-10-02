"""Exercise real HA config flow, entity lifecycle, coordinator and reauth."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.config_entries import SOURCE_USER, SOURCE_REAUTH
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.ixmanager.api import ApiError, AuthError, NoDevicesError
from custom_components.ixmanager.models import parse_device
from custom_components.ixmanager.coordinator import IxmanagerCoordinator

@pytest.fixture
def device():
    return parse_device(json.loads((Path(__file__).parent/'fixtures/get_device.json').read_text()))

@pytest.fixture
def mock_api(device):
    api = AsyncMock()
    api.account_id = 'account-test'
    api.async_discover.return_value = [device.id]
    api.async_device.return_value = device
    return api

@pytest.mark.asyncio
async def test_user_flow_and_duplicate(hass, enable_custom_integrations, mock_api):
    with patch('custom_components.ixmanager.config_flow.IxmanagerApi', return_value=mock_api), \
         patch('custom_components.ixmanager.async_setup_entry', return_value=True):
        result = await hass.config_entries.flow.async_init('ixmanager',context={'source':SOURCE_USER})
        assert result['type'] == FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(result['flow_id'],
            {CONF_USERNAME:'test',CONF_PASSWORD:'test'})
        assert result['type'] == FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        result = await hass.config_entries.flow.async_init('ixmanager',context={'source':SOURCE_USER},
            data={CONF_USERNAME:'test',CONF_PASSWORD:'test'})
        assert result['reason'] == 'already_configured'

@pytest.mark.asyncio
@pytest.mark.parametrize(('error','expected'),[(AuthError(),'invalid_auth'),(ApiError(),'cannot_connect'),(NoDevicesError(),'no_devices')])
async def test_flow_errors(hass, enable_custom_integrations, mock_api, error, expected):
    mock_api.async_discover.side_effect = error
    with patch('custom_components.ixmanager.config_flow.IxmanagerApi',return_value=mock_api):
        result=await hass.config_entries.flow.async_init('ixmanager',context={'source':SOURCE_USER},
            data={CONF_USERNAME:'test',CONF_PASSWORD:'test'})
        assert result['errors'] == {'base':expected}

@pytest.mark.asyncio
async def test_setup_states_offline_and_unload(hass, enable_custom_integrations, mock_api, device):
    entry=MockConfigEntry(domain='ixmanager',unique_id='account-test',data={CONF_USERNAME:'test',CONF_PASSWORD:'test'})
    entry.add_to_hass(hass)
    with patch('custom_components.ixmanager.IxmanagerApi',return_value=mock_api):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        states = hass.states.async_all('sensor')
        assert len(states) == 15
        temp=next(s for s in states if s.attributes.get('parameter')=='poolTempWithSettings')
        assert temp.state=='24.0'
        assert temp.attributes['unit_of_measurement']=='°C'
        coord=entry.runtime_data
        from dataclasses import replace
        coord.async_set_updated_data({device.id:replace(device,online=False)})
        await hass.async_block_till_done()
        assert hass.states.get(temp.entity_id).state=='unavailable'
        coord.async_set_updated_data({device.id:device})
        await hass.async_block_till_done()
        assert hass.states.get(temp.entity_id).state=='24.0'
        # Network failure hides previous values.
        coord.async_set_update_error(UpdateFailed('offline'))
        await hass.async_block_till_done()
        assert hass.states.get(temp.entity_id).state=='unavailable'
        assert await hass.config_entries.async_unload(entry.entry_id)

@pytest.mark.asyncio
async def test_coordinator_auth_and_network_errors(hass, mock_api):
    entry=MockConfigEntry(domain='ixmanager')
    coordinator=IxmanagerCoordinator(hass,entry,mock_api)
    mock_api.async_discover.side_effect=AuthError('auth')
    with pytest.raises(ConfigEntryAuthFailed): await coordinator._async_update_data()
    mock_api.async_discover.side_effect=ApiError('network')
    with pytest.raises(UpdateFailed): await coordinator._async_update_data()

@pytest.mark.asyncio
async def test_reauth_same_account(hass, enable_custom_integrations, mock_api):
    entry=MockConfigEntry(domain='ixmanager',unique_id='account-test',data={CONF_USERNAME:'test',CONF_PASSWORD:'old'})
    entry.add_to_hass(hass)
    with patch('custom_components.ixmanager.config_flow.IxmanagerApi',return_value=mock_api), \
         patch.object(hass.config_entries,'async_reload',return_value=True):
        result=await hass.config_entries.flow.async_init('ixmanager',context={'source':SOURCE_REAUTH,'entry_id':entry.entry_id},data=entry.data)
        result=await hass.config_entries.flow.async_configure(result['flow_id'],{CONF_USERNAME:'test',CONF_PASSWORD:'new'})
        assert result['reason']=='reauth_successful'
        assert entry.data[CONF_PASSWORD]=='new'

@pytest.mark.asyncio
async def test_new_parameters_added_and_missing_unavailable(hass, enable_custom_integrations, mock_api, device):
    from dataclasses import replace
    entry=MockConfigEntry(domain='ixmanager',unique_id='account-test',data={CONF_USERNAME:'test',CONF_PASSWORD:'test'})
    entry.add_to_hass(hass)
    with patch('custom_components.ixmanager.IxmanagerApi',return_value=mock_api):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        p=next(iter(device.parameters.values()))
        new=replace(p,name='newTemperature',label='Neue Temperatur')
        entry.runtime_data.async_set_updated_data({device.id:replace(device,parameters={new.key:new})})
        await hass.async_block_till_done()
        states=hass.states.async_all('sensor')
        added=[s for s in states if s.attributes.get('parameter')=='newTemperature']
        assert len(added)==1
        assert added[0].state=='24.0'
        assert len([s for s in states if s.state=='unavailable'])==15
        assert await hass.config_entries.async_unload(entry.entry_id)
        mock_api.async_close.assert_awaited_once()

@pytest.mark.asyncio
async def test_reauth_rejects_another_account(hass, enable_custom_integrations, mock_api):
    entry=MockConfigEntry(domain='ixmanager',unique_id='different-account',data={CONF_USERNAME:'test',CONF_PASSWORD:'old'})
    entry.add_to_hass(hass)
    with patch('custom_components.ixmanager.config_flow.IxmanagerApi',return_value=mock_api):
        result=await hass.config_entries.flow.async_init('ixmanager',context={'source':SOURCE_REAUTH,'entry_id':entry.entry_id},data=entry.data)
        result=await hass.config_entries.flow.async_configure(result['flow_id'],{CONF_USERNAME:'test',CONF_PASSWORD:'new'})
        assert result['reason']=='wrong_account'
        assert entry.data[CONF_PASSWORD]=='old'
