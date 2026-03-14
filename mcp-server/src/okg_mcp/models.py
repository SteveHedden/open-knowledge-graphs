"""Pydantic input models and response types for the OKG MCP server."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Category(str, Enum):
    """Domain categories for knowledge graph resources."""

    LIFE_SCIENCES = "Life Sciences & Healthcare"
    GEOSPATIAL = "Geospatial"
    GOVERNMENT = "Government & Public Sector"
    INTERNATIONAL_DEV = "International Development"
    FINANCE = "Finance & Business"
    LIBRARY = "Library & Cultural Heritage"
    TECHNOLOGY = "Technology & Web"
    ENVIRONMENT = "Environment & Agriculture"
    GENERAL = "General / Cross-domain"


class ResourceType(str, Enum):
    """Type filter for search results."""

    ONTOLOGY = "ontology"
    SOFTWARE = "software"


class SearchInput(BaseModel):
    """Input for searching across all OKG resources."""

    model_config = ConfigDict(str_strip_whitespace=True)

    q: str = Field(
        ...,
        description="Search query (natural language or keywords)",
        min_length=1,
        max_length=200,
    )
    category: Optional[Category] = Field(
        default=None,
        description="Filter by domain category",
    )
    type: Optional[ResourceType] = Field(
        default=None,
        description="Filter by resource type: 'ontology' or 'software'",
    )
    limit: Optional[int] = Field(
        default=20,
        description="Maximum results to return (1-100, default 20)",
        ge=1,
        le=100,
    )


class OntologySearchInput(BaseModel):
    """Input for searching ontologies, vocabularies, and taxonomies."""

    model_config = ConfigDict(str_strip_whitespace=True)

    q: str = Field(
        ...,
        description="Search query (natural language or keywords)",
        min_length=1,
        max_length=200,
    )
    category: Optional[Category] = Field(
        default=None,
        description="Filter by domain category",
    )
    limit: Optional[int] = Field(
        default=20,
        description="Maximum results to return (1-100, default 20)",
        ge=1,
        le=100,
    )


class SoftwareSearchInput(BaseModel):
    """Input for searching semantic software tools."""

    model_config = ConfigDict(str_strip_whitespace=True)

    q: str = Field(
        ...,
        description="Search query (natural language or keywords)",
        min_length=1,
        max_length=200,
    )
    limit: Optional[int] = Field(
        default=20,
        description="Maximum results to return (1-100, default 20)",
        ge=1,
        le=100,
    )
