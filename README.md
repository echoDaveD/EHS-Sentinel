# EHS-Sentinel
EHS Sentinel written in python which reads Samsung EHS serial Data and published it to MQTT.
If want, you can activate the Home Assistent MQTT Auto Discovery Format, then the Messages will be sent in Home Assistent format.

There are already some solutions, but most of them are limited to just a few data points.
Since extending these was often too difficult, I have written a script here which lists almost all known data points of the Samsung EHS (source: https://wiki.myehs.eu/wiki/NASA_Protocol) in a YAML file as a repository `data/NasaRepository` and the entries there were supplemented by a few Relavante HomeAssistant attributes

In addition, a few data points are generated from others, such as COP and Heat Output.

# Installation

## Simple

1. Just clone the repository
    `git clone https://github.com/echoDaveD/EHS-Sentinel`
2. Install the requierments
    `pip install -r requirements.txt`
3. Copy the `data/config.yml` and provide your Configuration
4. Start the Application:
    `python3 startEHSSentinel.py --configfile config.yml`

## Virtual Environment

...

## Systemd Service

..

# Configuration


## Command-Line Arguments

The `EHSArguments` class handles command-line arguments for the EHS-Sentinel script. Below is a detailed explanation of each argument and its usage.

### Arguments

- **--configfile** (required)
  - Type: `str`
  - Description: Path to the configuration file.
  - Example: `--configfile config.yml`

- **--dumpfile** (optional)
  - Type: `str`
  - Description: File path for where the dump file should be written to or read from if the `--dryrun` flag is set.
  - Example: `--dumpfile dumpfile.txt`

- **--dryrun** (optional)
  - Type: `bool`
  - Description: Run the script in dry run mode. Data will be read from the dump file.
  - Example: `--dryrun`

- **--clean-known-devices** (optional)
  - Type: `bool`
  - Description: Cleans the known devices topic on startup. Relevant for Home Assistant Auto Discovery, this option forces to resend the Device Configuration Autodiscovery Messages.
  - Example: `--clean-known-devices`

- **-v, --verbose** (optional)
  - Type: `bool`
  - Description: Enable verbose mode.
  - Example: `-v` or `--verbose`

### Example Usage

To run the EHS-Sentinel script with the required configuration file and optional arguments, use the following command:

```sh
python3 startEHSSentinel.py --configfile config.yml --dumpfile dumpfile.txt --dryrun --clean-known-devices -v
```

## Configuration File: `config.yml`

The `config.yml` file contains configuration settings for the EHS-Sentinel project. This file is used to configure general settings, serial connection parameters, and MQTT broker details. Below is a detailed explanation of each section and its parameters.

### General Settings

- **nasaRepositoryFile**: Path to the NASA repository file.
  - Default: `data/NasaRepository.yml`
- **silentMode**: Boolean flag to enable or disable silent mode. In Silent Mode only Logmessages above WARNING are printed out (for production use to not spam your systemlog)
  - Default: `True`
- **protocolFile**: Path to the protocol file. (not set in Sample config.yml)
  - Example: `prot.csv`

### Serial Connection Settings

- **device**: The serial device URL.
  - Example: `/dev/ttyUSB0`
- **baudrate**: The baud rate for the serial connection.
  - Example: `9600`

### MQTT Broker Settings

- **broker-url**: The URL of the MQTT broker.
  - Example: `123.45.6.69`
- **broker-port**: The port number of the MQTT broker.
  - Example: `1883`
- **client-id**: The client ID to use when connecting to the MQTT broker.
  - Deafult: `EHS-Sentinel`
- **user**: The username for authenticating with the MQTT broker.
  - Example: `user`
- **password**: The password for authenticating with the MQTT broker.
  - Example: `bigBabaBubuPa$$word1`
- **homeAssistantAutoDiscoverTopic**: The topic prefix for Home Assistant auto-discovery. This Topicprefix must be the same as in Home Assistant MQTT Integration Settings
  - Example: `homeassistant`
- **useCamelCaseTopicNames**: Boolean flag to enable or disable the use of camel case for topic names.
  - Example: `True`
- **topicPrefix**: The prefix to use for MQTT topics. (Is used when homeassistant is not set or empty)
  - Example: `ehsSentinel`

### Example Configuration

```yaml
general:
  nasaRepositoryFile: data/NasaRepository.yml
  silentMode: False
  protocolFile: prot.csv
serial:
  device: /dev/ttyUSB0
  baudrate: 9600
mqtt:
  broker-url: 123.45.6.69
  broker-port: 1883
  client-id: EHS-Sentinel
  user: user
  password: bigBabaBubuPa$$word1
  homeAssistantAutoDiscoverTopic: "homeassistant"
  useCamelCaseTopicNames: True
  topicPrefix: ehsSentinel
```

# Debugging

If you want to debug the App or just play around or even make some Changes, you can use the Dumpfile mode to be independent of the serial port and your production system.

## Creating Dump Files

To generate a Dumpfile just start the App with the `--dumpfile` Argument an let it run for a few minutes. 5-10 minutes has proven to be a good amount of time.

`python3 startEHSSentinel.py --configfile config.yml --dumpfile dump.txt`

to abort the Script jost Keyinterrupt with strg+c.

## Using Dumpfile as Input (no Serial)

If you have generated an Dumpfile you can use this to run in drymode so, the EHS-Sentinel is reading your dumpfile instead of Serial Port.

`python3 startEHSSentinel.py --configfile config.yml --dumpfile dump.txt --dryrun`

### Additional Commands

if you want to see how many uniquie Messages have been collected in the Dumpfile, here some commands:

1. Run the Dumpfile generatation with activated protocol file in the Config file.
2. search unique measerments

    `sort -u -t, -k1,3 prot.csv > prot_uniq.csv`
3. count lines

    `wc -l prot_uniq.csv`


# Changelog

### v0.1.0Beta - 2025-02-08
- Initial Commit