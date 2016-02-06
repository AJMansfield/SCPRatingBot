#!/bin/bash

urls=0;
series=0;

errors=$(mktemp);

if [ $urls ]
then

	out(){
		echo -e "$1\tresponse $2";
	}

	poll(){
		for retry in $(seq 0 10)
		do
			res=$(curl -I --write-out %{http_code} --silent --output /dev/null "http://www.scp-wiki.net/scp-$1");
			
			if (( $res >= 500 || $res == 000 ))
			then
				#out $1 $res $retry;
				sleep 0.1;
				continue;
			fi

			break;
		done
		
		if (( $res != 200 )) #|| $retry != 0 ))
		then
			out $1 $res $retry;
		fi;
	}

	export -f out;
	export -f poll;

	echo "Checking mainlist URLs for irregular response codes:"

	{	seq -w 000 999;
		seq -w 1000 2999;
	} \
	| parallel -j 64 --bar poll \
	>> $errors;
fi;



if [ $series ]
then

	checkLink(){
		if [[ $1 != $2 ]]
		then
			echo -e "$1\tfrom: $2";
			echo -e "$2\tbadlink: /$1";
		fi;
	}



	export -f checkLink;

	echo "Checking series pages for nonconformant linking:"

	{
		curl --silent "http://www.scp-wiki.net/scp-series";
		curl --silent "http://www.scp-wiki.net/scp-series-2";
		curl --silent "http://www.scp-wiki.net/scp-series-3";
	} \
	| hxselect -c -s '\n' '#page-content .content-panel #toc2 ~ ul li' 2>/dev/null \
	| sed -r 's#(<[^>]*>)?<a (class="newpage" )?href="/(scp-([0-9]*)|(.*))">(SCP-([0-9]*)|(.*))</a>.*#\4\5\t\7\8#gi; /^\s*$/d' \
	| parallel --colsep '\t' --bar checkLink \
	>> $errors;
fi;

echo "Summarizing:"

cat $errors \
| sort

rm $errors;