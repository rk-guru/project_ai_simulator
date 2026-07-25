'''simulation.py

Utility module for ordering equipment in a chemical process simulation.

The function :func:`order_equipments` performs a topological sort of the
equipment based on directed connections supplied by the API.  This ensures
that each piece of equipment is processed only after all of its upstream
dependencies have been handled.

Typical API payload (simplified)::

    {
        "equipment_count": 3,
        "connection_count": 2,
        "details": [
            {"id": "Feed-1784961079370", "name": "Feed-1", "type": "Feed", "specs": {...}},
            {"id": "Heater-1784961084430", "name": "Heater-1", "type": "Heater", "specs": {...}},
            {"id": "Product-1784961087461", "name": "Product-1", "type": "Product", "specs": {}}
        ],
        "connections": [
            {"source_id": "Feed-1784961079370", "target_id": "Heater-1784961084430"},
            {"source_id": "Heater-1784961084430", "target_id": "Product-1784961087461"}
        ]
    }

The ``connections`` list defines the directed flow of material: ``source_id`` →
``target_id``.  If the ``connections`` key is missing the function falls back to
the order in which the equipment appears in the ``details`` array.

The module also provides a thin ``run_simulation`` entry point that can be wired
to a UI button (e.g. a React ``onClick`` handler).  The entry point simply
orders the equipment and prints a placeholder processing message; in a real
application the loop would invoke the appropriate process model for each piece
of equipment.
'''  # noqa: E501

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class Equipment:
    """Simple value‑object representing a piece of process equipment.

    The ``specs`` field is kept generic because different equipment types have
    wildly different specifications (temperature, pressure, flow rate, etc.).
    """

    id: str
    name: str
    type: str
    specs: dict


@dataclass(frozen=True)
class Connection:
    """Directed connection between two pieces of equipment.

    ``source_id`` is the upstream equipment, ``target_id`` is the downstream
    equipment that receives the stream.
    """

    source_id: str
    target_id: str


def _parse_equipment(details: Sequence[dict]) -> Dict[str, Equipment]:
    """Convert the raw ``details`` list from the API into a mapping.

    Args:
        details: List of dictionaries each containing ``id``, ``name``, ``type``
            and ``specs``.

    Returns:
        Mapping from equipment ID to :class:`Equipment` instances.
    """
    equipment_by_id: Dict[str, Equipment] = {}
    for entry in details:
        eq = Equipment(
            id=entry["id"],
            name=entry.get("name", ""),
            type=entry.get("type", ""),
            specs=entry.get("specs", {}),
        )
        equipment_by_id[eq.id] = eq
    return equipment_by_id


def _parse_connections(raw: Sequence[dict] | None) -> List[Connection]:
    """Parse the optional ``connections`` list.

    The API may name the keys differently (e.g. ``source``/``target``).  This
    helper normalises to ``source_id``/``target_id`` when possible.
    """
    if not raw:
        return []
    connections: List[Connection] = []
    for entry in raw:
        # Accept a few common key names for robustness.
        source = entry.get("source_id") or entry.get("source") or entry.get("from")
        target = entry.get("target_id") or entry.get("target") or entry.get("to")
        if source and target:
            connections.append(Connection(source_id=source, target_id=target))
    return connections


def order_equipments(api_data: dict) -> List[Equipment]:
    """Return a list of :class:`Equipment` objects in a valid processing order.

    The algorithm performs a **topological sort** (Kahn's algorithm) on the
    directed graph defined by ``connections``.  Equipment with no upstream
    dependencies (indegree ``0``) appear first.  If the graph contains a cycle,
    a :class:`ValueError` is raised because a deterministic order does not
    exist.

    Args:
        api_data: Dictionary received from the backend API.  Expected keys are
            ``details`` (list of equipment dicts) and optionally ``connections``
            (list of directed edges).

    Returns:
        List of :class:`Equipment` objects ordered for simulation.
    """
    details = api_data.get("details", [])
    if not details:
        return []

    equipment_by_id = _parse_equipment(details)
    connections = _parse_connections(api_data.get("connections"))

    # If no explicit connections are provided, fall back to the order supplied
    # by the API – this mirrors the behaviour of the original example payload.
    if not connections:
        return list(equipment_by_id.values())

    # Build adjacency list and indegree map for Kahn's algorithm.
    adj: Dict[str, List[str]] = {eid: [] for eid in equipment_by_id}
    indegree: Dict[str, int] = {eid: 0 for eid in equipment_by_id}

    for conn in connections:
        src, dst = conn.source_id, conn.target_id
        # Guard against malformed connections referencing unknown IDs.
        if src not in equipment_by_id or dst not in equipment_by_id:
            continue
        adj[src].append(dst)
        indegree[dst] += 1

    # Queue of nodes with zero indegree.
    zero_indeg = deque([eid for eid, deg in indegree.items() if deg == 0])
    ordered: List[Equipment] = []

    while zero_indeg:
        current_id = zero_indeg.popleft()
        ordered.append(equipment_by_id[current_id])
        for neighbour in adj[current_id]:
            indegree[neighbour] -= 1
            if indegree[neighbour] == 0:
                zero_indeg.append(neighbour)

    if len(ordered) != len(equipment_by_id):
        # A cycle exists – we cannot determine a deterministic order.
        raise ValueError("Circular dependency detected among equipment connections.")

    return ordered


def simulation_calculation(api_data: dict) -> Any:
    """Entry‑point that can be wired to a UI ``Run Simulation`` button.

    The function orders the equipment and then invokes the SimulationOrchestrator
    to perform thermodynamic calculations and return a detailed results table.
    """
    from equipment_codes.orchestrator import SimulationOrchestrator

    ordered_eq = order_equipments(api_data)
    connections = api_data.get("connections", [])

    orchestrator = SimulationOrchestrator()
    results_table = orchestrator.execute_simulation(ordered_eq, connections)

    # Print as a formatted table for debugging/console output
    if results_table:
        headers = [
            "Stream Name", "Equipment Name", "Equipment", "Temperature",
            "Pressure", "Molar Flowrate", "Mass Flowrate", "Vapor Fraction",
            "Total Molar Composition (Mass Fraction)", "Liquid Molar Composition",
            "Vapor Molar Composition", "Enthalpy", "Energy Change"
        ]
        header_row = " | ".join(f"{h:25}" for h in headers)
        print(header_row)
        print("-" * len(header_row))
        for row in results_table:
            print(" | ".join(f"{str(row.get(h, '')):25}" for h in headers))

    return results_table


# ---------------------------------------------------------------------------
# Example usage (executed only when the module is run directly)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    example_payload = {
        "equipment_count": 3,
        "connection_count": 2,
        "details": [
            {
                "id": "Feed-1784961079370",
                "name": "Feed-1",
                "type": "Feed",
                "specs": {
                    "temperature": 300,
                    "pressure": 101325,
                    "flowRate": 10,
                    "compounds": [{"name": "Benzene", "moleFraction": 1}],
                },
            },
            {
                "id": "Heater-1784961084430",
                "name": "Heater-1",
                "type": "Heater",
                "specs": {"outletTemperature": 350},
            },
            {
                "id": "Product-1784961087461",
                "name": "Product-1",
                "type": "Product",
                "specs": {},
            },
        ],
        "connections": [
            {"source_id": "Feed-1784961079370", "target_id": "Heater-1784961084430"},
            {"source_id": "Heater-1784961084430", "target_id": "Product-1784961087461"},
        ],
    }
    example_payload={'equipment_count': 9, 'connection_count': 8, 'details': [{'id': 'Feed-1784961079370', 'name': 'Feed-1', 'type': 'Feed', 'specs': {'temperature': 300, 'pressure': 101325, 'flowRate': 10, 'compounds': [{'name': 'Benzene', 'moleFraction': 1}]}}, {'id': 'Heater-1784961084430', 'name': 'Heater-1', 'type': 'Heater', 'specs': {'outletTemperature': 350}}, {'id': 'Pump-1784987394970', 'name': 'Pump-1', 'type': 'Pump', 'specs': {'outletPressure': 200000}}, {'id': 'Feed-1784987402328', 'name': 'Feed-2', 'type': 'Feed', 'specs': {'temperature': 298, 'pressure': 101325, 'flowRate': 5, 'compounds': [{'name': 'Benzene', 'moleFraction': 1}]}}, {'id': 'Mixer-1784987404410', 'name': 'Mixer-1', 'type': 'Mixer', 'specs': {}}, {'id': 'Heater-1784987409581', 'name': 'Heater-2', 'type': 'Heater', 'specs': {'outletTemperature': 350}}, {'id': 'Flash-1784987412805', 'name': 'Flash-1', 'type': 'Flash', 'specs': {'temperature': 300, 'pressure': 101325}}, {'id': 'Product-1784987437473', 'name': 'Product-1', 'type': 'Product', 'specs': {}}, {'id': 'Product-1784987439229', 'name': 'Product-2', 'type': 'Product', 'specs': {}}], 'connections': [{'source_id': 'Feed-1784961079370', 'target_id': 'Heater-1784961084430'}, {'source_id': 'Heater-1784961084430', 'target_id': 'Pump-1784987394970'}, {'source_id': 'Pump-1784987394970', 'target_id': 'Mixer-1784987404410'}, {'source_id': 'Feed-1784987402328', 'target_id': 'Mixer-1784987404410'}, {'source_id': 'Mixer-1784987404410', 'target_id': 'Heater-1784987409581'}, {'source_id': 'Heater-1784987409581', 'target_id': 'Flash-1784987412805'}, {'source_id': 'Flash-1784987412805', 'target_id': 'Product-1784987437473'}, {'source_id': 'Flash-1784987412805', 'target_id': 'Product-1784987439229'}]}


    print("--- Equipment processing order ---")
    results = simulation_calculation(example_payload)
    print("\nSimulation completed. Results table generated.")
