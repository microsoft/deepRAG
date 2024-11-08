#!/bin/bash

# Variables
RESOURCE_GROUP="rg-deeprag"
LOCATION="westus" # Change to your preferred location
CONTAINER_REGISTRY="analyticassistant"
CONTAINER_ENVIRONMENT="agent-service-env"
AGENT_SERVICE_IMAGE="agent_service:latest"
STREAMLIT_IMAGE="streamlit_app:latest"

# Create a resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create a container registry
az acr create --resource-group $RESOURCE_GROUP --name $CONTAINER_REGISTRY --sku Basic

# Enable admin rights for the container registry
az acr update -n $CONTAINER_REGISTRY --admin-enabled true

# Build the Python service image
az acr build --registry $CONTAINER_REGISTRY --image $AGENT_SERVICE_IMAGE --file ./Dockerfile.agent_service ./

# Build the Streamlit app image
az acr build --registry $CONTAINER_REGISTRY --image $STREAMLIT_IMAGE --file ./Dockerfile.streamlit_app ./

# Create a container environment
az containerapp env create --name $CONTAINER_ENVIRONMENT --resource-group $RESOURCE_GROUP --location $LOCATION
az acr update -n $CONTAINER_REGISTRY --admin-enabled true

# Deploy the agent-service service and get its URL
agent_service_output=$(az containerapp create \
  --name agent-service \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENVIRONMENT \
  --image $CONTAINER_REGISTRY.azurecr.io/$AGENT_SERVICE_IMAGE \
  --min-replicas 1 --max-replicas 1 \
  --target-port 8000 \
  --ingress external \
  --registry-server $CONTAINER_REGISTRY.azurecr.io \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

# Check if the deployment was successful and the URL was retrieved
if [ -z "$agent_service_output" ]; then
  echo "Failed to retrieve the URL of the agent-service service."
  exit 1
fi

# Construct the agent_service_URL
agent_service_URL="https://$agent_service_output"

# Deploy the agent-fe service with the agent_service_URL environment variable
fe_service_output=$(az containerapp create \
  --name agent-fe \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENVIRONMENT \
  --image $CONTAINER_REGISTRY.azurecr.io/$STREAMLIT_IMAGE \
  --min-replicas 1 --max-replicas 1 \
  --target-port 8501 \
  --ingress external \
  --registry-server $CONTAINER_REGISTRY.azurecr.io \
  --env-vars agent_service_URL=$agent_service_URL \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

# Check if the deployment was successful
if [ -z "$fe_service_output" ]; then
  echo "Failed to deploy agent-fe."
  exit 1
else
  echo "Successfully deployed frontend service with URL: http://$fe_service_output"
fi
