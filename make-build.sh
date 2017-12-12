#! /bin/bash

NUM_CORES="`grep -c ^processor /proc/cpuinfo`"

echo "Using $NUM_CORES cores"

source build/envsetup.sh

lunch lineage_berlin-userdebug

make -j $NUM_CORES

mka target-files-package dist

./make-update-zip.sh
