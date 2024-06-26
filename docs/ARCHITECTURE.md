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
    rag[Classic RAG Agent]
    graphRag[Enhanced Graph RAG Agent]
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
  app ->> +rag: invoke rag agent to enhance prompt
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
    participant a as Agent
    participant ai as LLM
    participant db as Graph Database

    activate a
    a->>db: query graph ontology
    activate db
    db-->>a: return nodes and edges
    deactivate db
    a->>a: Serialize ontology as rdf.
    a->>a: Populate system prompt with serialized ontology
    activate u
    u->>a: Provide initial user prompt
    critical Get user intent
      a->>ai: Identify user intent from user prompt
      activate ai
      ai-->>a: Return intent as goal
      deactivate ai
    option Plan
      a->>ai: Break down prompt into execution plan for goal
      activate ai
      ai-->>a: Return execution plan
      deactivate ai
    option Generate graph query
      a->>ai: Generate graph query based on execution plan
      activate ai
      ai-->>a: return graph query for target language.
      deactivate ai
    option Execute graph
      a->>db: Execute graph query
      activate db
      db-->>a: Return graph query results
      deactivate db
      a->>a: Augment prompt with graph response
    end
    a->>ai: submit graphRAG enhanced user prompt to LLM
    activate ai
    ai-->>a: return response to user prompt
    deactivate ai
    a-->>u: return response to user    
    deactivate a
    deactivate u
    
```
