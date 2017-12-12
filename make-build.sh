#! /bin/bash

source build/envsetup.sh

lunch lineage_berlin-userdebug

make -j 4

mka target-files-package dist

./make-update-zip.sh
