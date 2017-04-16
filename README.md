# Rutracker search and get

## What is this:
Module allows communicating with <htps://rutracker.net> (mirror of rutracker.org). You can search the tracker, get topic info text and download torrent files. Module should work with rutracker.org or any other official mirror.

**Module works with Python 3.6** and utilises the following 3-rd party modules:
* Requests
* Beautiful Soup

## Usage:
Module contains the single Rutracker class. Import and create an instance, providing rutracker credentals.

```
from rutracker import Rutracker

x = Rutracker('yourlogin', 'yourpassword')
```

The module will either login successfully or throw an exception.

You may have to solve captcha, when loging in for the fist time. The module will save captcha image as 'captcha.jpg' in working directory.
After successful login the module will save cookies in 'rt_cookies.txt' in working directory and will reuse them for future sessions.

Optionaly you may supply alternative mirror url ('https://rutracker.net/' is used by default):
    
`x = Rutracker('yourlogin', 'yourpassword', tracker_url='https://rutracker.cr/')`


You may use the following methods with your new instance:
* search - search the tracker

   IN: Search line
   OUT: List of all results, each result a list of columns:
   * forum
   * topic
   * topic id
   * size (in bytes, approx.)
   * number of seeds (-1 if none)
   * number of leeches
   * number of downloads
   * date added (as UNIX time)
   
   example: `x.search('the man with a movie camera')`

* get_info - get topic description text
        IN: Topic id
        OUT: Unformatted topic description text
	example: 'x.get_info(5050254)'

* get_torrent - download torrent files
	IN: Torrent id (topic id).
	Optional: 
		- name (name will be used as a filename. Torrent id will be used otherwise)
		- path (working directory will be used by default)
        OUT: '{name}.torrent' file saved to {path}
		example: 'x.get_torrent(5050254)'
