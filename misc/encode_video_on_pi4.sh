#!/bin/sh

if [ "$#" -ne 2 ]; then
    echo "Usage: $(basename "$0") infile.mkv outfile.mp4"
    exit 0
fi

exec ffmpeg -i "$1" \
        -c:v h264_v4l2m2m \
        -pix_fmt yuv420p \
        -num_output_buffers 32 \
        -num_capture_buffers 16 \
        -b:v 3M \
        -vf scale=720x480,setdar=3/2 \
        -c:a copy \
     "$2"
