"""Submodule for SPARQL queries
"""
from typing import List


def get_p_o(h: str, labels: bool, limit: int = None):
    if labels:
        query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT * WHERE {{
                <{h}> ?predicate ?object.
                OPTIONAL {{?object rdfs:label ?objectLabel}}.
            }}"""
    else:
        query = f"""SELECT * WHERE {{<{h}> ?predicate ?object.}}"""

    if limit:
        query += f"LIMIT {limit}"

    return query


def get_s_p(h: str, labels: bool, limit: int = None):
    if labels:
        query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT * WHERE {{
                ?subject ?predicate <{h}>.
                OPTIONAL {{?subject rdfs:label ?subjectLabel}}.
            }}"""
    else:
        query = f"""SELECT * WHERE {{?subject ?predicate <{h}>.}}"""

    if limit:
        query += f"LIMIT {limit}"

    return query


def get_labels(entities: List[str]):
    ent_str = " ".join([f"<{ent}>" for ent in entities])

    return f"""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?s ?sLabel WHERE {{
        VALUES ?s {{{ent_str}}}.
        OPTIONAL {{?s rdfs:label ?sLabel}}.
    }} """
