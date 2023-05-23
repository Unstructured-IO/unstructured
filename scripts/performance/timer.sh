#!/bin/bash

export TIMEFORMAT="%R"
timer_out=$( { time sleep 0.34; } 2>&1 );
echo "Timer output: $timer_out"