"""Submodule for SPARQL queries
"""


def get_p_o(h):
    return f"""SELECT * WHERE {{<{h}> ?predicate ?object.}}"""
