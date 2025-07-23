import struct
import binascii
import re # For more robust parsing of the structure file if needed

# --- 1. Define the Structure ---
# This is the structure for "vat 00 actuals" DB102 variables based on the provided files
# Format: (Offset (bytes), Data Type, Tag, Description)
# Assuming VIRGULE_FLOTTANTE is IEEE 754 single precision float (4 bytes, Big-Endian)
# Note: Only variables with DBD (Double Word = 4 bytes) offsets relevant to the 64-byte dump are included
# Note: BOOL/CHAR/DEC types are ignored for this float-focused parsing of this specific dump

structure_vat_00_actuals_db102 = [
    # Offsets within the 64-byte dump:
    (0, 'REAL', '"VALUE"._00_P_actual_R', 'Puissance en kW'), # Starts at byte 0
    (4, 'REAL', '"VALUE"._00_P_actual_measured', 'Puissance mesurée en kW'), # Starts at byte 4
    # (8, ... ) # Bytes 8-11 are 00 00 00 00 in the dump
    # (12, ... ) # Bytes 12-15 are 00 00 00 00 in the dump
    # ...
    # (20, ... ) # Bytes 20-23 are 00 00 42 ca in the dump -> Part of 42ca9e66 at offset 16
    (16, 'REAL', '<Unknown or unmapped at offset 16>', 'Likely related to hydraulic pressure or temp (value ~101.3)'), # 42ca9e66
    (20, 'REAL', '<Unknown or unmapped at offset 20>', 'Likely related to hydraulic pressure or temp (value ~41.4)'), # 42257ccc
    (24, 'REAL', '<Unknown or unmapped at offset 24>', 'Likely related to hydraulic pressure or temp (value ~28.4)'), # 41e347ae
    (28, 'REAL', '<Unknown or unmapped at offset 28>', 'Likely related to hydraulic pressure or temp (value ~0.53)'), # 3e0f5c29
    # ... more 00 bytes ...
    (44, 'REAL', '<Unknown or unmapped at offset 44>', 'Likely related to crane data (value ~440.0)'), # 43dc0000
    # ... more 00 bytes ...
    (56, 'REAL', '<Unknown or unmapped at offset 56>', 'Likely related to crane data (value ~50.2)'), # 4248cccd
    # Offsets beyond the 64-byte dump (64 = 0x40) are not present in this specific read:
    # (94, 'REAL', '"VALUE"._04_Setpoint_Y_R', 'Valeur de consigne pompe hydraulique'),
    # (98, 'REAL', '"VALUE"._04_Temp_hydr_R', 'Température du système hydraulique'),
    # (206, 'REAL', '"VALUE"._11_N_setpoint_R', 'Transmission de consigne à l\'entraînement en %'),
    # (218, 'REAL', '"VALUE"._11_N_actual_R', 'Valeur réelle vitesse en t/min'),
    # (270, 'REAL', '"VALUE"._11_V_allow_R', 'Méc. levage: vitesse admissible en m/min'),
    # (476, 'REAL', '"VALUE"._21_N_setpoint_R', 'Transmission de consigne à l\'entraînement en %'),
    # (496, 'REAL', '"VALUE"._21_N_actual_R', 'Valeur réelle vitesse en t/min'),
    # (532, 'REAL', '"VALUE"._21_N_max_crane', 'Vitesse maxi de la grue en tr/min'),
    # (640, 'REAL', '"VALUE"._31_v_actual_R', 'Vitesse réelle du cylindre de variation de volée'),
    # (652, 'REAL', '"VALUE"._31_RAD_actual_R', 'Portée en mètres (codeur absolu)'),
    # (1020, 'REAL', '"VALUE"._63_SLI_check_63_L_act', 'Indicateur CEC, mode test: charge actuelle'),
]

# --- 2. Input Raw Hex String ---
# Full raw hex string for DB102 from your scan
raw_hex_string_db102 = "bf800000bf8000000000000000000000000042ca9e6642257ccc41e347ae3e0f5c290000000000000000000000000000000043dc0000000000004248cccd0000"

# --- 3. Processing Function ---
def parse_db_hex(hex_string, structure):
    """
    Parses a hex string representation of a DB based on a given structure.

    Args:
        hex_string (str): The hex string representing the DB content.
        structure (list): A list of tuples defining the structure
                          (offset, data_type, tag, description).

    Returns:
        dict: A dictionary mapping tags to their parsed values and metadata.
    """
    try:
        # Convert hex string to bytes
        raw_bytes = binascii.unhexlify(hex_string.strip())
        db_size = len(raw_bytes)
        print(f"Parsing DB of size: {db_size} bytes")
    except binascii.Error as e:
        print(f"Error: Invalid hex string provided: {e}")
        return {}

    results = {}
    for offset, data_type, tag, description in structure:
        try:
            # Check if the offset and required bytes are within the DB size
            if offset + 4 > db_size:
                print(f"Warning: Offset {offset} for tag '{tag}' is out of bounds for DB size {db_size}. Skipping.")
                # Optionally add an entry for out-of-bounds items
                # results[tag] = {'value': None, 'description': description, 'offset': offset, 'error': 'Out of bounds'}
                continue

            # Extract 4 bytes starting at the offset
            data_bytes = raw_bytes[offset : offset + 4]

            # Interpret based on data type
            if data_type == 'REAL':
                # Unpack as Big-Endian float32 (>f)
                value = struct.unpack('>f', data_bytes)[0]
            else:
                # Handle other data types if needed (e.g., DWORD, INT, etc.)
                value = f"Unsupported data type: {data_type} for bytes {data_bytes.hex()}"
                print(f"Warning: {value}")

            # Store the result
            results[tag] = {
                'value': value,
                'description': description,
                'offset': offset,
                'raw_bytes': data_bytes.hex()
            }

        except (struct.error, IndexError) as e:
            print(f"Error parsing tag '{tag}' at offset {offset}: {e}")
            results[tag] = {'value': None, 'description': description, 'offset': offset, 'error': str(e)}

    return results

# --- 4. Execution ---
if __name__ == "__main__":
    print("--- Parsing DB102 Hex String (64 bytes) ---")
    parsed_data = parse_db_hex(raw_hex_string_db102, structure_vat_00_actuals_db102)

    # --- 5. Output ---
    print("\n--- Parsed Results ---")
    if not parsed_data:
        print("No data parsed.")
    else:
        # Sort results by offset for clearer output
        sorted_results = sorted(parsed_data.items(), key=lambda item: item[1]['offset'])
        for tag, data in sorted_results:
            if 'error' in data:
                print(f"Tag: {tag}")
                print(f"  Error: {data['error']}")
                print(f"  Offset: {data['offset']}")
            else:
                print(f"Tag: {tag}")
                print(f"  Value: {data['value']}")
                print(f"  Description: {data['description']}")
                print(f"  Offset: {data['offset']}")
                print(f"  Raw Bytes: {data['raw_bytes']}")
            print("-" * 40) # Separator line
        print("Parsing complete.")