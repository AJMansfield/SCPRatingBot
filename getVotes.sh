#!/bin/bash

getVotes(){

	pid=$1
	pname=$2

	response=$(mktemp);

	curl 'http://www.scp-wiki.net/ajax-module-connector.php' \
	  -H 'Cookie: wikidot_udsession=1; WIKIDOT_SESSION_ID_b18d85b5=_domain_cookie_2238949_4d39ed1d113a6457fc66106c07199514; wikidot_token7=1jl18yw4s4i;' \
	  -H 'Origin: http://www.scp-wiki.net' \
	  -H 'Accept-Encoding: gzip, deflate' \
	  -H 'Accept-Language: en-US,en;q=0.8' \
	  -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
	  -H 'Accept: */*' \
	  -H "Referer: http://www.scp-wiki.net/$pname" \
	  -H 'X-Requested-With: XMLHttpRequest' \
	  -H 'Connection: keep-alive' \
	  --data "pageId=$pid&moduleName=pagerate%2FWhoRatedPageModule&callbackIndex=1&wikidot_token7=1jl18yw4s4i" \
	  --compressed \
	  --silent \
	| python2.7 -c "import json,sys;obj=json.load(sys.stdin);print obj['body'];" 2>/dev/null \
	> $response;

	if test $? -ne 0;
	then
		rm $response;
		echo "$2" >> errors.log;
		exit 1;
	fi

	vote=$(mktemp)
	cat $response \
	| hxselect -ci -s '\n' 'span[style*="color:#777"]' \
	| tr -d ' ' \
	| tr -s '\n' \
	| sed -e 's/$/1/' \
	| tail -n +2 \
	> $vote;

	uid=$(mktemp)
	cat $response \
	| hxselect -ci -s '\n' 'a' \
	| grep -oP '(?<=userid=)[0-9]*' \
	> $uid;

	uname=$(mktemp)
	cat $response \
	| hxselect -ci -s '\n' 'a' \
	| grep -oP '(?<=alt=")[^"]*' \
	> $uname;

	rm $response;

	paste $uid $vote \
	| sed -e "s/^/$pid\t/" \
	| awk -F'\t+' 'NF == 3';

	paste $uid $uname \
	| awk -F'\t+' 'NF == 2' \
	>> uids.tsv

	rm $vote $uid $uname;
}
export -f getVotes

getPages(){
	python2.7 -c 'from whiffle import wikidotapi; print "\n".join(str(p) for p in wikidotapi.connection().Pages)';
}

getPids(){
	xargs curl --silent "http://www.scp-wiki.net/$1" \
	| grep -oP '(?<=pageId = )[0-9]*' ;
}
export -f getPids


>&2 echo "Getting page list."

pname=$(mktemp)
getPages \
| sort -R \
> $pname

>&2 echo "Generating page ID table";

pids=$(mktemp)

cat $pname \
| parallel -j32 --bar getPids \
> $pids

paste $pids $pname \
> pids.tsv

rm $pids $pname

>&2 echo "Getting votes for each page";


echo "" > uids.tsv;

log=$(mktemp)

cat pids.tsv \
| parallel -j16 --retries 3 --halt soon,fail=1% --colsep '\t' --bar getVotes \
| sort -n \
| awk -F'\t+' 'NF == 3' \
> votes.tsv

rm $log

temp=$(mktemp)

cat pids.tsv \
| sort -u \
| awk -F'\t+' 'NF == 2' \
> $temp;
cp $temp pids.tsv;

cat uids.tsv \
| sort -un \
| awk -F'\t+' 'NF == 2' \
> $temp;
cp $temp uids.tsv;

rm $temp;