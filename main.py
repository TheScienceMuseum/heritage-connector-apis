"""
REST API for Heritage Connector.

To run: `python api.py`
"""

import argparse
import requests
import json
import re
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from pydantic.networks import HttpUrl
import uvicorn
from api_utils import config, logging, db_connectors, sparql
import utils

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

templates = Jinja2Templates(directory="templates")
templates.env.filters["abbreviateURI"] = utils.abbreviateURI


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


class ConnectionsRequest(BaseModel):
    entities: List[str]
    labels: bool = False


@app.get("/connections")
@app.post("/connections")
async def get_connections(request: ConnectionsRequest):
    """Get connections from or to each entity in the request."""

    response = {}

    for ent in request.entities:
        connections_from = sparql_connector.get_sparql_results(
            sparql.get_p_o(ent, labels=request.labels)
        )["results"]["bindings"]

        connections_to = sparql_connector.get_sparql_results(
            sparql.get_s_p(ent, labels=request.labels)
        )["results"]["bindings"]

        response.update(
            {
                ent: {
                    "from": connections_from,
                    "to": connections_to,
                }
            }
        )

    return response


def flatten_connections_response(connections_response, _id):
    """Process response from the /connections API to a format that can be easily displayed by the jinja2 template
    at `templates/connections.html`.

    Args:
        connections_response ([type]): [description]
        _id ([type]): [description]

    Returns:
        [type]: [description]
    """
    flattened_connections_data = {"from": [], "to": []}

    for connection in connections_response[_id].get("from", {}):
        processed_connection = dict()
        processed_connection["predicate"] = utils.abbreviateURI(
            connection["predicate"]["value"]
        )

        if connection["object"]["type"] == "uri":
            if "objectLabel" in connection:
                processed_connection[
                    "object"
                ] = f"<a href='?entity={utils.normaliseURI(connection['object']['value'])}'>{connection['objectLabel']['value']} [{utils.abbreviateURI(connection['object']['value'])}]</a>"
            else:
                processed_connection[
                    "object"
                ] = f"<a href='?entity={utils.normaliseURI(connection['object']['value'])}'>{utils.abbreviateURI(connection['object']['value'])}</a>"
        else:
            processed_connection["object"] = connection["object"]["value"]

        flattened_connections_data["from"].append(processed_connection)

    for connection in connections_response[_id].get("to", {}):
        processed_connection = dict()
        processed_connection["predicate"] = utils.abbreviateURI(
            connection["predicate"]["value"]
        )

        if connection["subject"]["type"] == "uri":
            if "subjectLabel" in connection:
                processed_connection[
                    "subject"
                ] = f"<a href='?entity={utils.normaliseURI(connection['subject']['value'])}'>{connection['subjectLabel']['value']} [{utils.abbreviateURI(connection['subject']['value'])}]</a>"
            else:
                processed_connection[
                    "subject"
                ] = f"<a href='?entity={utils.normaliseURI(connection['subject']['value'])}'>{utils.abbreviateURI(connection['subject']['value'])}</a>"
        else:
            processed_connection["subject"] = connection["subject"]["value"]

        flattened_connections_data["to"].append(processed_connection)

    return flattened_connections_data


def group_flattened_connections(flattened_connections: dict) -> dict:
    """Group the dict created by `flatten_connections_response` according to the manual groups
    set in `utils.predicateManualGroups`.
    """

    # each of the items in the from and to dicts takes the form {"group_name": [data, ...]}
    grouped_connections = {"from": {}, "to": {}}
    predicates_in_from = [item["predicate"] for item in flattened_connections["from"]]
    predicates_in_to = [item["predicate"] for item in flattened_connections["to"]]

    for group_name, abbreviated_predicates in utils.predicateManualGroups.items():
        from_data = []

        if group_name.startswith("Wikidata connections"):
            # if Wikidata, only include connections to other Wikidata items that are in the KG.
            # We can identify these by matching on the HTML link pattern that is used for Wikidata records which have a label (i.e. they are in the Wikidata cache, thus in the KG).
            for p in abbreviated_predicates:
                if p in predicates_in_from:
                    from_data += [
                        i
                        for i in flattened_connections["from"]
                        if (i["predicate"] == p)
                        and (
                            len(
                                re.findall(
                                    r"<a href='http://www.wikidata.org/entity/Q\d+'>.+\[WD:Q\d+\]</a>",
                                    i["object"],
                                )
                            )
                            > 0
                        )
                    ]
        else:
            for p in abbreviated_predicates:
                if p in predicates_in_from:
                    from_data += [
                        i for i in flattened_connections["from"] if i["predicate"] == p
                    ]

        if from_data:
            grouped_connections["from"][group_name] = from_data

        to_data = []

        for p in abbreviated_predicates:
            if p in predicates_in_to:
                to_data += [
                    i for i in flattened_connections["to"] if i["predicate"] == p
                ]

        if to_data:
            grouped_connections["to"][group_name] = to_data

    return grouped_connections


@app.get("/view_connections")
async def view_connections_single_entity(entity: Optional[str] = None):
    """View HTML template showing connections to and from each entity in the request."""

    if entity is None:
        entry_point_uris_images = {
            "http://www.wikidata.org/entity/Q5928": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/HendrixHoepla1967-2.jpg/220px-HendrixHoepla1967-2.jpg",  # Jimi Hendrix
            "https://www.wikidata.org/wiki/Q35765": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Osaka_montage.jpg/220px-Osaka_montage.jpg",  # Osaka
        }
        entry_point_uris = [
            utils.normaliseURI(uri) for uri in entry_point_uris_images.keys()
        ]
        entry_point_uris_images = {
            utils.normaliseURI(k): v for k, v in entry_point_uris_images.items()
        }
        entry_point_uri_label_mapping = await (
            get_labels(LabelsRequest(uris=entry_point_uris))
        )
        request = dict()
        request["entry_points"] = entry_point_uri_label_mapping
        request["entry_points_images"] = entry_point_uris_images
        return templates.TemplateResponse(
            "connections_index.html", {"request": request}
        )

    entity_redirect = utils.normaliseURI(entity)
    if entity_redirect != entity:
        logger.debug("redirecting")
        return RedirectResponse(url=f"/view_connections?entity={entity_redirect}")

    connections_request = ConnectionsRequest(
        entities=[entity],
        labels=True,
    )
    labels_request = LabelsRequest(uris=[entity])
    label_response = await get_labels(labels_request)
    ent_label = label_response[entity]

    connections = await get_connections(connections_request)
    connections_processed = flatten_connections_response(connections, entity)
    grouped_connections = group_flattened_connections(connections_processed)

    return templates.TemplateResponse(
        "connections.html",
        {"request": grouped_connections, "id": entity, "label": ent_label},
    )


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
