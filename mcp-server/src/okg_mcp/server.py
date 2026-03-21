"""MCP server for the Open Knowledge Graphs semantic search API.

Provides tools to search 1,800+ ontologies, vocabularies, taxonomies,
and semantic software tools cataloged from Wikidata.
"""

from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from okg_mcp.client import api_get, close_http_client, dual_search, handle_api_error
from okg_mcp.format import format_catalog, format_search_results
from okg_mcp.models import OntologySearchInput, SearchInput, SoftwareSearchInput


@asynccontextmanager
async def lifespan(_mcp: FastMCP):
    """Manage shared resources across the server lifecycle."""
    yield
    await close_http_client()


mcp = FastMCP("okg_mcp", lifespan=lifespan)


@mcp.tool(
    name="okg_get_catalog_info",
    annotations={
        "title": "Get OKG Catalog Info",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def okg_get_catalog_info() -> str:
    """Get metadata about the Open Knowledge Graphs catalog.

    Returns the catalog name, description, total counts of ontologies and
    software tools, available domain categories, and API endpoint descriptions.
    Use this to understand what's available before searching.

    Returns:
        str: Markdown-formatted catalog overview including:
            - Total ontologies and software counts
            - List of 9 domain categories for filtering
            - Available API endpoints and their parameters
    """
    try:
        data = await api_get("/")
        return format_catalog(data)
    except Exception as e:
        return handle_api_error(e)


@mcp.tool(
    name="okg_search",
    annotations={
        "title": "Search All OKG Resources",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def okg_search(params: SearchInput) -> str:
    """Semantic search across all Open Knowledge Graphs resources.

    Searches ontologies, vocabularies, taxonomies, and semantic software
    using vector similarity. Results are ranked by relevance score.

    Args:
        params (SearchInput): Search parameters:
            - q (str): Search query, natural language or keywords (required)
            - category (Optional[Category]): Filter by domain category
            - type (Optional[ResourceType]): Filter by 'ontology' or 'software'
            - limit (Optional[int]): Max results 1-100 (default: 20)

    Returns:
        str: Markdown-formatted search results, each with:
            - Title and relevance score
            - Description, Wikidata ID, types, category
            - Homepage URL, licenses, version info

    Examples:
        - "Find healthcare ontologies" -> q="healthcare", category="Life Sciences & Healthcare"
        - "RDF tools" -> q="RDF tools", type="software"
        - "geospatial vocabulary" -> q="geospatial vocabulary"
    """
    try:
        query_params: dict = {"q": params.q, "limit": params.limit}
        datasets = ["ontologies", "software"]
        if params.category:
            query_params["category"] = params.category.value
        if params.type:
            query_params["type"] = params.type.value
            datasets = ["ontologies"] if params.type.value == "ontology" else ["software"]

        data = await dual_search(
            "/search", query_params, datasets,
            category=params.category.value if params.category else None,
            limit=params.limit or 20,
        )
        return format_search_results(data)
    except Exception as e:
        return handle_api_error(e)


@mcp.tool(
    name="okg_search_ontologies",
    annotations={
        "title": "Search OKG Ontologies",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def okg_search_ontologies(params: OntologySearchInput) -> str:
    """Search for ontologies, vocabularies, and taxonomies in Open Knowledge Graphs.

    Use this when looking specifically for knowledge representation schemas,
    controlled vocabularies, or classification systems — not software tools.

    Args:
        params (OntologySearchInput): Search parameters:
            - q (str): Search query (required)
            - category (Optional[Category]): Filter by domain category
            - limit (Optional[int]): Max results 1-100 (default: 20)

    Returns:
        str: Markdown-formatted results with title, score, Wikidata link,
             types, category, homepage, and license information.

    Examples:
        - "SNOMED CT" -> q="SNOMED CT"
        - "Library classification" -> q="library classification", category="Library & Cultural Heritage"
    """
    try:
        query_params: dict = {"q": params.q, "limit": params.limit}
        if params.category:
            query_params["category"] = params.category.value

        data = await dual_search(
            "/ontologies", query_params, ["ontologies"],
            category=params.category.value if params.category else None,
            limit=params.limit or 20,
        )
        return format_search_results(data)
    except Exception as e:
        return handle_api_error(e)


@mcp.tool(
    name="okg_search_software",
    annotations={
        "title": "Search OKG Software",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def okg_search_software(params: SoftwareSearchInput) -> str:
    """Search for semantic software tools in Open Knowledge Graphs.

    Finds triple stores, RDF libraries, ontology editors, graph databases,
    SPARQL engines, and other semantic web tools.

    Args:
        params (SoftwareSearchInput): Search parameters:
            - q (str): Search query (required)
            - limit (Optional[int]): Max results 1-100 (default: 20)

    Returns:
        str: Markdown-formatted results with title, score, Wikidata link,
             homepage, latest version, and release date.

    Examples:
        - "triple store" -> q="triple store"
        - "RDF parser Python" -> q="RDF parser Python"
        - "ontology editor" -> q="ontology editor"
    """
    try:
        query_params: dict = {"q": params.q, "limit": params.limit}

        data = await dual_search(
            "/software", query_params, ["software"],
            limit=params.limit or 20,
        )
        return format_search_results(data)
    except Exception as e:
        return handle_api_error(e)


def main() -> None:
    """Entry point for the OKG MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
