import argparse
import configparser
import yaml

"""
This script provides helper functions for processing NASA table data and merging YAML files.
Functions:
    parse_arguments():
        Parses command-line arguments to get the function name to execute.
    nasatable2dict():
        Reads data from 'nasa_table.txt' and 'nasa_type_table.txt', processes it, and writes the output to 'nasa_data2.yaml'.
    yaml_merge():
        Merges data from 'nasa_data.yaml' and 'nasa_data2.yaml', and writes the merged output to 'nasa_data3.yaml'.
    main():
        Main function that calls the appropriate function based on the command-line argument.
"""
def parse_arguments():
    parser = argparse.ArgumentParser(description="EHS2MQTT Helper Script")
    parser.add_argument('functionname', type=str, help='Put the function name here')

    arg = parser.parse_args()


    return arg.functionname

def nasatable2dict():
    with open('nasa_table.txt', 'r') as file:
        lines = file.readlines()

    data = {}
    for line in lines:
        parts = line.strip().split('||')
        valid_name = parts[1].strip()
        if valid_name.endswith('?') or len(parts[1].strip()) == 0:
            valid_name = parts[2].strip()
        
        if valid_name.endswith('?'):
            valid_name = ''

        if len(valid_name) > 0:
            data[parts[0].strip()] = {
                'label': parts[1].strip() if (len(parts[2].strip()) == 0 and not parts[2].strip().endswith('??')) else parts[2].strip(),
                'description': parts[3].strip(),
                'remarks': parts[4].strip(),
                'type': '',
                'signed': '',
                'unit': '',
                'arithmetic': '',
            }

    with open('nasa_type_table.txt', 'r') as file:
        lines = file.readlines()

    types = {}
    for line in lines:
        parts = line.strip().split('||')
        types[parts[0].strip()] = {
            'type': parts[1].strip(),
            'signed': parts[2].strip(),
            'unit': parts[3].strip(),
            'arithmetic': parts[4].strip()
        }

    for key in data:
        if key in types:
            data[key]['type'] = types[key]['type']
            data[key]['signed'] = types[key]['signed']
            data[key]['unit'] = types[key]['unit']
            data[key]['arithmetic'] = types[key]['arithmetic']

    config = {}
    for key, value in data.items():
        print(f"Adding {value['label']} with address {value}")
        if len(value['label']) > 0:
            config[value['label']] = {
                'address': key,
                'description': value['description'],
                'remarks': value['remarks'],
                'type': value['type'],
                'signed': value['signed'],
                'unit': value['unit'],
                'arithmetic': value['arithmetic']
        }

    with open('nasa_data2.yaml', 'w') as configfile:
        yaml.dump(config, configfile, default_flow_style=False)

    print(data)

def yaml_merge():
    with open('nasa_data.yaml', 'r') as configfile:
            yaml1 = yaml.safe_load(configfile)
    
    with open('nasa_data2.yaml', 'r') as configfile:
            yaml2 = yaml.safe_load(configfile)
    yaml3 = {}
    for key2, value2 in yaml2.items():
        found = False
        for key, value in yaml1.items():
            if(value['address'] == value2['address']):
                found = True
                if key2 != key:
                    print(f"Key {key} rewrite with {key2}")
                    yaml3[key2] = value
                else:
                    yaml3[key] = value
                break
            if key2 == key:
                print(f"Key {key2} already exists")
                break
        if not found:
            print(f"Adding {key2} with address {value2['address']}")
            yaml3[key2] = value2

    with open('nasa_data3.yaml', 'w') as configfile:
        yaml.dump(yaml3, configfile, default_flow_style=False)

def main():
    funktion = parse_arguments()

    if funktion.lower() == "nasatable2dict":
        print("Calling nasatable2dict")
        nasatable2dict()

    if funktion.lower() == "yaml_merge":
        print("Calling yaml_merge")
        yaml_merge()



if __name__ == "__main__":
    main()