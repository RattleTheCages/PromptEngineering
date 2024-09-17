#!/bin/noop /bin/bash

# These are the steps to install the Arduino AI IDE development environment for QK AI IDE.

wget https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_64bit.tar.gz
tar -xvzf arduino-cli_latest_Linux_64bit.tar.gz
./arduino-cli config init
./arduino-cli core update-index
./arduino-cli core install arduino:avr

./arduino-cli sketch new blink_led
./arduino-cli compile --fqbn arduino:avr:uno blink_led
./arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno blink_led











