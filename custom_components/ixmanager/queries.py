"""Read-only selections verified against the public iXfield web client.

Request names and metadata together on every poll: never join anonymous values
by array position. options is a JSON scalar, not a GraphQL object selection.
"""
DISCOVER = """
query GetUserDevices($pageNumber: Int!) {
  me { id devices(type: POOL, pageNumber: $pageNumber) { id name } }
}
"""
_FIELDS = """
  id name type controller connectionStatus
  needPropagateDeviceData isConfigurationJobInProgress dataPropagationFailed
  thingType { name businessName }
  liveDeviceData {
    operatingValues(lang: $lang) {
      name label type value desiredValue options settable showDesired validFor
    }
    controls(lang: $lang) {
      name label type value desiredValue options settable showDesired
      forbiddenByUser forbiddenByTechnology
    }
  }
"""
GET_DEVICE = "query GetDevice($id: ID!, $lang: String!) { device(deviceId: $id) {" + _FIELDS + "} }"
LIVE_DATA = "query deviceLiveData($id: ID!, $lang: String!) { device(deviceId: $id) {" + _FIELDS + "} }"
# Future number/select/switch implementations must use an explicit reviewed
# allowlist and server eligibility checks. No mutations or services in v0.1.
