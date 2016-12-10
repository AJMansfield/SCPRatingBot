#!/bin/bash
source ./getAuth.sh

# pname=$1

# curl --silent "http://www.scp-wiki.net/$pname" \
# | hxselect -ci -s ',' '.page-tags span a' 2>/dev/null \
# | sed -e "s/^/$pname\t/"

getTags(){

	pname=$1

	curl --silent "http://www.scp-wiki.net/$pname" \
	| hxselect -ci -s ',' '.page-tags span a' 2>/dev/null \
	| sed -e "s/^/$pname\t/" 
	echo

}
export -f getTags;


cat pids.tsv \
| parallel -j4 --retries 3 --colsep '\t' --bar getTags \
> tags.tsv

