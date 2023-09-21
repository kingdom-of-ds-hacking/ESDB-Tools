#!/usr/bin/python3
'''
    ESDBMerger
    Written by PlatinumMaster (2023)
'''
import argparse
import yaml
from pathlib import Path

class HexInteger(int):
    pass

def main() -> int:
    yaml.add_representer(HexInteger, representer)

    parser = argparse.ArgumentParser()
    parser.add_argument('--old', dest='old', type=str)
    parser.add_argument('--new', dest='new', type=str)
    parser.add_argument('--output', dest='output', type=str)
    
    arguments = parser.parse_args()
    old_map, new_map = construct_segment_map(Path(arguments.old)), construct_segment_map(Path(arguments.new))
    merged_map = merge_segment_maps(old_map, new_map)
    write_new_esdb(merged_map, Path(arguments.output))
    return 0

def representer(dumper, data) -> yaml.ScalarNode: 
    return yaml.ScalarNode('tag:yaml.org,2002:int', hex(data))

def construct_segment_map(file: Path) -> dict:
    with file.open('r') as YML:
        YML_DICT = yaml.safe_load(YML)
    
    # Each YML should have "Segments" & "Symbols" sections.
    if 'Segments' not in YML_DICT.keys() or 'Symbols' not in YML_DICT.keys():
        return {}
    
    # Create segment structures.
    segments, segment_map = {}, {}
    for element in YML_DICT['Segments']:
        segments[element['Name']] = {
            'Type': element['Type'],
            'Symbols': {}
        }
        segment_map |= {
            element['ID'] : len(segment_map.keys())
        }
    segment_keys = list(segments.keys())
    
    # Tree-walk symbols, and match them to segments.
    for element in YML_DICT['Symbols']:
        if element['Segment'] not in segment_map.keys():
            print(f'Segment {element["Segment"]} is not defined in {file.as_posix()}, yet symbol {element["Name"]} is using it?! Make sure your ESDB is valid. Exiting.')
            exit(1)
        # print(len(segment_keys))
        segments[segment_keys[segment_map[element['Segment']]]]['Symbols'] |= {
            element['Name'] : HexInteger(element['Address'])
        }
    return segments

def merge_segment_maps(old: dict, new: dict) -> dict:
    # Create a unified segment map.
    result_segment_map = old
    for segment_name, segment_data in new.items():
        if segment_name in result_segment_map.keys():
            print(f'Matching segment "{segment_name}" found! Merging functions...')
            for symbol_name, symbol_address in segment_data['Symbols'].items():
                symbols_with_same_address = [(name, address) for name, address in result_segment_map[segment_name]['Symbols'].items() if address == symbol_address]
                if len(symbols_with_same_address) == 1:
                    print(symbols_with_same_address)
                    if symbol_name != symbols_with_same_address[0][0]:
                        print(f'CONFLICT! Function with address {hex(symbol_address)} is defined in both ESDBs, but with different names.')
                        print(f'Name in old ESDB: {symbols_with_same_address[0][0]}')
                        print(f'Name in new ESDB: {symbol_name}')
                        conflict_input = input('What would you like to do?  (Press 1 to use the old name, 2 to use the new name, and 3 to define a new name.): ')
                        
                        while not conflict_input.isnumeric() or not 1 <= (conflict_input := int(conflict_input)) <= 3:
                            print('Not a valid answer. I will ask again.')
                            conflict_input = input('What would you like to do?  (Press 1 to use the old name, 2 to use the new name, and 3 to define a new name.): ')
                        
                        match conflict_input:
                            case 1:
                                # We're keeping the old name. Don't change anything.
                                print(f'Using {symbols_with_same_address[0][0]}...')
                            case 2:
                                # New name; update attributes.
                                print(f'Using {symbol_name}...')
                                result_segment_map[segment_name]['Symbols'][symbol_name] = symbols_with_same_address[0][1]
                                del result_segment_map[segment_name]['Symbols'][symbols_with_same_address[0][0]]
                            case 3:
                                # New name; new attributes.
                                new_name = input('Name? ')
                                print(f'Using {new_name}...')
                                result_segment_map[segment_name]['Symbols'][new_name] = symbols_with_same_address[0][1]
                                del result_segment_map[segment_name]['Symbols'][symbols_with_same_address[0][0]]
                elif len(symbols_with_same_address) == 0:
                    result_segment_map[segment_name]['Symbols'] |= { symbol_name : symbol_address }
        else:
            result_segment_map |= { segment_name : segment_data }
    return result_segment_map

def write_new_esdb(new_map: dict, output: Path) -> None:
    esdb_proper_map = {
        'Segments' : [],
        'Symbols': []
    }

    for key, value in new_map.items():
        id = len(esdb_proper_map['Segments'])
        esdb_proper_map['Segments'].append({
            'ID': HexInteger(id),
            'Name': key,
            'Type': value['Type'],
        })
        for symbol_name, symbol_address in value['Symbols'].items():
            esdb_proper_map['Symbols'].append({
                'Name': symbol_name,
                'Segment': HexInteger(id),
                'Address': HexInteger(symbol_address)
            })

    with output.open('w') as YML_OUT:
        yaml.dump(esdb_proper_map, YML_OUT)

if __name__ == '__main__':
    exit(main())