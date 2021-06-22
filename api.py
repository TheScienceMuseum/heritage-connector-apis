"""
REST API for Heritage Connector.

To run: `python api.py`
"""

from fastapi import FastAPI
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


@app.on_event("startup")
async def startup():
    pass


@app.get("/predicate_object/by_uri")
@app.post("/predicate_object/by_uri")
async def get_predicate_object(uri: HttpUrl):
    # TODO: return correct error if URL not in database
    return sparql_connector.get_sparql_results(sparql.get_p_o(uri))["results"][
        "bindings"
    ]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
