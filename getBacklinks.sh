#!/bin/bash
source ./getAuth.sh

getLinks(){

	pname=$1
	pid=$2

	response="$(\
	curl 'http://www.scp-wiki.net/ajax-module-connector.php' \
		-H "Cookie: $cookie; $token" \
		-H 'Origin: http://www.scp-wiki.net' \
		-H 'Accept-Encoding: gzip, deflate' \
		-H 'Accept-Language: en-US,en;q=0.8' \
		-H 'User-Agent: scpRank' \
		-H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
		-H 'Accept: */*' \
		-H "Referer: http://www.scp-wiki.net/$pname" \
		-H 'X-Requested-With: XMLHttpRequest' \
		-H 'Connection: keep-alive' \
		--data "page_id=$pid&moduleName=backlinks%2FBacklinksModule&$token" \
		--compressed \
		--silent \
	| python2.7 -c "import json,sys;obj=json.load(sys.stdin);print obj['body'];" 2>/dev/null \
	)"

	if test $? -ne 0;
	then
		echo "$pname $pid getLnk" >> errors.log;
		exit 1;
	fi

	echo $response \
	| hxselect -ci -s '\n' 'li' \
	| grep -oP '(?<=href="/)[^"/]*' \
	| sed -e "s/$/\t$pname/" \

}
export -f getLinks;


cat pids.tsv \
| parallel -j4 --retries 3 --colsep '\t' --bar getLinks \
| awk -F'\t' 'NF == 2' \
> links.tsv;