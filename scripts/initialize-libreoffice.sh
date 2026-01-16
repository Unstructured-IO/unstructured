#!/bin/bash

/usr/bin/soffice --headless || [ $? -eq 81 ] || exit 1
