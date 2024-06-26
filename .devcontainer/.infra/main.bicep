
param location string = resourceGroup().location
var projectName = 'graphRAG'

resource aoai 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${projectName}-aoai'
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'F0'
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${projectName}-storage'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}

module vectorDb './vectorDb.bicep' = {
  name: '${projectName}-vectorDb'
  params: {
    location: location
    name: projectName
  }
}

module graphDb './graphDb.bicep' = {
  name: '${projectName}-graphDb'
  params: {
    location: location
    primaryRegion: 'eastus'
    secondaryRegion: 'westus'
  }
}

module webApp './webApp.bicep' = {
  name: projectName
  params: {
    location: location
  }
}
