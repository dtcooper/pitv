#!/bin/sh

if [ "$#" -lt 2 ]; then
    echo "Usage: $(basename "$0") infile.mkv outfile.mp4 [subtitles.srt]"
    exit 0
fi

SUBTITLES=""
if [ "$3" ]; then
    SUBTITLES=",subtitles=$3"
fi

exec ffmpeg -i "$1" \
        -c:v h264_v4l2m2m \
        -pix_fmt yuv420p \
        -num_output_buffers 32 \
        -num_capture_buffers 16 \
        -b:v 3M \
        -vf "scale=720x480,setdar=3/2${SUBTITLES}" \
        -c:a copy \
     "$2"
