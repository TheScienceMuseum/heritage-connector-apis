# heritage-connector-apis
APIs for the Heritage Connector project

**Commands:**

* set up (install requirements and pre-commit hooks): `make init`
* run: `python main.py`

**Config/environment:**

All config is stored in `.env`.

``` env
SPARQL_ENDPOINT=<public-sparql-endpoint>
ELASTIC_SEARCH_CLUSTER=<elastic-cluster>
ELASTIC_SEARCH_USER=<username>
ELASTIC_SEARCH_PASSWORD=<secure-password>
ELASTIC_SEARCH_INDEX=heritageconnector
ELASTIC_SEARCH_WIKI_INDEX=wikidump
VECTORS_API=<endpoint for vectors apis in heritage-connector-vectors>
```
