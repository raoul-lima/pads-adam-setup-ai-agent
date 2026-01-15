import pandas as pd
import json
from typing import Dict, List, Any
from datetime import datetime

from utils.gcs_uploader import upload_to_gcs_with_fallback
from utils.constants import BUCKET_NAME, FOLDER_NAME

# Cell threshold for GCS upload (rows × columns)
CELL_THRESHOLD_FOR_GCS = 0

class ResultProcessor:
    """Handles DataFrame and list of DataFrame results from code execution"""
    
    def __init__(self, bucket_name: str = BUCKET_NAME):
        self.bucket_name = bucket_name
    
    def process_result(self, result: Any, label: str = "Query_Result") -> Dict[str, Any]:
        """
        Main entry point to process DataFrame, dictionary of DataFrames, or list of DataFrame results
        Since code generator ensures all results are DataFrames, dicts of DataFrames, or lists of DataFrames
        """
        if isinstance(result, pd.DataFrame):
            return self._handle_dataframe_result(result, label)
        elif isinstance(result, dict):
            # Handle dictionary of DataFrames with meaningful keys
            return self._handle_dict_result(result)
        elif isinstance(result, list):
            return self._handle_list_result(result, label)
        else:
            # This should not happen with the new code generator constraints
            # But we'll handle it gracefully by converting to DataFrame
            return self._handle_unexpected_result(result, label)
    
    def _should_upload_to_gcs(self, df: pd.DataFrame) -> bool:
        """Determine if DataFrame should be uploaded to GCS based on size"""
        cell_count = len(df) * len(df.columns)
        return cell_count >= CELL_THRESHOLD_FOR_GCS
    
    def _format_dataframe_for_display(self, df: pd.DataFrame) -> str:
        """Format DataFrame for display, always truncated to 10 rows × 10 columns"""
        if df.empty:
            return "*(Empty DataFrame)*"
        
        # Always truncate to 10 rows and 10 columns max
        truncated_df = df.head(10).iloc[:, :10]
        
        # Convert to string representation
        df_str = truncated_df.to_string(index=False)
        
        # Add truncation indicators if needed
        truncation_info = []
        if len(df) > 10:
            truncation_info.append(f"... +{len(df) - 10} more rows")
        if len(df.columns) > 10:
            truncation_info.append(f"... +{len(df.columns) - 10} more columns")
        
        if truncation_info:
            df_str += f"\n{' '.join(truncation_info)}"
        
        return f"```\n{df_str}\n```"
    
    def _handle_dataframe_result(self, df: pd.DataFrame, label: str) -> Dict[str, Any]:
        """Handle pandas DataFrame results"""
        
        # Check if this is an error DataFrame
        if 'error' in df.columns and len(df.columns) == 1:
            error_msg = df['error'].iloc[0] if len(df) > 0 else "Unknown error"
            return {
                "type": "error",
                "status": "error",
                "message": f"❌ **Code Execution Failed After Retries**\n\n{error_msg[:500]}{'...' if len(error_msg) > 500 else ''}",
                "download_links": [],
                "display_data": None,
                "error_details": error_msg
            }
        
        if df.empty:
            return {
                "type": "dataframe",
                "status": "empty",
                "message": f"❌ **{label}** data is empty.",
                "download_links": [],
                "display_data": "*(Empty DataFrame)*"
            }
        
        cell_count = len(df) * len(df.columns)
        should_upload = self._should_upload_to_gcs(df)
        
        # Create summary info
        numeric_cols = df.select_dtypes(include='number').columns
        stats_summary = ""
        if len(numeric_cols) > 0 and should_upload:  # Only show stats for large DataFrames
            stats = df[numeric_cols].describe().round(2)
            stats_summary = f"\n📊 **Numeric Summary:**\n```\n{stats.to_string()}\n```"
        
        # Get sample row info
        sample_row = df.iloc[0].to_dict() if len(df) > 0 else {}
        
        # Format column info
        columns_info = f"📋 **Columns:** {', '.join(df.columns[:6])}"
        if len(df.columns) > 6:
            columns_info += f" (+{len(df.columns) - 6} more)"
        
        # Always format data for display (truncated to 10x10)
        display_data = self._format_dataframe_for_display(df)
        
        if should_upload:
            # Upload large DataFrame to GCS using the improved fallback function with descriptive label
            download_url = upload_to_gcs_with_fallback(df, self.bucket_name, folder=FOLDER_NAME, label=label)
            
            # Check if upload was successful (URL vs error message)
            upload_failed = download_url.startswith("❌")
            upload_warning = download_url.startswith("⚠️")
            
            if upload_failed:
                return {
                    "type": "dataframe",
                    "status": "partial_success", 
                    "label": label,
                    "rows_count": len(df),
                    "columns_count": len(df.columns),
                    "cell_count": cell_count,
                    "columns": list(df.columns),
                    "sample_row": sample_row,
                    "stats_summary": stats_summary,
                    "columns_info": columns_info,
                    "download_links": [],
                    "upload_error": download_url,
                    "display_data": display_data,
                    "message": f"✅ **{label}** processed successfully ({len(df)} rows, {len(df.columns)} columns, {cell_count} cells)\n{download_url}"
                }
            else:
                # Clean up warning messages from URL for display
                clean_url = download_url
                warning_message = ""
                if upload_warning:
                    # Extract warning and clean URL
                    parts = download_url.split(": ", 1)
                    if len(parts) == 2:
                        warning_message = f"\n⚠️ {parts[0].replace('⚠️', '').strip()}"
                        clean_url = parts[1]
                
                return {
                    "type": "dataframe",
                    "status": "success", 
                    "label": label,
                    "rows_count": len(df),
                    "columns_count": len(df.columns),
                    "cell_count": cell_count,
                    "columns": list(df.columns),
                    "sample_row": sample_row,
                    "stats_summary": stats_summary,
                    "columns_info": columns_info,
                    "download_links": [{"label": label, "url": clean_url}],
                    "display_data": display_data,
                    "warning_message": warning_message,
                    "message": f"✅ **{label}** processed successfully ({len(df)} rows, {len(df.columns)} columns, {cell_count} cells){warning_message}"
                }
        else:
            # Small DataFrame - display data directly
            return {
                "type": "dataframe",
                "status": "success", 
                "label": label,
                "rows_count": len(df),
                "columns_count": len(df.columns),
                "cell_count": cell_count,
                "columns": list(df.columns),
                "sample_row": sample_row,
                "columns_info": columns_info,
                "download_links": [],
                "display_data": display_data,
                "message": f"✅ **{label}** ({len(df)} rows, {len(df.columns)} columns, {cell_count} cells)"
            }
    
    def _handle_dict_result(self, result_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Handle dictionary of DataFrames with meaningful keys"""
        if not result_dict:
            return {
                "type": "dict",
                "status": "empty",
                "message": "❌ Result dictionary is empty.",
                "download_links": [],
                "processed_items": []
            }
        
        processed_items = []
        all_download_links = []
        total_rows = 0
        total_cells = 0
        
        for key, item in result_dict.items():
            # Use the dictionary key as the meaningful label
            item_label = key.replace('_', ' ').title() if '_' in key else key.capitalize()
            
            if isinstance(item, pd.DataFrame):
                processed_item = self._handle_dataframe_result(item, item_label)
                processed_items.append(processed_item)
                all_download_links.extend(processed_item.get("download_links", []))
                total_rows += processed_item.get("rows_count", 0)
                total_cells += processed_item.get("cell_count", 0)
            else:
                # Convert unexpected types to DataFrame
                fallback_result = self._handle_unexpected_result(item, item_label)
                processed_items.append(fallback_result)
                all_download_links.extend(fallback_result.get("download_links", []))
                total_rows += fallback_result.get("rows_count", 0)
                total_cells += fallback_result.get("cell_count", 0)
        
        return {
            "type": "dict",
            "status": "success",
            "items_count": len(result_dict),
            "total_rows": total_rows,
            "total_cells": total_cells,
            "processed_items": processed_items,
            "download_links": all_download_links,
            "message": f"✅ Processed {len(result_dict)} named results ({total_rows} total rows, {total_cells} total cells)"
        }
    
    def _handle_list_result(self, result_list: List[Any], base_label: str) -> Dict[str, Any]:
        """Handle list of DataFrames results"""
        if not result_list:
            return {
                "type": "list",
                "status": "empty",
                "message": "❌ Result list is empty.",
                "download_links": [],
                "processed_items": []
            }
        
        processed_items = []
        all_download_links = []
        total_rows = 0
        total_cells = 0
        
        for i, item in enumerate(result_list):
            item_label = f"{base_label}_{i+1}"
            
            if isinstance(item, pd.DataFrame):
                processed_item = self._handle_dataframe_result(item, item_label)
                processed_items.append(processed_item)
                all_download_links.extend(processed_item.get("download_links", []))
                total_rows += processed_item.get("rows_count", 0)
                total_cells += processed_item.get("cell_count", 0)
            else:
                # Convert unexpected types to DataFrame
                fallback_result = self._handle_unexpected_result(item, item_label)
                processed_items.append(fallback_result)
                all_download_links.extend(fallback_result.get("download_links", []))
                total_rows += fallback_result.get("rows_count", 0)
                total_cells += fallback_result.get("cell_count", 0)
        
        return {
            "type": "list",
            "status": "success",
            "items_count": len(result_list),
            "total_rows": total_rows,
            "total_cells": total_cells,
            "processed_items": processed_items,
            "download_links": all_download_links,
            "message": f"✅ Processed list with {len(result_list)} DataFrames ({total_rows} total rows, {total_cells} total cells)"
        }
    
    def _handle_unexpected_result(self, result: Any, label: str) -> Dict[str, Any]:
        """
        Handle unexpected result types by converting them to DataFrame
        This is a fallback for cases where code generator doesn't follow the new rules
        """
        try:
            # Convert to DataFrame with appropriate column name
            if isinstance(result, (str, int, float, bool)):
                df = pd.DataFrame({f'{label.lower()}_value': [result]})
            elif isinstance(result, dict):
                # Try to convert dict to DataFrame
                if all(isinstance(v, (list, tuple)) for v in result.values()):
                    df = pd.DataFrame(result)
                else:
                    # Convert dict to single row DataFrame
                    df = pd.DataFrame([result])
            elif result is None:
                df = pd.DataFrame({'result': ['No data returned']})
            else:
                # Convert to string representation
                df = pd.DataFrame({'result': [str(result)]})
            
            return self._handle_dataframe_result(df, f"{label}_Converted")
            
        except Exception as e:
            # Ultimate fallback
            error_df = pd.DataFrame({
                'error_type': [type(result).__name__],
                'error_message': [f"Failed to process result: {str(e)}"],
                'raw_value': [str(result)[:500]]  # Truncate long values
            })
            return self._handle_dataframe_result(error_df, f"{label}_Error")


def format_summary_message(processed_result: Dict[str, Any]) -> str:
    """Format the processed result into a user-friendly summary message"""
    result_type = processed_result.get("type", "unknown")
    status = processed_result.get("status", "unknown")
    message = processed_result.get("message", "")
    
    if status == "error":
        return message
    elif status == "empty":
        return message
    
    summary_parts = [message]
    
    if result_type == "dataframe":
        # Always display data (truncated to 10 columns x 10 rows)
        display_data = processed_result.get("display_data", "")
        if display_data and display_data != "*(Empty DataFrame)*":
            # Get original data info
            rows_count = processed_result.get("rows_count", 0)
            columns_count = processed_result.get("columns_count", 0)
            
            # Show truncated data preview
            summary_parts.append(f"\n📋 **Data Preview (showing up to 10 rows × 10 columns):**\n{display_data}")
            
            # Add info about full dataset size if truncated
            if rows_count > 10 or columns_count > 10:
                summary_parts.append(f"\n💡 **Full Dataset:** {rows_count} rows, {columns_count} columns")
        
        # Always add download links if available
        download_links = processed_result.get("download_links", [])
        if download_links:
            summary_parts.append("\n📁 **Download Full Data:**")
            for link_info in download_links:
                label = link_info.get("label", "Data")
                url = link_info.get("url", "")
                summary_parts.append(f"- [{label}]({url})")
        
        # Add statistics for numeric data
        if processed_result.get("stats_summary"):
            summary_parts.append(processed_result["stats_summary"])
    
    elif result_type in ["list", "dict"]:
        # Always display all items (each truncated to 10 columns x 10 rows)
        all_items = processed_result.get("processed_items", [])
        if all_items:
            summary_parts.append(f"\n📋 **Data Items (each showing up to 10 rows × 10 columns):**")
            for item in all_items:
                label = item.get("label", "DataFrame")
                display_data = item.get("display_data", "")
                if display_data:
                    summary_parts.append(f"\n**{label}:**\n{display_data}")
        
        # Always add download links if available
        download_links = processed_result.get("download_links", [])
        if download_links:
            summary_parts.append("\n📁 **Download Full Data:**")
            for link_info in download_links:
                label = link_info.get("label", "Data")
                url = link_info.get("url", "")
                summary_parts.append(f"- [{label}]({url})")
        
        # Add summary statistics  
        total_items = len(all_items)
        if total_items > 0:
            if result_type == "dict":
                summary_parts.append(f"\n📊 **Summary:** {total_items} named results processed")
            else:
                summary_parts.append(f"\n📊 **Summary:** {total_items} DataFrames processed")
    
    return "\n".join(summary_parts)


def summarize_result_node(state: dict) -> dict:
    """
    Main node function to process code execution results
    Now simplified to only handle DataFrames and lists of DataFrames
    Small DataFrames (<50 cells) are displayed directly, large ones uploaded to GCS
    """
    result = state.get("result", {})
    
    # Initialize result processor
    processor = ResultProcessor()
    
    # Process the result (guaranteed to be DataFrame or list of DataFrames)
    processed_result = processor.process_result(result)
    
    # Format the summary message
    summary_message = format_summary_message(processed_result)
    
    # Return state with processed result info
    return {
        **state,
        "result_query": summary_message,
        "processed_result": processed_result,
        "download_links": processed_result.get("download_links", [])
    }