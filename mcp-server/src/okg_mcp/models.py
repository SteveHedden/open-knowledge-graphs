"""Pydantic input models and response types for the OKG MCP server."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    HEALTHCARE = "Healthcare"
    LIFE_SCIENCES_SPECIFIC = "Life sciences"
    FINANCIAL_SERVICES = "Financial services"
    SUPPLY_CHAIN = "Supply chain and commerce"


class ResourceType(str, Enum):
    """Type filter for search results."""

    ONTOLOGY = "ontology"
    SOFTWARE = "software"


class SharedSearchInput(BaseModel):
    @model_validator(mode="after")
    def require_query_or_tags(self):
        if not self.q and not any((self.tools, self.activities, self.domains)):
            raise ValueError("Provide a query or at least one shared tag filter")
        return self


class SearchInput(SharedSearchInput):
    """Input for searching across all OKG resources."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tools: list[str] = Field(default_factory=list, description="Tool/resource URIs; OR within this dimension")
    activities: list[str] = Field(default_factory=list, description="Activity/use-case URIs; OR within this dimension")
    domains: list[str] = Field(default_factory=list, description="Domain URIs; includes descendants; AND across dimensions")

    q: str = Field(
        default="",
        description="Search query; optional when shared tag filters are supplied",
        max_length=200,
    )
    category: Category | None = Field(
        default=None,
        description="Filter by domain category",
    )
    type: ResourceType | None = Field(
        default=None,
        description="Filter by resource type: 'ontology' or 'software'",
    )
    limit: int | None = Field(
        default=20,
        description="Maximum results to return (1-100, default 20)",
        ge=1,
        le=100,
    )


class OntologySearchInput(SharedSearchInput):
    """Input for searching ontologies, vocabularies, and taxonomies."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tools: list[str] = Field(default_factory=list, description="Tool/resource URIs; OR within this dimension")
    activities: list[str] = Field(default_factory=list, description="Activity/use-case URIs; OR within this dimension")
    domains: list[str] = Field(default_factory=list, description="Domain URIs; includes descendants; AND across dimensions")

    q: str = Field(
        default="",
        description="Search query; optional when shared tag filters are supplied",
        max_length=200,
    )
    category: Category | None = Field(
        default=None,
        description="Filter by domain category",
    )
    limit: int | None = Field(
        default=20,
        description="Maximum results to return (1-100, default 20)",
        ge=1,
        le=100,
    )


class SoftwareSearchInput(SharedSearchInput):
    """Input for searching semantic software tools."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tools: list[str] = Field(default_factory=list, description="Tool/resource URIs; OR within this dimension")
    activities: list[str] = Field(default_factory=list, description="Activity/use-case URIs; OR within this dimension")
    domains: list[str] = Field(default_factory=list, description="Domain URIs; includes descendants; AND across dimensions")

    q: str = Field(
        default="",
        description="Search query; optional when shared tag filters are supplied",
        max_length=200,
    )
    limit: int | None = Field(
        default=20,
        description="Maximum results to return (1-100, default 20)",
        ge=1,
        le=100,
    )
