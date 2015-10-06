#!/bin/bash

cd $(dirname $0)

NEW_VERSION=$(awk 'match($0, /^__VERSION__ = "([0-9]+)\.([0-9]+)"$/, arr) { arr[2] = arr[2] + 1; printf("%d.%d", arr[1], arr[2]) }' setup.py)
sed -i "s/^__VERSION__ = .*/__VERSION__ = \"$NEW_VERSION\"/g" setup.py

echo "Do you want to build DEB package? [y/n]"
read confirm && if [ "$confirm" = 'y' ]; then 
    gbp dch -R --urgency=low --debian-tag='%(version)s' --git-author --new-version=$NEW_VERSION
    debuild -i -I
    git add setup.py debian/changelog
fi

echo "Do you want to upload package to PYPI? [y/n]"
read confirm && if [ "$confirm" = 'y' ]; then
    python setup.py sdist upload
fi

git commit -m "Version $NEW_VERSION"
git tag -m "" $NEW_VERSION
