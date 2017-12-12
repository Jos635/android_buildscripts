#! /bin/bash

OUT="lineageos-14.1-berlin-`date +%Y-%m-%d-%H%M`.zip"
ZIP="`ls -dt out/dist/*.zip | head -n 1`"
echo "ZIP file: $ZIP"

./build/tools/releasetools/ota_from_target_files --block --backup=true "$ZIP" "$OUT"

