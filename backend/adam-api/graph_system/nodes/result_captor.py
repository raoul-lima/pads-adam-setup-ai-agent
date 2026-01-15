from graph_system.states import SystemState
import pandas as pd

def capture_result(state: SystemState) -> dict:
    """Checks if the result from the previous step is a pandas DataFrame, a dict of DataFrames, or a list of pandas DataFrames.

    Returns:
        A dictionary containing the result if it's valid (e.g., {"result": result}).

    Raises:
        TypeError: If the result is not a pandas DataFrame, dict of DataFrames, or a list of pandas DataFrames,
                   or if it's a list/dict containing non-DataFrame items.
        KeyError: If the 'result' key is not found in the state (implicitly handled by state.get, returning None).
    """
    result_value = state.get("result") # Get the result, could be None if key doesn't exist

    if result_value is None:
        raise TypeError("No 'result' key found in the execution state or result is None.")

    if isinstance(result_value, pd.DataFrame):
        return {"result": result_value}  # Valid: DataFrame

    if isinstance(result_value, dict):
        if not result_value: # Empty dict is valid
            return {"result": result_value}
        if all(isinstance(item, pd.DataFrame) for item in result_value.values()):
            return {"result": result_value}  # Valid: Dict of DataFrames
        else:
            # Invalid: Dict, but contains non-DataFrame values
            offending_types = list(set([type(item).__name__ for item in result_value.values() if not isinstance(item, pd.DataFrame)]))
            error_message = (
                f"Result is a dictionary, but not all values are pandas DataFrames. "
                f"Encountered non-DataFrame types: {offending_types}."
            )
            raise TypeError(error_message)

    if isinstance(result_value, list):
        if not result_value: # Empty list is valid
            return {"result": result_value}
        if all(isinstance(item, pd.DataFrame) for item in result_value):
            return {"result": result_value}  # Valid: List of DataFrames
        else:
            # Invalid: List, but contains non-DataFrame items
            offending_types = list(set([type(item).__name__ for item in result_value if not isinstance(item, pd.DataFrame)]))
            error_message = (
                f"Result is a list, but not all items are pandas DataFrames. "
                f"Encountered non-DataFrame types: {offending_types}."
            )
            raise TypeError(error_message)
    else:
        # Invalid: Not a DataFrame, dict, or list (e.g., string, int, etc.)
        error_message = (
            f"Result must be a pandas DataFrame, a dictionary of DataFrames, or a list of pandas DataFrames. "
            f"Received type: {type(result_value).__name__}."
        )
        raise TypeError(error_message)