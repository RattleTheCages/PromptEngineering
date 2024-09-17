#!/bin/bash

# Description: User takes the file of the serial data produced by the recorder
#              and produces a C++ data object to use in the Arduino servo player code.

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <input_file>"
  exit 1
fi

input_file="$1"
output_file="data_array.cc"

pot1=()
pot2=()
pot3=()

# Read the input file and extract the values
while IFS= read -r line
do
  pot1_val=$(echo "$line" | sed -n 's/.*Pot1: \([0-9]*\).*/\1/p')
  pot2_val=$(echo "$line" | sed -n 's/.*Pot2: \([0-9]*\).*/\1/p')
  pot3_val=$(echo "$line" | sed -n 's/.*Pot3: \([0-9]*\).*/\1/p')
  pot1+=("$pot1_val")
  pot2+=("$pot2_val")
  pot3+=("$pot3_val")
done < "$input_file"

# Determine the number of elements (n)
n=${#pot1[@]}

# Create the C++ array file
{
  echo "const int n = $n;"
  echo "int data[3][$n] PROGMEM = {"
  echo "  {"
  for i in ${!pot1[@]}; do
    if (( i != 0 )); then echo -n ", "; fi
    echo -n "${pot1[$i]}"
  done
  echo "  },"
  echo "  {"
  for i in ${!pot2[@]}; do
    if (( i != 0 )); then echo -n ", "; fi
    echo -n "${pot2[$i]}"
  done
  echo "  },"
  echo "  {"
  for i in ${!pot3[@]}; do
    if (( i != 0 )); then echo -n ", "; fi
    echo -n "${pot3[$i]}"
  done
  echo "  }"
  echo "};"
} > "$output_file"



