import re
import csv

def parse_db102_info(input_file_path, output_csv_path):
    """
    Parses a text file for DB102.DBD entries and creates a CSV summary.

    Args:
        input_file_path (str): Path to the input text file (e.g., 'Pasted_Text_1753349311500.txt').
        output_csv_path (str): Path where the output CSV file will be saved.
    """
    dbd_entries = {}

    # Regular expression to match DB102.DBD lines
    # Captures offset, symbol, description, data type, and optional measurement unit
    # Handles cases where the unit might be on the same line or the next line
    dbd_pattern = re.compile(
        r'DB102\.DBD\s+(\d+)\s*"([^"]*)"\s*(.*?)\s+([A-Z_]+)(?:\s+([A-Z%°/\-0-9]+))?$'
    )

    try:
        with open(input_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: File '{input_file_path}' not found.")
        return
    except Exception as e:
        print(f"Error reading file '{input_file_path}': {e}")
        return

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for DB102.DBD entries
        if line.startswith("DB102.DBD"):
            match = dbd_pattern.match(line)
            if match:
                offset = match.group(1)
                # symbol = match.group(2) # Not requested, but available
                description = match.group(3).strip()
                data_type = match.group(4)
                unit = match.group(5) # Unit might be None if not on this line

                # If unit wasn't captured and the next line looks like a unit,
                # take it from the next line. This is a heuristic.
                if not unit and (i + 1) < len(lines):
                    next_line = lines[i + 1].strip()
                    # Check if the next line is a plausible unit (e.g., starts with capital letter or %, -, / etc.)
                    # and is not another DB entry or keyword. Adjust logic if needed.
                    if (re.match(r'^[A-Z%°/\-\d]+$', next_line) and
                            not next_line.startswith("DB") and
                            not next_line.startswith("//") and
                            " " not in next_line and len(next_line) < 20):
                        unit = next_line
                        i += 1 # Skip the next line as it was consumed as the unit

                # Store unique entries based on offset, preferring the first occurrence
                # or potentially updating if a more complete description/unit is found later.
                # This handles duplicates in the input file.
                if offset not in dbd_entries:
                    dbd_entries[offset] = {
                        "offset": offset,
                        "description": description,
                        "measurement_unit": unit if unit else "", # Use empty string if no unit
                        "data_type": data_type
                    }
                # Optional: Update if description/unit is better (e.g., not empty)
                # else:
                #     if not dbd_entries[offset]["description"] and description:
                #         dbd_entries[offset]["description"] = description
                #     if not dbd_entries[offset]["measurement_unit"] and unit:
                #         dbd_entries[offset]["measurement_unit"] = unit

        i += 1 # Move to the next line

    # --- Write to CSV ---
    if not dbd_entries:
        print("No DB102.DBD entries found in the input file.")
        return

    # Sort entries by offset numerically
    sorted_entries = sorted(dbd_entries.values(), key=lambda x: int(x['offset']))

    try:
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['offset', 'description', 'measurement_unit', 'data_type']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for entry in sorted_entries:
                writer.writerow(entry)

        print(f"✅ Successfully created CSV file: {output_csv_path}")
        print(f"   Found {len(sorted_entries)} unique DB102.DBD entries.")
    except Exception as e:
        print(f"Error writing CSV file '{output_csv_path}': {e}")


# --- Main Execution ---
if __name__ == "__main__":
    # Replace 'Pasted_Text_1753349311500.txt' with the actual path to your uploaded file
    input_file = 'variableTables.txt'
    output_file = 'db102_summary.csv'

    parse_db102_info(input_file, output_file)
