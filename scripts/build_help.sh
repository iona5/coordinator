#!/bin/bash

set -e

if [ ! -z $1 ]; then cd $1; fi

if [ -z $2 ] ; then
	CODE_REF=unknown
else
	CODE_REF=$2
fi

python3 -m markdown2 -x smarty-pants,header-ids README.md > help/index.html
# images src should now be "images/image.png" instead of "help/images/image.png":
sed -i 's|src=\"help\/images|src=\"images|' help/index.html

# remove some chapters:
sed -i '/id="coordinator-plugin"/,/id="basics"/d' help/index.html

# replace last chapter with links:
sed -i '/known-issues-limitations-planned-features/,$d' help/index.html
echo '<h2 id="help-links">Links</h2>
<ul>
<li><a href="https://plugins.qgis.org/plugins/coordinator/">Plugin homepage on plugins.qgis.org</a></li>
<li><a href="https://github.com/iona5/coordinator">Github page</a></li>
<li><a href="https://github.com/iona5/coordinator/issues">Bug Reports</a></li>
</ul>' >> help/index.html

echo "<p style='font-size: 8pt; font-style: italic; text-align: right'>git commit: ${CODE_REF}</p>" >> help/index.html
