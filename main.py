"""
REST API for Heritage Connector.

To run: `python api.py`
"""

import argparse
from collections import defaultdict
import requests
import json
import re
from typing import List, Optional, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic.networks import HttpUrl
import uvicorn
from api_utils import logging, db_connectors, sparql
from dotenv import load_dotenv
import os
import utils

import data_models

logger = logging.get_logger(__name__)
load_dotenv()
app = FastAPI()
sparql_connector = db_connectors.SPARQLConnector(endpoint=os.environ["SPARQL_ENDPOINT"])

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


@app.post(
    "/predicate_object/by_uri",
    response_model=List[data_models.SPARQLPredicateObject],
    response_model_exclude_unset=True,
    deprecated=True,
)
@app.post(
    "/predicate_object",
    response_model=List[data_models.SPARQLPredicateObject],
    response_model_exclude_unset=True,
)
async def get_predicate_object(uri: HttpUrl, labels: bool = False):
    """Get all the predicate-object pairs for an entity with a specific URI. Optionally return the labels of all objects which have labels."""
    # TODO: return correct error if URL not in database
    return sparql_connector.get_sparql_results(sparql.get_p_o(uri, labels=labels))[
        "results"
    ]["bindings"]


@app.post("/neighbours", response_model=data_models.NeighboursResponse)
async def get_neighbours(request: data_models.NeighboursRequest):
    """
    Return `k` nearest neighbours in embedding space for each entity specified in `entities`. Scores returned are *distances*: to get *similarities*, calculate `1 - score`.

    Response format:

    ```
    {
        "input_entity_1": [
            ["nearest_neighbour_id", score],
            ["nearest_neighbour_id", score],
            ["nearest_neighbour_id", score],
            ...
        ],
        "input_entity_2: [
            ...
        ]
    }
    ```
    """

    neighbours_api_endpoint = f"{os.environ['VECTORS_API']}/neighbours"
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


@app.post("/distance", response_model=float)
async def get_distance(request: data_models.DistanceRequest):
    """Return the distance between two vectors. A 'similarity' score can be calculated as `1-distance`."""

    distance_api_endpoint = f"{os.environ['VECTORS_API']}/distance"
    body = json.dumps(
        {
            "entity_a": request.entity_a,
            "entity_b": request.entity_b,
        }
    )
    headers = {
        "Content-Type": "application/json",
    }

    response = requests.post(distance_api_endpoint, headers=headers, data=body)

    return response.json()


@app.post(
    "/connections",
    response_model=Dict[str, data_models.EntityConnections],
    response_model_exclude_unset=True,
)
async def get_connections(request: data_models.ConnectionsRequest):
    """Get connections *from* and *to* each entity in the request.
    Connections *to* are all the subject-predicate pairs where the entity is the object, and connections *from* are all the predicate-object pairs where the entity is the subject."""

    response = {}

    for ent in request.entities:
        connections_from = sparql_connector.get_sparql_results(
            sparql.get_p_o(ent, labels=request.labels, limit=request.limit)
        )["results"]["bindings"]

        connections_to = sparql_connector.get_sparql_results(
            sparql.get_s_p(ent, labels=request.labels, limit=request.limit)
        )["results"]["bindings"]

        for predicate_object_dict in connections_from:
            if (
                "collections.vam.ac.uk" in predicate_object_dict["object"]["value"]
            ) and "objectLabel" not in predicate_object_dict:
                object_label = utils.get_vam_object_title(
                    predicate_object_dict["object"]["value"]
                )
                if object_label is not None:
                    predicate_object_dict["objectLabel"] = dict()
                    predicate_object_dict["objectLabel"]["type"] = "literal"
                    predicate_object_dict["objectLabel"]["value"] = object_label

        for subject_predicate_dict in connections_to:
            if (
                "collections.vam.ac.uk" in subject_predicate_dict["subject"]["value"]
            ) and "subjectLabel" not in subject_predicate_dict:
                subject_label = utils.get_vam_object_title(
                    subject_predicate_dict["subject"]["value"]
                )
                if subject_label is not None:
                    subject_predicate_dict["subjectLabel"] = dict()
                    subject_predicate_dict["subjectLabel"]["type"] = "literal"
                    subject_predicate_dict["subjectLabel"]["value"] = subject_label

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
        from_data = defaultdict(list)

        if group_name.startswith("Wikidata connections"):
            # if Wikidata, only include connections to other Wikidata items that are in the KG.
            # We can identify these by matching on the HTML link pattern that is used for Wikidata records which have a label (i.e. they are in the Wikidata cache, thus in the KG).
            for p in abbreviated_predicates:
                if p in predicates_in_from:
                    for i in flattened_connections["from"]:
                        if (i["predicate"] == p) and (
                            len(
                                re.findall(
                                    r"<a href='http://www.wikidata.org/entity/Q\d+'>.+\[WD:Q\d+\]</a>",
                                    i["object"],
                                )
                            )
                            > 0
                        ):
                            from_data[utils.assignGroupToURI(i["object"])].append(i)
        else:
            for p in abbreviated_predicates:
                if p in predicates_in_from:
                    for i in flattened_connections["from"]:
                        if i["predicate"] == p:
                            from_data[utils.assignGroupToURI(i["object"])].append(i)

        if from_data:
            grouped_connections["from"][group_name] = {
                k: v for k, v in from_data.items() if v
            }

        to_data = defaultdict(list)

        for p in abbreviated_predicates:
            if p in predicates_in_to:
                for i in flattened_connections["to"]:
                    if i["predicate"] == p:
                        to_data[utils.assignGroupToURI(i["subject"])].append(i)

        if to_data:
            grouped_connections["to"][group_name] = {
                k: v for k, v in to_data.items() if v
            }

    return grouped_connections


async def process_neighbours_output(neighbours: List[list]):
    """
    - convert distances to similarities
    - convert URLs to links with labels and abbreviated URLs
    """

    labels_request = data_models.LabelsRequest(
        uris=[i[0] for i in neighbours if i[0].startswith("http")]
    )
    uri_label_mapping = await get_labels(labels_request)

    neighbours_out = []

    for (neighbour_uri_or_literal, neighbour_distance) in neighbours:
        neighbour_similarity_percent = round((1 - neighbour_distance) * 100, 1)

        if neighbour_uri_or_literal.startswith("http") and (
            neighbour_uri_or_literal in uri_label_mapping.keys()
        ):
            neighbour_display = f"<a href='?entity={utils.normaliseURI(neighbour_uri_or_literal)}'>{uri_label_mapping[neighbour_uri_or_literal]} [{utils.abbreviateURI(neighbour_uri_or_literal)}]</a>"

            # Only add related URIs with labels that are not lowercase
            if (
                isinstance(uri_label_mapping[neighbour_uri_or_literal], str)
                and uri_label_mapping[neighbour_uri_or_literal]
                != uri_label_mapping[neighbour_uri_or_literal].lower()
            ):
                neighbours_out.append([neighbour_display, neighbour_similarity_percent])

        elif neighbour_uri_or_literal.startswith("http"):
            neighbour_display = f"<a href='?entity={utils.normaliseURI(neighbour_uri_or_literal)}'>{utils.abbreviateURI(neighbour_uri_or_literal)}</a>"
            neighbours_out.append([neighbour_display, neighbour_similarity_percent])
        else:
            neighbour_display = neighbour_uri_or_literal
            neighbours_out.append([neighbour_display, neighbour_similarity_percent])

    return neighbours_out


@app.get("/view_connections", include_in_schema=False)
async def view_connections_single_entity(entity: Optional[str] = None):
    """View HTML template showing connections to and from each entity in the request."""

    CONNECTIONS_LIMIT = 150

    if entity is None:
        entry_point_uris_images = {
            "http://www.wikidata.org/entity/Q5928": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/HendrixHoepla1967-2.jpg/220px-HendrixHoepla1967-2.jpg",  # Jimi Hendrix
            "https://www.wikidata.org/wiki/Q35765": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Osaka_montage.jpg/220px-Osaka_montage.jpg",  # Osaka
            "https://www.wikidata.org/wiki/Q129864": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/Indian_Rebellion_of_1857.jpg/220px-Indian_Rebellion_of_1857.jpg",  # Indian Rebellion of 1857,
            "https://www.wikidata.org/wiki/Q469027": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Issey_Miyake_Tokyo_2016.jpg/440px-Issey_Miyake_Tokyo_2016.jpg",  # Issey Miyake
            "https://www.wikidata.org/wiki/Q46861": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Unknown_Tibetan_Sanskrit_Text.jpg/440px-Unknown_Tibetan_Sanskrit_Text.jpg",  # Tibetan alphabet
            "https://www.wikidata.org/wiki/Q585777": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Aerial_View_of_Brookhaven_National_Laboratory.jpg/440px-Aerial_View_of_Brookhaven_National_Laboratory.jpg",  # Brookhaven National Laboratory
            "https://www.wikidata.org/wiki/Q9696": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/John_F._Kennedy%2C_White_House_color_photo_portrait.jpg/440px-John_F._Kennedy%2C_White_House_color_photo_portrait.jpg",  # John F Kennedy
            "https://www.wikidata.org/wiki/Q172763": "https://live.staticflickr.com/65535/50046568722_73000066f0_z.jpg",  # Joy Division
            "https://www.wikidata.org/wiki/Q8577": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/15-11-05_101_Monument.jpg/440px-15-11-05_101_Monument.jpg",  # 2012 Summer Olympics
            "https://www.wikidata.org/wiki/Q9439": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Queen_Victoria_by_Bassano.jpg/440px-Queen_Victoria_by_Bassano.jpg",  # Queen Victoria
            # "https://www.wikidata.org/wiki/Q37922": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/Nobel2008Literature_news_conference1.jpg/440px-Nobel2008Literature_news_conference1.jpg" # Nobel Prize in Literature
        }
        entry_point_uris = [
            utils.normaliseURI(uri) for uri in entry_point_uris_images.keys()
        ]
        entry_point_uris_images = {
            utils.normaliseURI(k): v for k, v in entry_point_uris_images.items()
        }
        entry_point_uri_label_mapping = await (
            get_labels(data_models.LabelsRequest(uris=entry_point_uris))
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

    connections_request = data_models.ConnectionsRequest(
        entities=[entity], labels=True, limit=CONNECTIONS_LIMIT
    )
    labels_request = data_models.LabelsRequest(uris=[entity])
    label_response = await get_labels(labels_request)
    ent_label = label_response[entity]

    neighbours_request = data_models.NeighboursRequest(entities=[entity], k=30)
    neighbours_response = await get_neighbours(neighbours_request)
    neighbours_response_to_display = await process_neighbours_output(
        neighbours_response[entity]
    )

    connections = await get_connections(connections_request)
    connections_processed = flatten_connections_response(connections, entity)
    grouped_connections = group_flattened_connections(connections_processed)

    entity = utils.vam_api_url_to_collection_url(entity)

    return templates.TemplateResponse(
        "connections.html",
        {
            "request": grouped_connections,
            "neighbours": neighbours_response_to_display,
            "id": entity,
            "label": ent_label,
        },
    )


@app.post("/labels", response_model=data_models.LabelsResponse)
async def get_labels(request: data_models.LabelsRequest):
    """Get labels for several entities represented by their URIs (i.e. literals have no label). Returns a dictionary mapping each input entity to the label if it exists, and `null` otherwise."""
    results = sparql_connector.get_sparql_results(sparql.get_labels(request.uris))[
        "results"
    ]["bindings"]
    response = {k: None for k in request.uris}

    # TODO: this could be sped up by bundling all wikidata label requests into one list, and modifying
    # `utils.get_wikidata_entity_label` to send up to 50 QIDs at a time to the wbgetentities API.

    for res in results:
        item_label = res.get("sLabel", {}).get("value")
        if not item_label:
            if "collections.vam.ac.uk/item" in res["s"]["value"]:
                item_label = utils.get_vam_object_title(res["s"]["value"])
            if ("wikidata.org" in res["s"]["value"]) and re.findall(
                r"Q\d+", res["s"]["value"]
            ):
                item_label = utils.get_wikidata_entity_label(res["s"]["value"])

        response[res["s"]["value"]] = item_label

    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--port", type=int, help="Optional port (default 8000)", default=8000
    )

    args = parser.parse_args()
    port = args.port

    uvicorn.run(app, host="0.0.0.0", port=port)
