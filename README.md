# EHS-Sentinel
EHS Sentinel written in python which reads Samsung EHS serial Data and published it to MQTT/Home Asistent

change in config silentMode to False to get a lot of messages

1. python3 startEHSSentinel.py --configfile config.yml --dumpfile dump.txt
2. wait a few minutes then strg+c
3. python3 startEHSSentinel.py --configfile config.yml --dumpfile dump.txt --dryrun
4. search unique measerments: sort -u -t, -k1,3 prot.csv > prot_uniq.csv
5. count lines: wc -l prot_uniq.csv