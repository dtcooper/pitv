#!/bin/sh

if [ "$#" -lt 2 ]; then
    echo "Usage: $(basename "$0") infile.mkv outfile.mp4 [subtitles.srt]"
    exit 0
fi

SUBTITLES=""
if [ "$3" ]; then
    SUBTITLES=",subtitles=$3:force_style='Fontsize=24'"
fi

exec ffmpeg -i "$1" \
        -map 0 -map -0:s \
        -c:v libx264 \
        -profile:v high \
        -preset fast \
        -crf 18 \
        -b-pyramid none \
        -vf "scale=720x480,setdar=3/2${SUBTITLES}" \
        -c:a copy \
     "$2"
