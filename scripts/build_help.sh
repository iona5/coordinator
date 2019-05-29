#!/bin/bash

set -ex

if [ ! -z $1 ]; then cd $1; fi

python3 -m markdown2 -x smarty-pants README.md > help/index.html
# images src should now be "images/image.png" instead of "help/images/image.png":
sed -i 's|src=\"help\/images|src=\"images|' help/index.html