"""Submodule for SPARQL queries
"""


def get_p_o(h: str, labels: bool):
    if labels:
        return f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT * WHERE {{
                <{h}> ?predicate ?object.
                OPTIONAL {{?object rdfs:label ?objectLabel}}.
            }}"""
    else:
        return f"""SELECT * WHERE {{<{h}> ?predicate ?object.}}"""
