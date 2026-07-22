import json

# This string serves as a reference for the LLM to understand available equipment,
# their parameters, and connection rules for generating PFDs.
EQUIPMENT_REFERENCE_JSON = """
{
  "equipments": {
    "Feed": {
      "description": "Feed stream input",
      "parameters": {
        "temperature": {"unit": "K", "type": "number"},
        "pressure": {"unit": "Pa", "type": "number"},
        "flowRate": {"unit": "mol/s", "type": "number"}
      },
      "composition": {
        "description": "Molar composition of the feed",
        "structure": [
          {
            "name": "chemical_name",
            "moleFraction": "number (0-1)"
          }
        ],
        "constraint": "Sum of moleFractions must equal 1.0"
      },
      "connections": {
        "maxInputs": 0,
        "maxOutputs": 1,
        "ports": {
          "inputs": [],
          "outputs": ["out"]
        }
      }
    },
    "Product": {
      "description": "Final product stream",
      "parameters": {},
      "connections": {
        "maxInputs": 1,
        "maxOutputs": 0,
        "ports": {
          "inputs": ["in"],
          "outputs": []
        }
      }
    },
    "Tank": {
      "description": "Storage tank / Equilibrium flash vessel",
      "parameters": {
        "temperature": {"unit": "K", "type": "number"},
        "pressure": {"unit": "Pa", "type": "number"}
      },
      "connections": {
        "maxInputs": 1,
        "maxOutputs": 2,
        "ports": {
          "inputs": ["in"],
          "outputs": ["out1", "out2"]
        }
      }
    },
    "Flash": {
      "description": "Flash separator",
      "parameters": {
        "temperature": {"unit": "K", "type": "number"},
        "pressure": {"unit": "Pa", "type": "number"}
      },
      "connections": {
        "maxInputs": 1,
        "maxOutputs": 2,
        "ports": {
          "inputs": ["inlet"],
          "outputs": ["vapor", "liquid"]
        }
      }
    },
    "Reactor": {
      "description": "Chemical reactor",
      "parameters": {
        "temperature": {"unit": "K", "type": "number"},
        "pressure": {"unit": "Pa", "type": "number"},
        "conversion": {"unit": "%", "type": "number"}
      },
      "stoichiometry": {
        "reactants": [
          {
            "compound": "chemical_name",
            "stoichiometry": "number"
          }
        ],
        "products": [
          {
            "compound": "chemical_name",
            "stoichiometry": "number"
          }
        ]
      },
      "connections": {
        "maxInputs": 1,
        "maxOutputs": 2,
        "ports": {
          "inputs": ["in"],
          "outputs": ["out1", "out2"]
        }
      }
    },
    "Pump": {
      "description": "Liquid pump",
      "parameters": {
        "outletPressure": {"unit": "Pa", "type": "number"}
      },
      "connections": {
        "maxInputs": 1,
        "maxOutputs": 1,
        "ports": {
          "inputs": ["in"],
          "outputs": ["out"]
        }
      }
    },
    "Compressor": {
      "description": "Gas compressor",
      "parameters": {
        "outletPressure": {"unit": "Pa", "type": "number"}
      },
      "connections": {
        "maxInputs": 1,
        "maxOutputs": 1,
        "ports": {
          "inputs": ["in"],
          "outputs": ["out"]
        }
      }
    },
    "Expander": {
      "description": "Gas expander / Turbine",
      "parameters": {
        "outletPressure": {"unit": "Pa", "type": "number"}
      },
      "connections": {
        "maxInputs": 1,
        "maxOutputs": 1,
        "ports": {
          "inputs": ["in"],
          "outputs": ["out"]
        }
      }
    },
    "Heater": {
      "description": "Process heater",
      "parameters": {
        "outletTemperature": {"unit": "K", "type": "number"}
      },
      "connections": {
        "maxInputs": 1,
        "maxOutputs": 1,
        "ports": {
          "inputs": ["in"],
          "outputs": ["out"]
        }
      }
    },
    "Cooler": {
      "description": "Process cooler",
      "parameters": {
        "outletTemperature": {"unit": "K", "type": "number"}
      },
      "connections": {
        "maxInputs": 1,
        "maxOutputs": 1,
        "ports": {
          "inputs": ["in"],
          "outputs": ["out"]
        }
      }
    },
    "HeatExchanger": {
      "description": "Shell and tube heat exchanger",
      "parameters": {},
      "connections": {
        "maxInputs": 2,
        "maxOutputs": 2,
        "ports": {
          "inputs": ["hot-in", "cold-in"],
          "outputs": ["hot-out", "cold-out"]
        }
      }
    },
    "DistillationColumn": {
      "description": "Fractional distillation column",
      "parameters": {
        "stages": {"unit": "count", "type": "number"},
        "condenserType": {"type": "string", "options": ["Total", "Partial"]},
        "pressure": {"unit": "Pa", "type": "number"},
        "temperature": {"unit": "K", "type": "number"},
        "refluxRatio": {"unit": "ratio", "type": "number"}
      },
      "connections": {
        "maxInputs": 1,
        "maxOutputs": 2,
        "ports": {
          "inputs": ["feed"],
          "outputs": ["distillate", "bottoms"]
        }
      }
    },
    "Mixer": {
      "description": "Stream mixer",
      "parameters": {},
      "connections": {
        "maxInputs": "Infinity",
        "maxOutputs": 1,
        "ports": {
          "inputs": ["in"],
          "outputs": ["out"]
        }
      }
    },
    "Splitter": {
      "description": "Stream splitter",
      "parameters": {},
      "connections": {
        "maxInputs": 1,
        "maxOutputs": "Infinity",
        "ports": {
          "inputs": ["in"],
          "outputs": ["out"]
        }
      }
    }
  }
}
"""

# This structured list represents the exact format required by the frontend
# for the `generateFlowsheetFromStructuredData` function.
EQUIPMENT_FRONTEND_SCHEMA_JSON = """
[
  {
    "equipment": "Feed",
    "equipment_id": "Feed_1",
    "params": {
      "Temperature": 298.15,
      "Pressure": 101325,
      "Flow Rate": 1.0
    },
    "outlets": ["Next_Equipment_ID"]
  },
  {
    "equipment": "Tank",
    "equipment_id": "Tank_1",
    "params": {
      "Temperature": 298.15,
      "Pressure": 101325
    },
    "outlets": ["Out1_ID", "Out2_ID"]
  },
  {
    "equipment": "Flash",
    "equipment_id": "Flash_1",
    "params": {
      "Temperature": 350.0,
      "Pressure": 200000
    },
    "outlets": ["Vapor_ID", "Liquid_ID"]
  },
  {
    "equipment": "Reactor",
    "equipment_id": "Reactor_1",
    "params": {
      "Temperature": 500.0,
      "Pressure": 1000000,
      "Conversion": 0.8
    },
    "outlets": ["Out1_ID", "Out2_ID"]
  },
  {
    "equipment": "Pump",
    "equipment_id": "Pump_1",
    "params": {
      "Outlet Pressure": 500000
    },
    "outlets": ["Next_ID"]
  },
  {
    "equipment": "Compressor",
    "equipment_id": "Compressor_1",
    "params": {
      "Outlet Pressure": 1000000
    },
    "outlets": ["Next_ID"]
  },
  {
    "equipment": "Expander",
    "equipment_id": "Expander_1",
    "params": {
      "Outlet Pressure": 101325
    },
    "outlets": ["Next_ID"]
  },
  {
    "equipment": "Heater",
    "equipment_id": "Heater_1",
    "params": {
      "Outlet Temperature": 450.0
    },
    "outlets": ["Next_ID"]
  },
  {
    "equipment": "Cooler",
    "equipment_id": "Cooler_1",
    "params": {
      "Outlet Temperature": 300.0
    },
    "outlets": ["Next_ID"]
  },
  {
    "equipment": "HeatExchanger",
    "equipment_id": "HX_1",
    "params": {},
    "outlets": ["Hot_Out_ID", "Cold_Out_ID"]
  },
  {
    "equipment": "DistillationColumn",
    "equipment_id": "Col_1",
    "params": {
      "Stages": 20,
      "Condenser Type": "Total",
      "Pressure": 101325,
      "Temperature": 350.0,
      "Reflux Ratio": 1.5
    },
    "outlets": ["Distillate_ID", "Bottoms_ID"]
  },
  {
    "equipment": "Mixer",
    "equipment_id": "Mixer_1",
    "params": {},
    "outlets": ["Next_ID"]
  },
  {
    "equipment": "Splitter",
    "equipment_id": "Splitter_1",
    "params": {},
    "outlets": ["Out1_ID", "Out2_ID", "OutN_ID"]
  },
  {
    "equipment": "Product",
    "equipment_id": "Product_1",
    "params": {},
    "outlets": []
  }
]
"""

def get_equipment_reference():
    return {
        "reference": json.loads(EQUIPMENT_REFERENCE_JSON),
        "frontend_schema": json.loads(EQUIPMENT_FRONTEND_SCHEMA_JSON)
    }

if __name__ == "__main__":
    print(json.dumps(get_equipment_reference(), indent=2))
