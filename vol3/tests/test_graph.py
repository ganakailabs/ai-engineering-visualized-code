"""Chapter 13: entity resolution, edge provenance, covered / excluded / unknown."""
import _path  # noqa: F401

import graph as G


def test_two_names_one_entity():
    assert G.resolve("NW charger") == G.resolve("USB-C charger (NW)") == "NW-500 charger"


def test_every_edge_has_a_source():
    assert all(len(e) == 4 and e[3] for e in G.EDGES)


def test_three_way_coverage():
    assert G.coverage("NW charger")[0] == "covered"
    assert G.coverage("NW-500 ear tips")[0] == "excluded"
    assert G.coverage("NW-500 cable")[0] == "unknown"


def test_missing_edge_is_not_no():
    assert G.naive_coverage("NW-500 cable") == "not covered"       # the BREAK
    assert G.coverage("NW-500 cable")[0] != "excluded"             # the FIX


def test_join_answers_the_one_hop_case():
    assert G.join_bundle("NW charger")[0][0] == "W2 bundle warranty"


if __name__ == "__main__":
    from _run import run_all
    run_all("test_graph")
