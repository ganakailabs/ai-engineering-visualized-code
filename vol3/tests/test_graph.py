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


# Review probes: the old walk followed only the first outgoing edge.
DEAD_END = ("NW-500 charger", "PART_OF", "Old Charger Kit", "catalogue 2024 p.2")


def test_dead_end_branch_listed_first_does_not_hide_path():
    edges = [DEAD_END] + G.EDGES
    verdict, hops = G.coverage("NW charger", edges=edges)
    assert verdict == "covered" and hops[-1][2] == "W2 bundle warranty"


def test_edge_order_does_not_change_answer():
    import random
    rng = random.Random(7)
    base = G.coverage("NW charger", edges=[DEAD_END] + G.EDGES)
    for _ in range(20):
        edges = [DEAD_END] + G.EDGES
        rng.shuffle(edges)
        assert G.coverage("NW charger", edges=edges) == base


def test_cycle_terminates_unknown():
    edges = [("A", "PART_OF", "B", "s1"), ("B", "PART_OF", "A", "s2")]
    assert G.coverage("A", edges=edges) == ("unknown", [])


def test_path_longer_than_bound_is_unknown():
    edges = [("A", "PART_OF", "B", "s"), ("B", "PART_OF", "C", "s"),
             ("C", "PART_OF", "D", "s"), ("D", "COVERED_BY", "W2 bundle warranty", "s")]
    assert G.coverage("A", edges=edges)[0] == "unknown"
    assert G.coverage("A", edges=edges, max_hops=4)[0] == "covered"


def test_unknown_part_and_exclusion():
    assert G.coverage("Some other gadget") == ("unknown", [])
    assert G.coverage("NW-500 ear tips", edges=[DEAD_END] + G.EDGES)[0] == "excluded"


if __name__ == "__main__":
    from _run import run_all
    run_all("test_graph")
