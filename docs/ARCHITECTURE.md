# Architecture Reference Docs

This document is currently a working document. The materials located here are subject to change.

## Logical Architecture

```mermaid
graph TD
  subgraph AzureServices
    search[Azure AI Search]
    AOAI[Azure AI Services]
    app[Azure App Services]
    storage[Azure Storage]
    graphDb[Cosmos Db]
  end

  subgraph Agents
    rag[Vector RAG Agent]
    graphRag[Graph RAG Agent]
  end

  rag --> search --> storage --> app --> AOAI
  graphRag --> graphDb --> app --> AOAI
  app --> rag --> graphRag --> AOAI

```

## Application Architecture

```mermaid
sequenceDiagram
  autonumber
  participant rag as RAG Agent
  participant graphRag as Graph RAG Agent
  participant search as Azure AI Search
  participant AOAI as Azure AI Services
  participant app as Azure App Services
  participant storage as Azure Storage
  participant graphDb as Azure Cosmos Db

  user ->> app: prompt for information
  app ->> +rag: invoke vector rag agent to enhance prompt
  rag ->> search: grab vectorized content through semantic search.
  search ->> storage: search through indexed content on storage
  storage-->>search: return relevant indexed documents
  search-->>rag: return relevant document chunks/partitions.
  rag-->>app: return enhanced prompt
  deactivate rag

  app ->> +graphRag: invoke graphRag agent to further enhance prompt.
  graphRag ->> graphDb: query relations from entity edges of rag retrieved entities
  graphDb-->>graphRag: return names of edges.
  graphRag ->> AOAI: request to filter related entities and generate a query from user prompt.
  AOAI-->>graphRag: return a structure query for execution.
  graphRag ->> graphDb: search with AOAI generated graph query
  graphDb-->>graphRag: return relevant entities.
  deactivate graphRag

  app ->> AOAI: send prompt enhanced by classic and graph enhanced RAG.
  AOAI-->app: return LLM response
  app -->> app: sanitize LLM response for correctness
  app-->>user: return sanitized response

```

## Software Architecture

```mermaid
sequenceDiagram
    autonumber
    actor u as User
    participant vRAG as Vector Agent
    participant gRAG as Graph Agent
    participant ai as LLM
    participant gDB as Graph Database
    participant vDB as Vector Database

    activate gRAG
    gRAG->>gDB: query graph ontology
    activate gDB
    gDB-->>gRAG: return nodes and edges
    deactivate gDB
    gRAG->>gRAG: Serialize ontology as rdf.
    gRAG->>gRAG: Populate system prompt with serialized ontology
    deactivate gRAG
    critical Get user intent
      activate u
      activate vRAG
      u->>vRAG: Provide initial user prompt
      vRAG->>ai: Identify user intent from user prompt
      activate ai
      ai-->>vRAG: Return intent as goal
      deactivate ai
      deactivate vRAG
    option Gather initial documents
      activate vRAG
      vRAG->>vDB: Search k top results
      vDB-->>vRAG: Return k top results
      vRAG->>vRAG: Enhance prompt with results
      deactivate vRAG
    option Generate graph query
      activate gRAG
      gRAG->>ai: Generate graph query based on k documents from vRAG and ontology.
      activate ai
      ai-->>gRAG: return graph query for target language.
      deactivate ai
      deactivate gRAG
    option Execute graph
      activate gRAG
      gRAG->>gDB: Execute graph query
      activate gDB
      gDB-->>gRAG: Return graph query results
      deactivate gDB
      gRAG->>gRAG: store graph response
      deactivate gRAG
    option Generate additional prompts
      activate vRAG
      vRAG->>ai: Use results of graph query to create n number of related prompts.
      ai-->>vRAG: return a question for each related node in graph query results.
      vRAG->>vDB: search top k results for each generated prompt.
      vDB-->>vRAG: return top k related documents.
      vRAG->>vRAG: enhance prompt with vRAG results.
      deactivate vRAG
    end
    activate vRAG
    vRAG->>ai: submit enhanced user prompt to LLM
    activate ai
    ai-->>vRAG: return response to user prompt
    deactivate ai
    vRAG-->>u: return response to user    
    deactivate u
    deactivate vRAG
    
```
