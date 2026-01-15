from langchain_core.runnables import RunnableConfig
import traceback
import pandas as pd
import numpy as np

from utils.data_loader import load_data

def exec_code_tool(code: str, config: RunnableConfig) -> str:
    """
    Executes Python code defining main(df1, df2, ...) and returns the result.
    You must ensure the code defines a function `main(df1, df2, ...)`.
    """
    print("\n🔧 [Tool Execution] Running code:\n", code)
    
    try:
        user_email = config["configurable"]["user_email"]
        partner_name = config["configurable"]["partner_name"]
        
        Line_Items, Campaigns, Insertion_orders  = load_data(user_email, partner_name)
        
        # Prepare the namespace for code execution, ensuring pandas and numpy are available.
        namespace = {
            'pd': pd,
            'np': np,
            'Line_Items': Line_Items,
            'Campaigns': Campaigns,
            'Insertion_orders': Insertion_orders
        }
        
        exec(code, namespace)
        
        if "main" not in namespace:
            print("❌ [Tool Error] No main(df) found")
            return "Error: No function named 'main' found."
            
        result = namespace["main"](Line_Items, Campaigns, Insertion_orders)
        return result
    except FileNotFoundError:
        print(f"❌ [Tool Execution Error]: Some error when reading the data. I can retry if you want.")
        error_df = pd.DataFrame({"error": ["Some error when reading the data. I can retry if you want."]})
        return error_df
    except Exception as e:
        error_msg = traceback.format_exc()
        print("❌ [Tool Execution Error]:\n", error_msg + " I can retry if you want.")
        error_df = pd.DataFrame({"error": [f"Execution Error:\n{error_msg} I can retry if you want."]})
        return error_df