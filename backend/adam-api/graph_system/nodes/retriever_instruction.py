import json

from graph_system.states import SystemState
from utils.constants import INSTRUCTION_FILE_PATH

def retrieve_instruction(state: SystemState) -> dict:
    selected_theme = state.get("intent_category")

    if not selected_theme:
        raise ValueError("No selected_base_intent found in state. Cannot retrieve instruction.")

    if selected_theme == "dsp_support":
        return {
            **state,
            "in_dsp": True,
        }

    if selected_theme == "anomaly_det_run":
        return {
            **state,
            "in_anomaly_det_run": True,
        }

    if selected_theme != "dsp_support" and selected_theme != "anomaly_det_run":
        # Load the instruction blocks from the JSON file
        try:
            with open(INSTRUCTION_FILE_PATH, "r") as f:
                instruction_blocks = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load instruction file: {str(e)}")

        instruction_block = instruction_blocks.get(selected_theme)

        if not instruction_block:
            raise ValueError(f"Selected theme '{selected_theme}' not found in instruction blocks.")

        return {
            **state,
            "instruction_block": instruction_block,
        }
