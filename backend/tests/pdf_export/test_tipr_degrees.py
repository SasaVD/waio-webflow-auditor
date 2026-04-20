"""TIPR engine must derive outbound/inbound counts from the adjacency matrix."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from tipr_engine import run_tipr_analysis


def test_tipr_computes_outbound_from_links_when_nodes_lack_stats():
    """Nodes stripped of inbound/outbound metadata must still yield correct
    counts, because the engine derives them from the adjacency matrix."""
    nodes = [
        {"id": "https://example.com/"},
        {"id": "https://example.com/a"},
        {"id": "https://example.com/b"},
        {"id": "https://example.com/c"},
    ]
    links = [
        {"source": "https://example.com/", "target": "https://example.com/a"},
        {"source": "https://example.com/", "target": "https://example.com/b"},
        {"source": "https://example.com/", "target": "https://example.com/c"},
        {"source": "https://example.com/a", "target": "https://example.com/"},
    ]
    result = run_tipr_analysis({"nodes": nodes, "links": links})
    assert result is not None

    page_by_url = {p["url"]: p for p in result["pages"]}
    home = page_by_url["https://example.com/"]
    page_a = page_by_url["https://example.com/a"]
    page_b = page_by_url["https://example.com/b"]

    # Homepage has 3 outbound edges and 1 inbound — matrix truth.
    assert home["outbound_count"] == 3
    assert home["inbound_count"] == 1
    # Page A is linked to from home, and links back to it.
    assert page_a["outbound_count"] == 1
    assert page_a["inbound_count"] == 1
    # Page B has only inbound.
    assert page_b["outbound_count"] == 0
    assert page_b["inbound_count"] == 1
