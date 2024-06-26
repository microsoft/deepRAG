# Connect to Azure
Connect-AzAccount

# Set variables
$resourceGroupName = "YourResourceGroupName"
$searchServiceName = "YourSearchServiceName"
$indexName = "YourIndexName"
$storageAccountName = "YourStorageAccountName"
$storageAccountKey = "YourStorageAccountKey"

# Get the search service
$searchService = Get-AzSearchService -ResourceGroupName $resourceGroupName -Name $searchServiceName

# Create a new index
$index = @{
    name = $indexName
    fields = @(
        @{
            name = "id"
            type = "Edm.String"
            searchable = $true
            filterable = $true
            sortable = $true
            facetable = $true
            key = $true
        },
        @{
            name = "title"
            type = "Edm.String"
            searchable = $true
            filterable = $true
            sortable = $true
            facetable = $true
        },
        @{
            name = "content"
            type = "Edm.String"
            searchable = $true
            filterable = $true
            sortable = $false
            facetable = $false
        }
    )
}

New-AzSearchIndex -ServiceName $searchServiceName -Index $index

# Link the search service to the storage account
$storageConnectionString = "DefaultEndpointsProtocol=https;AccountName=$storageAccountName;AccountKey=$storageAccountKey;EndpointSuffix=core.windows.net"
Set-AzSearchService -ResourceGroupName $resourceGroupName -Name $searchServiceName -StorageConnectionString $storageConnectionString