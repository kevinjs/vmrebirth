#!/bin/sh

filename=$1

if [ -f "$filename" ]; then
echo 'Exist'
else
echo 'Not Exist'
fi
