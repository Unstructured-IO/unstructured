#!/usr/bin/env bash

# get a string representing the system stats. we should be able to infer
# this from aws types, but this guarantees we have the info we need in all cases

# hack to get gpus available for processing
# assumes nvidia drivers available for inference tasks
if command -v nvidia-smi &>/dev/null; then
  gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
else
  gpu="0"
fi
if command -v sysctl >/dev/null && command -v system_profiler >/dev/null; then
  cpu=$(sysctl -n hw.logicalcpu_max)
  mem=$(sysctl -n hw.memsize | awk '{printf "%.0fGB",$0/1024/1024/1024}')
else
  cpu=$(getconf _NPROCESSORS_ONLN)
  mem=$(grep 'MemTotal' /proc/meminfo | awk '{printf "%.0fGB",$2/1024/1024}')
fi

echo "${cpu}cpu_${gpu}gpu_${mem}mem"
