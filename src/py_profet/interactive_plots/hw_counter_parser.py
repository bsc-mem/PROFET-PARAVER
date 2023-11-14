import json
import sys

def parse_cpu_info_from_file(file_path):
    parsed_data = {
        "CPU": {},
        "Data": []
    }

    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Parse the CPU information from the first section
    for line in lines[:4]:
        if line.startswith("CPU name:"):
            parsed_data["CPU"]["name"] = line.split('\t')[1].strip()
        elif line.startswith("CPU type:"):
            parsed_data["CPU"]["type"] = line.split('\t')[1].strip()
        elif line.startswith("CPU clock:"):
            parsed_data["CPU"]["clock"] = line.split('\t')[1].strip()

    # Parse the number of hardware threads
    hw_thread_line = lines[5]  # HWThreads line
    parsed_data["HWThreads"] = len(hw_thread_line.split(':')[1].split('|'))

    # Parse the keys
    keys_line = lines[6]  # Keys line
    keys = keys_line.strip().lstrip('# ').split('|')

    # Parse the data lines
    data_lines = lines[7:]  # Data starts from line 7
    index=0
    for line in data_lines:
        if line.startswith('---') or not line.strip():
            continue  # Skip empty or irrelevant lines

        data_dict = {}
        values = line.split()

        def get_unique_key(key, data_dict):
            if key not in data_dict:
                return key
            i = 1
            while f"{key}-{i}" in data_dict:
                i += 1
            return f"{key}-{i}"

        # Parse first 4 unique values
        for i in range(4):
            key = get_unique_key(keys[i], data_dict)
            data_dict[key] = float(values[i])

        # Parse the grouped values
        # Corrected data parsing loop for grouped values
        bytes = 0
        flops = 0
        for i in range(4, len(keys)):
            key = get_unique_key(keys[i], data_dict)
            start_index = 4 + (i - 4) * parsed_data["HWThreads"]
            end_index = start_index + parsed_data["HWThreads"]
            data_dict[key] = [float(values[j]) for j in range(start_index, end_index)]
            if key.startswith("CAS_COUNT"):
                bytes += sum(data_dict[key])
            if key.startswith("FP_ARITH_INST"):
                flops += sum(data_dict[key])

        # flops are in MFLOPS, convert to FLOPS
        data_dict["TOTAL_FLOPS"] = flops * 1000 * 1000
        data_dict["TOTAL_BYTES"] = (bytes*64)
        data_dict["BANDWIDTH (MB/s)"] = (bytes*64) / data_dict["Total runtime [s]"] / 1000 / 1000

        parsed_data["Data"].append(data_dict)
        index = index + 1

    return parsed_data


def convert_to_json_file(file_path, parsed_data):

    output_path = file_path.replace('.txt', '.json')

    for entry in parsed_data['Data']:
        for key, value in entry.items():
            if isinstance(value, list):
                # Convert list of floats to a formatted string
                entry[key] = '[' + ', '.join(f'{v:.1f}' for v in value) + ']'

    with open(output_path, 'w') as outfile:
        json_str = json.dumps(parsed_data, indent=4)
        # Replace the string-formatted lists with their unindented versions
        json_str = json_str.replace('"[', '[').replace(']"', ']')
        json_str = json_str.replace('Total runtime [s]', 'Total runtime [s]\"')
        outfile.write(json_str)

# USAGE: python counter_parser.py <file_path>

if __name__ == "__main__":
    file_path = sys.argv[1]

    parsed_data = parse_cpu_info_from_file(file_path)

    convert_to_json_file(file_path, parsed_data)


