# SCPRatingBot

This was originally designed to perform collaborative filtering on the SCP articles based on vote data, and has expanded since then to include a chatbot interface and a crosslink visualization tool.

In order to use this, you will need a few things:

0. You need to add a file `getAuth.sh` that contains a set of active wikidot session tokens for a user.

  You can get these tokens by using the network activity recorder in your browser and examining the cookies sent with each request to the site. The file should look like this:

      #!/bin/bash
      export token='wikidot_token7=15pl9ir2kxzsn86ebt37';
      export cookie='WIKIDOT_SESSION_ID_88764372=_domain_cookie_2238949_b8e40705561b9c9441e662253c8e46e0';
    
  (Obviously not my real session tokens.)
    
0. To use features that use the actual wikidot API (none at present), you need to add a `identity.ini` file with your username, API key, and site identifier.

        [default@wikidot]
        user: SomeUsername
        key: EpvnM8DKr8BfJsbyulLKytH7N4Jg6x09
        site: scp-wiki
        
  (Obviously not my real api key.)

0. To use the chatbot features, you need to add a `connection.ini` file:
    
        [ScpRank]
        Server: irc.example.net
        Channel: #channelName
        Nickname: your_nickname
        Password: none
        
 Once that is done, you need to `make all` and then you can run the various python scripts to do the different things.
        
