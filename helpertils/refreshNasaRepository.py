import argparse
import yaml

def replace_empty_with_null(d):
    
    if isinstance(d, dict):
        return {k: replace_empty_with_null(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [replace_empty_with_null(v) for v in d]
    elif d is None:
        return None  # Ensure `None` stays as YAML `null`
    elif len(d.strip()) == 0:
        return None
    return d

def main():
    with open('data/NasaRepository.yml', 'r') as nasarepo:
        old_yaml = yaml.safe_load(nasarepo)

    ele = {}

    for key, value in old_yaml.items():
        print(key)
        ele[key] = {}
        ele[key]['hass_opts'] = {}
        ele[key]['hass_opts']['platform'] = {}
        ele[key]['address'] = replace_empty_with_null(old_yaml[key]['address'])
        if replace_empty_with_null(old_yaml[key]['arithmetic']) is not None:
            ele[key]['arithmetic'] = old_yaml[key]['arithmetic']
        if 'description' in old_yaml[key] and replace_empty_with_null(old_yaml[key]['description']) is not None:
            ele[key]['description'] = old_yaml[key]['description']
        ele[key]['hass_opts']['default_platform'] = "sensor"
        if 'writable' in old_yaml[key]:
            ele[key]['hass_opts']['writable'] = old_yaml[key]['writable']
        else:
            ele[key]['hass_opts']['writable'] = False
        if 'enum' in old_yaml[key]:
            new_values = [x.replace("'", "") for x in old_yaml[key]['enum'].values()]
            if all([en.lower() in ['on', 'off'] for en in new_values]):
                ele[key]['enum'] = old_yaml[key]['enum']
                ele[key]['hass_opts']['default_platform'] = "binary_sensor"
                ele[key]['hass_opts']['platform']['payload_off'] = 'OFF'
                ele[key]['hass_opts']['platform']['payload_on'] = 'ON'
                ele[key]['hass_opts']['platform']['type'] = 'switch'
            else:
                ele[key]['enum'] = old_yaml[key]['enum']
                ele[key]['hass_opts']['platform']['options'] = new_values
                ele[key]['hass_opts']['platform']['type'] = 'select'
        else:
            if 'min' in old_yaml[key]:
                ele[key]['hass_opts']['platform']['min'] = old_yaml[key]['min']
            if 'max' in old_yaml[key]:
                ele[key]['hass_opts']['platform']['max'] = old_yaml[key]['max']
            if 'step' in old_yaml[key]:
                ele[key]['hass_opts']['platform']['step'] = old_yaml[key]['step']
            ele[key]['hass_opts']['platform']['type'] = 'number'
        if replace_empty_with_null(old_yaml[key]['remarks']) is not None:
            ele[key]['remarks'] = old_yaml[key]['remarks']
        if replace_empty_with_null(old_yaml[key]['signed']) is not None:
            ele[key]['signed'] = old_yaml[key]['signed']
        if replace_empty_with_null(old_yaml[key]['type']) is not None:
            ele[key]['type'] = old_yaml[key]['type']

        if 'state_class' in old_yaml[key]:
            ele[key]['hass_opts']['state_class'] = old_yaml[key]['state_class']
        if 'device_class' in old_yaml[key]:
            ele[key]['hass_opts']['device_class'] = old_yaml[key]['device_class']

        if 'unit' in old_yaml[key]:
            if replace_empty_with_null(old_yaml[key]['unit']) is not None:
                ele[key]['hass_opts']['unit'] = old_yaml[key]['unit']
                if ele[key]['hass_opts']['unit'] == "\u00b0C":
                    ele[key]['hass_opts']['device_class'] = "temperature"
                elif ele[key]['hass_opts']['unit'] == '%':
                    ele[key]['hass_opts']['state_class'] = "measurement"
                elif ele[key]['hass_opts']['unit'] == 'kW':
                    ele[key]['hass_opts']['device_class'] = "power"
                elif ele[key]['hass_opts']['unit'] == 'rpm':
                    ele[key]['hass_opts']['state_class'] = "measurement"
                elif ele[key]['hass_opts']['unit'] == 'bar':
                    ele[key]['hass_opts']['device_class'] = "pressure"
                elif ele[key]['hass_opts']['unit'] == 'HP':
                    ele[key]['hass_opts']['device_class'] = "power"
                elif ele[key]['hass_opts']['unit'] == 'hz':
                    ele[key]['hass_opts']['device_class'] = "frequency"
                elif ele[key]['hass_opts']['unit'] == 'min':
                    ele[key]['hass_opts']['device_class'] = "duration"
                elif ele[key]['hass_opts']['unit'] == 'h':
                    ele[key]['hass_opts']['device_class'] = "duration"
                elif ele[key]['hass_opts']['unit'] == 's':
                    ele[key]['hass_opts']['device_class'] = "duration"

    with open('data/NasaRepository.yml', 'w') as newyaml:
        yaml.dump(ele, newyaml, default_flow_style=False)

if __name__ == "__main__":
    main()