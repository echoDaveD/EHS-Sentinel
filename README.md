# EHS-Sentinel
EHS Sentinel written in python which reads Samsung EHS serial Data and published it to MQTT.
If want, you can activate the Home Assistent MQTT Auto Discovery Format, then the Messages will be sent in Home Assistent format.

There are already some solutions, but most of them are limited to just a few data points.
Since extending these was often too difficult, I have written a script here which lists almost all known data points of the Samsung EHS (source: https://wiki.myehs.eu/wiki/NASA_Protocol) in a YAML file as a repository `data/NasaRepository` and the entries there were supplemented by a few Relavante HomeAssistant attributes

In addition, a few data points are generated from others, such as COP and Heat Output.

# Prerequisites

You need an MQTT Broker.
For Homeassistant you need the MQTT Plugin there with enabled Auto Discovery with Discovery Topic Prefix and Birth-Messages on Discovery Topic Prefix with subtopic "status" with text "online".
EHS-Sentinel subscribes <hass_discovery_prefix>/status Topic and if it receive an "online", then it cleans his intern known-devices topic and send the Auto Discovery Config again for any Measurment for Home Assistant.

# Installation

## Simple

1. Just clone the repository
    `git clone https://github.com/echoDaveD/EHS-Sentinel`
2. Install the requierments
    `pip install -r requirements.txt`
3. Copy the `data/config.yml` and provide your Configuration
4. Start the Application:
    `python3 startEHSSentinel.py --configfile config.yml`

## Systemd Service

1. Just clone the repository
    `git clone https://github.com/echoDaveD/EHS-Sentinel`
2. Install the requierments
    `pip install -r requirements.txt`
3. Copy the `data/config.yml` and provide your Configuration
4. Change to ehs-sentinel.service file as followed:

   `ExecStart = python3 <Path of the script you want to run>` <- provide here to path to your folder where startEHSSentinel.py is

   sample: `ExecStart = python3 /root/EHS-Sentinel/startEHSSentinel.py --configfile /root/EHS-Sentinel/config.yml`

5. Change your `config.yml` to absolut paths:
   `nasaRepositoryFile: /root/EHS-Sentinel/data/NasaRepository.yml`

6. Copy the service File to your systemd folder:
  `cp ehs-sentinel.service /etc/systemd/system`

7. Enable the new service
  `systemctl enable ehs-sentinel`

8. Reload deamon
  `systemctl daemon-reload`

9. Start the Service
  `systemctl start ehs-sentinel`

10. check if anything is fine 
  `systemctl status ehs-sentinel`

11. If your want to check the journal logs
  `journalctl | grep ehsSentinel`


## Venv Installation (recommendet)

In general, it is recommended to work with a virtual environment (venvs) in python to be independent of other projects.
Some Distributions like debian 12 dont allow to use system wide pip package installation, so you have to use venv.

1. Just clone the repository
    `git clone https://github.com/echoDaveD/EHS-Sentinel`

2. Install python venv
  `apt install python3.11-venv` <- modify your python verison here

3. Create Python venv
  `python3 -m venv EHS-Sentinel`

4. change diractory
   `cd EHS-Sentinel`

5. activate venv
  `source bin/activate`

6. Install the requierments
    `pip install -r requirements.txt`

7. Copy the `data/config.yml` and provide your Configuration

8. get path of venv python executable
  `which python3` <- copy the output

9. Change to ehs-sentinel.service file as followed:

   `ExecStart = <path to python3> <Path of the script you want to run>` <- provide here to path to your folder where startEHSSentinel.py is

   sample: `ExecStart = /root/EHS-Sentinel/bin/python3 /root/EHS-Sentinel/startEHSSentinel.py --configfile /root/EHS-Sentinel/config.yml`

10. Change your `config.yml` to absolut paths:
   `nasaRepositoryFile: /root/EHS-Sentinel/data/NasaRepository.yml`

11. Deactivate venv
  `dactivate`

12. Copy the service File to your systemd folder:
  `cp ehs-sentinel.service /etc/systemd/system`

13. Enable the new service
  `systemctl enable ehs-sentinel`

14. Reload deamon
  `systemctl daemon-reload`

15. Start the Service
  `systemctl start ehs-sentinel`

16. check if anything is fine 
  `systemctl status ehs-sentinel`

17. If your want to check the journal logs
  `journalctl | grep ehsSentinel`


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

### Logging Settings

- **deviceAdded**: Set to true will log when new device is added to known Devices (and discover to HASS).
  - Default: `True`
- **messageNotFound**: Set to true will log when a received message was not found in NasaRepository
  - Default: `False`
- **packetNotFromIndoorOutdoor**: Set to true will log when a message not from Indoor/Outdoor unit was received
  - Example: `False`

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
logging:
  deviceAdded: true
  messageNotFound: False
  packetNotFromIndoorOutdoor: False
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

### v0.2.0 - 2025-02-18
- Changed MQTT Auto Discovery Config Message from single Entitiy to all Entities at once, known devices are fully configured, not known empty (marked to delete)
- NASAPacket and NASAMessage are now bidirectional, can decode and encode Packets
- Improved data quality
  - Added crc16 Checksum check for any Packet to reduce incorrect value changes 
  - Only Packets from outdoor/Indoor Units are processed
- Folloiwng warnings moved to SkipInvalidPacketException and from warning to debug log level to reduce log entries
  - Source Adress Class out of enum
  - Destination Adress Class out of enum
  - Checksum for package could not be validatet calculated
  - Message with structure type must have capacity of 1.
- added new logging config property to allow to turn on/off additional info log entries
 - deviceAdded set to true (default) will log when new device is added to known Devices (and discover to HASS)
 - messageNotFound set to true (false is default) will log when a received message was not found in NasaRepository
 - packetNotFromIndoorOutdoor set to true (false is default) will log when a message not from Indoor/Outdoor unit was received
- Added new Measurements
  - 0x4423 LVAR_IN_MINUTES_SINCE_INSTALLATION 
  - 0x4424 LVAR_IN_MINUTES_ACTIVE
  - 0x4426 LVAR_IN_GENERATED_POWER_LAST_MINUTE
  - 0x4427 LVAR_IN_TOTAL_GENERATED_POWER
- NASA Repository, measurements enums completed
  - ENUM_IN_FSV_3041: enum edited
  - ENUM_IN_FSV_3071: enum edited
  - ENUM_IN_FSV_4021: enum edited
  - ENUM_IN_FSV_4041: enum edited
  - ENUM_IN_FSV_4051: enum edited
  - ENUM_IN_FSV_4053: enum edited
  - ENUM_IN_FSV_5022: enum edited
  - ENUM_IN_FSV_5042: enum edited
  - ENUM_IN_FSV_5081: enum edited
  - ENUM_IN_FSV_5091: enum edited
  - ENUM_IN_FSV_2093: enum edited
  - ENUM_IN_FSV_2094: enum edited
  - VAR_IN_FSV_2011: desc edited
  - VAR_IN_FSV_2012: desc edited
  - VAR_IN_FSV_2021: desc edited
  - VAR_IN_FSV_2022: desc edited
  - VAR_IN_FSV_2031: desc edited
  - VAR_IN_FSV_2032: desc edited
  - ENUM_IN_FSV_2041: desc edited
  - VAR_IN_FSV_2051: desc edited
  - VAR_IN_FSV_2052: desc edited
  - VAR_IN_FSV_2061: desc edited
  - VAR_IN_FSV_2062: desc edited
  - VAR_IN_FSV_2071: desc edited
  - VAR_IN_FSV_2072: desc edited
  - ENUM_IN_FSV_2093: desc edited
  - VAR_IN_FSV_3021: desc edited
  - VAR_IN_FSV_3022: desc edited
  - VAR_IN_FSV_3023: desc edited
  - VAR_IN_FSV_3024: desc edited
  - VAR_IN_FSV_3025: desc edited
  - VAR_IN_FSV_3026: desc edited
  - VAR_IN_FSV_3032: desc edited
  - VAR_IN_FSV_3033: desc edited
  - VAR_IN_FSV_3041: desc edited
  - VAR_IN_FSV_3042: desc edited
  - VAR_IN_FSV_3043: desc edited
  - VAR_IN_FSV_3044: desc edited
  - VAR_IN_FSV_3045: desc edited
  - VAR_IN_FSV_3046: desc edited
  - ENUM_IN_FSV_3051: desc edited
  - ENUM_IN_FSV_3052: desc edited
  - ENUM_IN_FSV_3071: desc edited
  - ENUM_IN_FSV_3081: desc edited
  - ENUM_IN_FSV_3082: desc edited
  - ENUM_IN_FSV_3083: desc edited
  - VAR_IN_FSV_4011: desc edited
  - VAR_IN_FSV_4012: desc edited
  - VAR_IN_FSV_4013: desc edited
  - VAR_IN_FSV_4021: desc edited
  - VAR_IN_FSV_4022: desc edited
  - VAR_IN_FSV_4023: desc edited
  - VAR_IN_FSV_4024: desc edited
  - VAR_IN_FSV_4025: desc edited
  - VAR_IN_FSV_4031: desc edited
  - VAR_IN_FSV_4032: desc edited
  - VAR_IN_FSV_4033: desc edited
  - VAR_IN_FSV_4041: desc edited
  - VAR_IN_FSV_4042: desc edited
  - VAR_IN_FSV_4043: desc edited
  - VAR_IN_FSV_4044: desc edited
  - VAR_IN_FSV_4045: desc edited
  - VAR_IN_FSV_4046: desc edited
  - VAR_IN_FSV_4051: desc edited
  - VAR_IN_FSV_4052: desc edited
  - VAR_IN_FSV_4053: desc edited
  - VAR_IN_FSV_4061: desc edited
  - VAR_IN_FSV_5011: desc edited
  - VAR_IN_FSV_5012: desc edited
  - VAR_IN_FSV_5013: desc edited
  - VAR_IN_FSV_5014: desc edited
  - VAR_IN_FSV_5015: desc edited
  - VAR_IN_FSV_5016: desc edited
  - VAR_IN_FSV_5017: desc edited
  - VAR_IN_FSV_5018: desc edited
  - VAR_IN_FSV_5019: desc edited
  - VAR_IN_FSV_5021: desc edited
  - VAR_IN_FSV_5023: desc edited
  - ENUM_IN_FSV_5022: desc edited
  - ENUM_IN_FSV_5041: desc edited
  - ENUM_IN_FSV_5042: desc edited
  - ENUM_IN_FSV_5043: desc edited
  - ENUM_IN_FSV_5051: desc edited
  - VAR_IN_FSV_5083: desc edited
  - VAR_IN_FSV_5082: desc edited
  - ENUM_IN_FSV_5081: desc edited
  - ENUM_IN_FSV_5091: desc edited
  - ENUM_IN_FSV_5094: desc edited
  - VAR_IN_FSV_5092: desc edited
  - VAR_IN_FSV_5093: desc edited

### v0.1.0Beta - 2025-02-08
- Initial Commit