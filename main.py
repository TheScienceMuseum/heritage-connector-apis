"""
REST API for Heritage Connector.

To run: `python api.py`
"""

import argparse
import requests
import json
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic.networks import HttpUrl
import uvicorn
from api_utils import config, logging, db_connectors, sparql

logger = logging.get_logger(__name__)
cfg = config.config
app = FastAPI()
es_connector = db_connectors.ElasticsearchConnector(
    cfg.ELASTIC_SEARCH_CLUSTER, cfg.ELASTIC_SEARCH_USER, cfg.ELASTIC_SEARCH_PASSWORD
)
sparql_connector = db_connectors.SPARQLConnector()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    pass


@app.get("/predicate_object/by_uri")
@app.post("/predicate_object/by_uri")
async def get_predicate_object(uri: HttpUrl, labels: bool = False):
    # TODO: return correct error if URL not in database
    # TODO: re-enable POST by adding data model as in /neighbours and /labels
    return sparql_connector.get_sparql_results(sparql.get_p_o(uri, labels=labels))[
        "results"
    ]["bindings"]


class NeighboursRequest(BaseModel):
    entities: List[str]
    k: int


@app.get("/neighbours")
@app.post("/neighbours")
async def get_neighbours(request: NeighboursRequest):
    neighbours_api_endpoint = cfg.NEIGHBOURS_API
    body = json.dumps(
        {
            "entities": request.entities,
            "k": request.k,
        }
    )
    headers = {
        "Content-Type": "application/json",
    }
    response = requests.post(neighbours_api_endpoint, headers=headers, data=body)

    return response.json()


class LabelsRequest(BaseModel):
    uris: List[HttpUrl]


@app.get("/labels")
@app.post("/labels")
async def get_labels(request: LabelsRequest):
    results = sparql_connector.get_sparql_results(sparql.get_labels(request.uris))[
        "results"
    ]["bindings"]
    response = {k: None for k in request.uris}

    for res in results:
        response[res["s"]["value"]] = res.get("sLabel", {}).get("value")

    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--port", type=int, help="Optional port (default 8000)", default=8000
    )

    args = parser.parse_args()
    port = args.port

    uvicorn.run(app, host="0.0.0.0", port=port)
