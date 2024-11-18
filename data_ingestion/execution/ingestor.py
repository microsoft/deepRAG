import asyncio

from fastapi import FastAPI, HTTPException, Request
import logging

from data_ingestion.main import ingest_product_documentation

app = FastAPI()


@app.post("/trigger")
async def http_trigger(request: Request):
    logging.info('Python HTTP trigger function processed a request.')

    data = await request.json()
    source = data.get("source", "intercom")

    if source == "intercom" or source == "notion":
        asyncio.create_task(ingest_product_documentation(source))
        return {"message": f"Ingesting {source} documentation"}
    else:
        raise HTTPException(status_code=400, detail="Please pass a source in the request body")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
