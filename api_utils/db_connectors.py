"""Submodule for connecting to and querying databases.
"""
import json
import time
import urllib
from elasticsearch import Elasticsearch
from SPARQLWrapper import SPARQLWrapper, JSON
from api_utils import logging
from api_utils.config import config

logger = logging.get_logger(__name__)


def get_elasticsearch_connector(
    es_cluster: str, es_user: str, es_password: str, **kwargs
) -> Elasticsearch:
    """Create an Elasticsearch connector with a timeout of 60 seconds.

    Args:
        es_cluster (str)
        es_user (str)
        es_password (str)

    Returns:
        Elasticsearch: elasticsearch connector
    """
    es = Elasticsearch(
        [es_cluster], http_auth=(es_user, es_password), timeout=60, **kwargs
    )
    logger.debug(f"Connected to Elasticsearch cluster at {es_cluster}")

    return es


class SPARQLConnector:
    def __init__(self):
        self.endpoint = config.SPARQL_ENDPOINT

    def get_sparql_results(self, query: str) -> dict:
        """
        Makes a SPARQL query to endpoint_url. From the heritageconnector repo

        Args:
            query (str): SPARQL query

        Returns:
            query_result (dict): the JSON result of the query as a dict
        """
        user_agent = "heritageconnector-api"

        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(query)
        sparql.setMethod("POST")
        sparql.setReturnFormat(JSON)
        sparql.addCustomHttpHeader(
            "User-Agent",
            user_agent,
        )
        try:
            return sparql.query().convert()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print("429")
                if e.headers.get("retry-after", None):
                    print(f"Retrying after {e.headers['retry-after']} seconds")
                    time.sleep(int(e.headers["retry-after"]))
                else:
                    time.sleep(10)
                return self.get_sparql_results(self.endpoint, query)
            elif e.code == 403:
                print("403")
                return e.read().decode("utf8", "ignore")
            raise e
        except json.decoder.JSONDecodeError as e:
            print("JSONDecodeError. Query:")
            print(query)
            raise e


class ElasticsearchConnector:
    def __init__(self, es_cluster: str, es_user: str, es_password: str):
        self.endpoint = es_cluster
        self.es = Elasticsearch(
            [self.endpoint],
            http_auth=(es_user, es_password),
        )

    def get_doc_by_uri(self, index: str, uri: str, simplify=True) -> dict:
        """
        Get doc by SMG URI.
        """
        res = self.es.search(
            index=index, body={"query": {"term": {"uri.keyword": uri}}}
        )
        if len(res["hits"]["hits"]):
            res_doc = res["hits"]["hits"][0]

        return self._simplify_document(res_doc) if simplify else res_doc

    def _simplify_document(self, doc: dict) -> dict:
        """
        Extracts just the URI, topconcept, label and description from an Elasticsearch document.
        """

        return {
            "uri": doc["_id"],
            "topconcept": doc["_source"]["graph"]["@skos:hasTopConcept"]["@value"],
            "label": doc["_source"]["graph"]["@rdfs:label"]["@value"],
            "description": doc["_source"]["data"][
                "http://www.w3.org/2001/XMLSchema#description"
            ],
        }
