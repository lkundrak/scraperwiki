#!/bin/bash

settings=$1

if [ -f "${settings}" ]; then
  user=`sed -n -e "s/^[ \t]*'USER' : '//p" $settings | sed "s/',//"`
  password=`sed -n -e "s/^[ \t]*'PASSWORD' : '//p" $settings | tr -d "'"`
  database=`sed -n -e "s/^[ \t]*'NAME' : '//p" $settings | sed "s/',//"`

  # Debug
  # echo $user, $password, $database

  sql='
SELECT
  username, count(user_id) AS "script_count", last_login, date_joined
FROM auth_user
JOIN codewiki_usercoderole
ON auth_user.id = codewiki_usercoderole.user_id
GROUP BY codewiki_usercoderole.user_id;'
  echo $sql | mysql -B -u$user -p$password $database
else
  echo
  echo I dump the user table delimited by tabs to stdout.
  echo Specify the settings.py file as the first argument.
  echo So run me like this.
  echo
  echo "    ./dump_user_table.sh ../settings.py|"
  echo "    tr '\t' , > `date --rfc-3339=date`.csv"
  echo
fi

