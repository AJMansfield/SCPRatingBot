#!/bin/bash

# sets $token and $cookie to the appropriate values
source ./getAuth.sh

# gets records of all user votes on a page
getVotes(){

	pname=$1
	pid=$2
	aid=$4

	response=$(mktemp);

	vote=$(mktemp);
	uid=$(mktemp);
	uname=$(mktemp);

	# Add author vote, since author's can't upvote their own stuff
	echo -e $pid'\t'$aid'\t+1' \
	> $vote;

	#requet user vote data
	curl 'http://www.scp-wiki.net/ajax-module-connector.php' \
	  -H "Cookie: wikidot_udsession=1; $cookie; $token;" \
	  -H 'Origin: http://www.scp-wiki.net' \
	  -H "Referer: http://www.scp-wiki.net/$pname" \
	  -H 'Accept-Encoding: gzip, deflate' \
	  -H 'Accept-Language: en-US,en;q=0.8' \
	  -H 'User-Agent: scpRank' \
	  -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
	  -H 'Accept: */*' \
	  -H 'X-Requested-With: XMLHttpRequest' \
	  -H 'Connection: keep-alive' \
	  --data "pageId=$pid&moduleName=pagerate%2FWhoRatedPageModule&callbackIndex=1&$token" \
	  --compressed \
	  --silent \
	| python2.7 -c "import json,sys;obj=json.load(sys.stdin);print obj['body'];" 2>/dev/null \
	> $response;

	if test $? -ne 0;
	then
		rm $response $vote $uid $uname;
		echo "$pname user" >> errors.log;
		exit 1;
	fi
	#extract vote data from response
	cat $response \
	| hxselect -ci -s '\n' 'span[style*="color:#777"]' \
	| tr -d ' ' \
	| tr -s '\n' \
	| sed -e 's/$/1/' \
	| tail -n +2 \
	>> $vote;

	cat $response \
	| hxselect -ci -s '\n' 'a' \
	| grep -oP '(?<=userid=)[0-9]*' \
	>> $uid;

	cat $response \
	| hxselect -ci -s '\n' 'a' \
	| grep -oP '(?<=alt=")[^"]*' \
	>> $uname;

	#zip data together into output format
	paste $uid $vote \
	| sed -e "s/^/$pid\t/" \
	| awk -F'\t+' 'NF == 3';

	paste $uid $uname \
	| awk -F'\t+' 'NF == 2' \
	>> uids2.tsv;

	#clean up temporary files
	rm $response $vote $uid $uname;
}
export -f getVotes;

#retrieves a list of page names
getPages(){
	curl --silent 'http://www.scp-wiki.net/sitemap_page_1.xml' \
	| hxselect -ci -s '\n' 'url loc' \
	| sed -e 's#^http://www.scp-wiki.net/##';
}

#retrieves the pid number for a given page name
getPid(){
	pname="$1";

	# get author vote data (since author's can't upvote their own work)
	page="$(curl --silent "http://www.scp-wiki.net/$pname")"

	pid="$(echo $page \
		| grep -oP '(?<=pageId = )[0-9]*' )"

	ptitle="$(echo $page \
		| hxselect -ci -s '\n' 'div#page-title' 2>/dev/null \
		| sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
		| tr -d '\n' \
		| perl -MHTML::Entities -pe 'decode_entities($_);' )"

	if test $? -ne 0;
	then
		echo "$pname getPid" >> errors.log;
		exit 1;
	fi

	response="$(curl 'http://www.scp-wiki.net/ajax-module-connector.php' \
	  -H "Cookie: wikidot_udsession=1; $cookie; $token;" \
	  -H 'Origin: http://www.scp-wiki.net' \
	  -H "Referer: http://www.scp-wiki.net/$pname" \
	  -H 'Accept-Encoding: gzip, deflate' \
	  -H 'Accept-Language: en-US,en;q=0.8' \
	  -H 'User-Agent: scpRank' \
	  -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
	  -H 'Accept: */*' \
	  -H 'X-Requested-With: XMLHttpRequest' \
	  -H 'Connection: keep-alive' \
	  --data "page=1&perpage=20&page_id=$pid&options=%7B%22new%22%3Atrue%7D&moduleName=history%2FPageRevisionListModule&callbackIndex=3&$token" \
	  --compressed \
	  --silent \
	| python2.7 -c "import json,sys;obj=json.load(sys.stdin);print obj['body'];" 2>/dev/null )"

	if test $? -ne 0;
	then
		echo "$pname $pid getAid" >> errors.log;
		exit 1;
	fi

	aid="$(echo $response \
	| hxselect -ci -s '\n' 'a' 2>/dev/null \
	| grep -oP '(?<=userid=)[0-9]*' )"

	aname="$(echo $response \
	| hxselect -ci -s '\n' 'a' 2>/dev/null \
	| grep -oP '(?<=alt=")[^"]*' )"

	date="$(echo $response \
	| grep -oP '(?<=odate time_)[0-9]*' )"

	echo -e $aid'\t'$aname >> uids2.tsv;

	echo -e $pname'\t'$pid'\t'$ptitle'\t'$aid'\t'$date;

	exit $?;
}
export -f getPid;

getOverrides() {
curl --silent 'http://scprank.wikidot.com/author-override' \
| hxselect -ci -s '\t\n' 'table.wiki-content-table tr td' \
| perl -pe 's|<span class="printuser avatarhover">.*?userid=([[:digit:]]+).*?<\/span>|\1|g' \
| xargs -L 3 -d '\n' echo \
| sed "s/[[:blank:]]*$//"
}



# check robots.txt to make sure we are allowed in
# Currently, there are no restrictions at all, so this just checks in case
# a new rule is added that applies to this bot. If a rule gets added, we
# will need to add something else to make sure we are still allowed.
echo "Checking robots.txt"
curl 'http://www.scp-wiki.net/robots.txt' \
  -H 'User-Agent: scpRank' \
  --silent \
| grep -i 'scpRank|User-agent: \*' \
> /dev/null

if [ ! $? ];
then
	echo 'Uh-oh, robots.txt has a rule in it that applies to this bot! We might still be allowed, but please check first!';
	exit 1;
fi;




echo "Updating page list"
newpages=$(mktemp);

getPages \
| sort \
> $newpages;



echo "Updating page ID table";

echo "" > uids2.tsv; #clear user ID list

# filter out names of pages that are already known, and download all new pages
touch pages.tsv;
comm -13 pages.tsv $newpages \
| parallel -j4 --retries 3 --bar getPid \
>> pids.tsv;
mv $newpages pages.tsv;

sort -u pids.tsv -o pids.tsv;

getOverrides > override.tsv

echo "Generating vote database";
votes=$(mktemp);
cat pids.tsv \
| parallel -j4 --retries 3 --colsep '\t' --bar getVotes \
> $votes;

if [ ! $? ];
then
	echo "Something went wrong; not updating tables.";
	rm $votes uids2.tsv;
fi
#only update main files once everything is done
awk -F'\t+' 'NF == 2' < uids2.tsv > uids.tsv;
mv $votes votes.tsv;
