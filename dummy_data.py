import random
import json

def generate_dummy_chat_response(user_input):
    responses = [
        "Based on the process analysis, I recommend increasing the reactor temperature by 5C to improve conversion.",
        "The current flow diagram shows a bottleneck at the distillation column. Consider adding a secondary reflux stream.",
        "According to the uploaded documentation, the pressure drop in the heat exchanger is within nominal limits.",
        "I have analyzed the chemical composition. The ethylene byproduct concentration is slightly higher than expected.",
        "The simulation suggests that optimizing the feed flowrate to 120 mol/s will maximize the yield of ethylbenzene.",
        "I've detected a potential issue in Step 2: Heater. The energy balance indicates an efficiency drop of 3%.",
        "From a chemical engineering perspective, the current catalyst loading is sufficient for the target conversion rate."
    ]
    return random.choice(responses)

def generate_dummy_flow_diagram():
    equipment = ["Reactor_1", "Heater_1", "Cooler_1", "Pump_1", "Flash_1", "Distillation_1"]
    equipment_list = {eq: random.choice(["Reactor", "Heater", "Cooler", "Pump", "Flash", "Distillation"]) for eq in equipment}

    connections = []
    for i, eq in enumerate(equipment):
        outlets = [f"{eq}_outlet"] if i < len(equipment)-1 else []
        connections.append({
            "equipment": eq,
            "outlet": outlets,
            "Param": {"temp": random.randint(50, 300), "pres": random.randint(1, 50)}
        })

    return {
        "Equipment_list": equipment_list,
        "Connection": connections
    }

def generate_dummy_simulation_results(project_data):
    # project_data might contain nodes/edges, we can use them to generate more results
    nodes = project_data.get("nodes", [])
    if not nodes:
        # Default dummy results if no nodes provided
        equipment = ["Reactor_1", "Heater_1", "Cooler_1", "Distillation_1"]
    else:
        equipment = [node.get("data", {}).get("label", f"Eq_{i}") for i, node in enumerate(nodes)]

    results = []
    parameters = ["Conversion", "Temperature", "Pressure", "Flowrate", "Purity"]
    statuses = ["Nominal", "Warning", "Critical"]

    for i, eq in enumerate(equipment):
        for param in parameters:
            results.append({
                "id": i * len(parameters) + parameters.index(param) + 1,
                "Equipment": eq,
                "Parameter": param,
                "Value": f"{random.uniform(10, 500):.2f} {'%' if param == 'Conversion' else 'C' if param == 'Temperature' else 'bar' if param == 'Pressure' else 'mol/s' if param == 'Flowrate' else '%'}",
                "Status": random.choice(statuses)
            })
    return results
