"""
Utils and filters for use with jinja2. Used in `main.py`.
"""

import re
import requests
from api_utils import logging

logger = logging.get_logger(__name__)

predicateAbbreviationMapping = {
    "http://www.w3.org/2000/01/rdf-schema#": "RDFS",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "RDF",
    "http://www.w3.org/2004/02/skos/core#": "SKOS",
    "http://www.w3.org/2001/XMLSchema#": "XSD",
    "http://xmlns.com/foaf/0.1/": "FOAF",
    "http://www.w3.org/2002/07/owl#": "OWL",
    "http://www.w3.org/ns/prov#": "PROV",
    "https://schema.org/": "SDO",
    "http://www.wikidata.org/entity/": "WD",
    "http://www.wikidata.org/prop/direct/": "WDT",
    "http://www.heritageconnector.org/RDF/": "HC",
    "https://collection.sciencemuseumgroup.org.uk/people/": "SMGP",
    "https://collection.sciencemuseumgroup.org.uk/objects/": "SMGO",
    "https://collection.sciencemuseumgroup.org.uk/documents/": "SMGD",
    "https://blog.sciencemuseum.org.uk/": "SMGBLOG",
    "http://journal.sciencemuseum.ac.uk/browse/": "SMGJOURNAL",
    "https://api.vam.ac.uk/v2/objects/search?id_organisation=": "VAMORG",
    "https://api.vam.ac.uk/v2/objects/search?id_person=": "VAMPERSON",
    "http://collections.vam.ac.uk/item/": "VAMOBJECT",
}

predicateManualGroups = {
    "Existing record metadata": [
        "RDFS:label",
        "HC:database",
        "RDF:type",
        "SKOS:hasTopConcept",
        "SDO:isPartOf",
        "XSD:additionalType",
        "SDO:birthDate",
        "SDO:deathDate",
        "SDO:birthPlace",
        "SDO:deathPlace",
        "SDO:hasOccupation",
        "SDO:nationality",
        "SDO:addressCountry",
        "SDO:foundingDate",
        "SDO:dissolutionDate",
        "SDO:material",
        "SDO:dateCreated",
        "SDO:author",
        "SDO:genre",
        "SDO:keywords",
        "SDO:identifier",
    ],
    "Existing links to other pages": [
        "SDO:mentions",
        "FOAF:maker",
        "FOAF:made",
        "SKOS.related",
    ],
    "sameAs/similar links": [
        "SKOS.relatedMatch",
        "OWL:sameAs",
    ],
    "From NER & NEL": [
        "HC:entityPERSON",
        "HC:entityORG",
        "HC:entityNORP",
        "HC:entityFAC",
        "HC:entityLOC",
        "HC:entityOBJECT",
        "HC:entityLANGUAGE",
        "HC:entityDATE",
        "HC:entityEVENT",
    ],
    "Wikidata connections (selected)": [
        "WDT:P17",
        "WDT:P18",
        "WDT:P20",
        "WDT:P21",
        "WDT:P27",
        "WDT:P31",
        "WDT:P39",
        "WDT:P61",
        "WDT:P101",
        "WDT:P106",
        "WDT:P127",
        "WDT:P135",
        "WDT:P136",
        "WDT:P137",
        "WDT:P155",
        "WDT:P156",
        "WDT:P159",
        "WDT:P166",
        "WDT:P176",
        "WDT:P180",
        "WDT:P186",
        "WDT:P195",
        "WDT:P214",
        "WDT:P217",
        "WDT:P244",
        "WDT:P276",
        "WDT:P279",
        "WDT:P287",
        "WDT:P297",
        "WDT:P361",
        "WDT:P366",
        "WDT:P452",
        "WDT:P463",
        "WDT:P485",
        "WDT:P495",
        "WDT:P527",
        "WDT:P569",
        "WDT:P570",
        "WDT:P571",
        "WDT:P580",
        "WDT:P582",
        "WDT:P585",
        "WDT:P607",
        "WDT:P620",
        "WDT:P625",
        "WDT:P646",
        "WDT:P710",
        "WDT:P729",
        "WDT:P730",
        "WDT:P749",
        "WDT:P793",
        "WDT:P828",
        "WDT:P856",
        "WDT:P973",
        "WDT:P1056",
        "WDT:P1064",
        "WDT:P1202",
        "WDT:P1367",
        "WDT:P1535",
        "WDT:P1542",
        "WDT:P1679",
        "WDT:P1711",
        "WDT:P1716",
        "WDT:P1816",
        "WDT:P1995",
        "WDT:P2067",
        "WDT:P2598",
        "WDT:P2669",
        "WDT:P2703",
        "WDT:P2741",
        "WDT:P2802",
        "WDT:P3074",
        "WDT:P3342",
        "WDT:P4326",
        "WDT:P4438",
        "WDT:P6379",
        "WDT:P6764",
        "WDT:P7818",
        "WDT:P8565",
        "WDT:P9144",
    ],
}


def abbreviateURI(uri: str) -> str:
    if not isinstance(uri, str):
        uri = str(uri)

    for k, v in predicateAbbreviationMapping.items():
        if uri.startswith(k):
            return f"{v}:{uri[len(k):]}"

    return uri


def normaliseURI(uri: str) -> str:
    """Change URI from SMG, V&A or Wikidata to the form that exists in the KG"""

    try:
        if "collection.sciencemuseumgroup" in uri:
            # remove anything after cp/co/cd/aa (ID) from the end of the URL
            return re.findall(
                r"https:\/\/(?:collection\.sciencemuseum).(?:\w.+)\/(?:co|cd|cp|aa|ap)(?:\d+)",
                uri,
            )[0]
        elif "blog.sciencemuseum.org.uk" in uri:
            return uri
        elif "https://journal.sciencemuseum.ac.uk" in uri:
            return re.sub("https", "http", uri)
        elif "collections.vam.ac.uk/item" in uri:
            if "https" in uri:
                uri = re.sub("https", "http", uri)
            return re.findall(r"(http://collections.vam.ac.uk/item/[A-Za-z\d]+)", uri)[
                0
            ]
        elif uri.startswith("https://www.wikidata.org/wiki/"):
            return re.sub(
                "https://www.wikidata.org/wiki/", "http://www.wikidata.org/entity/", uri
            )
        elif uri.startswith("https://www.wikidata.org/entity/"):
            return re.sub("https", "http", uri)
        else:
            # return the input if it doesn't fit into any of the above categories
            return uri

    except Exception as e:
        logger.error(f"{uri} normalisation failed: {e}")
        return uri


def assignGroupToURI(uri: str) -> str:
    """Returns a group for a URI e.g. science museum, v&a, wikidata. Should operate on the normalised URI produced by `normaliseURI`."""

    if "collection.sciencemuseumgroup" in uri:
        return "Science Museum Group Collection"
    elif "blog.sciencemuseum.org.uk" in uri:
        return "Science Museum Blog"
    elif "journal.sciencemuseum.ac.uk" in uri:
        return "Science Museum Journal"
    elif ("collections.vam.ac.uk" in uri) or (
        "api.vam.ac.uk/v2/objects/search?" in uri
    ):
        return "V&A collection"
    elif "http://www.wikidata.org/entity/" in uri:
        return "Wikidata"
    else:
        return "Literal (raw value)"


def get_vam_object_title(object_url) -> str:
    """"""
    object_url = normaliseURI(object_url)
    api_url = (
        re.sub("collections.vam.ac.uk/item", "api.vam.ac.uk/v2/object", object_url)
        + "?response_format=json"
    )
    headers = {
        "Accept": "application/json",
    }
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        response_json = response.json()
        titles = response_json["record"].get("titles", [])
        if titles:
            generic_titles = [
                v["title"] for v in titles if v["type"] == "generic title"
            ]
            if generic_titles:
                return generic_titles[0]
        else:
            return response_json["record"].get("objectType")

    else:
        return None


def get_wikidata_entity_label(wiki_url) -> str:
    qid = re.findall(r"Q\d+", wiki_url)[0]
    api_url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&props=labels&ids={qid}&format=json"
    response = requests.get(api_url)

    if response.status_code == 200:
        response_json = response.json()
        return (
            response_json["entities"]
            .get(qid, {})
            .get("labels", {})
            .get("en", {})
            .get("value", None)
        )

    else:
        return None


def vam_api_url_to_collection_url(api_url) -> str:
    """
    Return a human-readable collection URL, given a machine-readable API URL.
    Returns original URL if `api_url` doesn't look like a V&A API path.

    This has only been tested for searches and API calls ?id_person and ?id_organisation query strings.
    """

    if "api.vam.ac.uk" in api_url:
        return re.sub(
            r"https://api.vam.ac.uk/v2/objects/",
            r"https://collections.vam.ac.uk/",
            api_url,
        )
    else:
        return api_url
