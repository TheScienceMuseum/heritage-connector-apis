# heritage-connector-apis
APIs for the Heritage Connector project

**Commands:**

* set up (install requirements and pre-commit hooks): `make init`
* run: `python main.py`

**Config:**

All config is stored in `config.ini`, which is the same as in the heritage-connector repo, with the addition of:

``` ini
[APIs]
NEIGHBOURS_API = <endpoint for nearest neighbours api in heritage-connector-vectors>
```
