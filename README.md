# Rutracker search and get

## What is this:
Module that communicates with https://rutracker.net (mirror of rutracker.org). You can search the tracker, get topic info text, and download torrent files. Module should work with rutracker.org or any other official mirror. 

**New**: Proxies! (as all rutracker mirrors are blocked for many people these days anyway)

**Module works with Python 3.6** and utilizes the following 3-rd party modules:
* Requests (requests[socks] if you use socks5 proxy)
* Beautiful Soup

## Usage:

Module contains the single Rutracker class. Import and create an instance, providing rutracker credentials.

```
from rutracker import Rutracker

x = Rutracker('yourlogin', 'yourpassword')
```

The module will either login successfully or throw an exception.

You may be prompted to enter captcha, when logging in for the first time. The module will save captcha image as 'captcha.jpg' in working directory.
After successful login, the module will save cookies in 'rt_cookies.txt' in working directory and will reuse them for future sessions.

Optionally you may supply alternative mirror url ('https://rutracker.net/' is used by default):
    
```x = Rutracker('yourlogin', 'yourpassword', tracker_url='https://rutracker.cr/')```

You may provide proxy as a dictionary (like in requests):
* for https proxy: `proxies = {'https': 'https://user:pass@host:port'}`
* for socks proxy: `proxies = {'https': 'socks5://user:pass@host:port'}`

```x = Rutracker('yourlogin', 'yourpassword', proxies={'https': 'https://user:pass@host:port'})```

---
You may use the following methods with your new instance:

`search('search string')` - search the tracker. Outputs the list of topics, each a list of the fields:
* forum
* topic
* topic id
* size (in bytes, approx.)
* number of seeds (negative number means days without seeds)
* number of leeches
* number of downloads
* date added (as UNIX time)  

`x.search('the man with a movie camera')`

---
`get_info(topic_id)` - get topic description text.  
	
 `x.get_info(5050254)`

---
`get_torrent(topic_id)` - download torrent files. Optional fields:  
* name (name will be used as a filename. Torrent id will be used otherwise)
* path (working directory will be used by default)   

 `x.get_torrent(5050254)`