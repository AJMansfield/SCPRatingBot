#!/bin/bash

ok=0

if [[ $(python2.7 --version 2>&1 | head -c10) != 'Python 2.7' ]]
then
	echo "Need python 2.7!"
	echo "(do 'apt-get install python2.7' to fix this)"
	echo ""
	ok=1
fi

if [[ $(python -c 'import whiffle' 2>&1) != "" ]]
then
	echo "Need whiffle!"
	echo "(do 'pip install whiffle' to fix this)"
	echo ""
	ok=1
fi

if [[ $(parallel --version | head -c12) != 'GNU parallel' ]]
then
	echo "Need GNU Parallel!"
	echo "(do 'apt-get install parallel' to fix this)"
	echo ""
	ok=1
fi

if ! command -v ii >/dev/null 2>&1
then
	echo "Need Irc Improved!"
	echo "(do 'apt-get install ii' to fix this)"
	echo ""
	ok=1
fi

if [ $ok ]
then
	echo "No problems detected!"
fi
