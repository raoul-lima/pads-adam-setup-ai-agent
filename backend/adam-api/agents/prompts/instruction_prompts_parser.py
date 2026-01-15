import json
import os

def main():
    """
    Reads a JSON configuration file and updates its values based on corresponding .txt files.
    """
    try:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Define the path to the JSON file
        json_file_path = os.path.join(script_dir, "prompt_instructions.json")

        # Load the JSON file
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"Error: JSON file not found at {json_file_path}")
            return
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {json_file_path}")
            return

        # Create a new dictionary to store potentially modified data
        # This ensures we iterate over original keys even if keys themselves are filenames
        modified_data = data.copy()

        # Iterate through the keys of the loaded JSON object
        for key in data.keys():
            txt_filename = f"{key}.txt"
            txt_file_path = os.path.join(script_dir, "static_check_instructions", txt_filename)

            if os.path.exists(txt_file_path):
                try:
                    with open(txt_file_path, 'r', encoding='utf-8') as f_txt:
                        txt_content = f_txt.read()
                    modified_data[key] = txt_content
                except Exception as e:
                    print(f"Warning: Could not read file {txt_file_path}. Retaining original value for key '{key}'. Error: {e}")
                    # Original value is already in modified_data if not updated
            else:
                # If the .txt file doesn't exist, do nothing, original value remains.
                pass

        # Output the modified JSON
        # print(json.dumps(modified_data, indent=2, ensure_ascii=False))

        # Save the modified data back to the JSON file
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(modified_data, f, indent=2, ensure_ascii=False)
            print(f"Successfully updated {json_file_path}")
        except Exception as e:
            print(f"Error: Could not write to JSON file {json_file_path}. Error: {e}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
