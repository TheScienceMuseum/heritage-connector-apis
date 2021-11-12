from pydantic import BaseModel, HttpUrl, Field
from typing import Union, Optional, List, Dict

"""
Request models
"""


class NeighboursRequest(BaseModel):
    entities: List[str]
    k: int = 10


class DistanceRequest(BaseModel):
    entity_a: str
    entity_b: str


class ConnectionsRequest(BaseModel):
    entities: List[str]
    labels: bool = False
    limit: Optional[int] = None


class LabelsRequest(BaseModel):
    uris: List[HttpUrl]


"""
Response models
"""


class SPARQLEntity(BaseModel):
    """One entity (e.g. subject, predicate or object) as returned by a SPARQL response. Also applies to subjectLabel, predicateLabel or objectLabel which are returned when `labels=True` for an endpoint."""

    type: str
    value: Union[HttpUrl, str]
    datatype: Optional[str]


class SPARQLPredicateObject(BaseModel):
    predicate: SPARQLEntity
    object: SPARQLEntity
    objectLabel: Optional[SPARQLEntity]


class SPARQLSubjectPredicate(BaseModel):
    subject: SPARQLEntity
    subjectLabel: Optional[SPARQLEntity]
    predicate: SPARQLEntity


class NeighboursResponse(BaseModel):
    __root__: Dict[str, List[list]]


class EntityConnections(BaseModel):
    from_field: List[SPARQLPredicateObject] = Field(alias="from")
    to: List[SPARQLSubjectPredicate]


class ConnectionsResponse(BaseModel):
    __root__: Dict[str, EntityConnections]


class LabelsResponse(BaseModel):
    __root__: Dict[str, Union[str, None]]
