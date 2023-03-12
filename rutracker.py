# -*- coding: utf-8 -*-
"""Module allows communicating with rutracker.net (mirror of rutracker.org)

You can search the tracker, get topic info text and download torrent files from rutracker.net
(rutracker.org or any other official mirror should work as well)
"""

import logging
import os
import re
import sys
import time
import unicodedata

from bs4 import BeautifulSoup
from bs4 import SoupStrainer
import requests

class Rutracker:
    """Main class for communicating with the tracker

    Usable methods:
    - search (search the tracker and get results as array)
    - get_info (get the description for the specified topic)
    - get_torrent (download .torrent file for the specified topic)
    """

    def __init__(self, login, password, tracker_url='https://rutracker.net/', logging_mode='', proxies={}):
        """Create an instance of Rutracker class

        Required arguments:
        - login (your rutracker login)
        - password (your rutracker password)

        Optional arguments:
        - tracker_url (mirror url, 'https://rutracker.net/' by default)
        - logging_mode ('console' or 'file', disabled by default)
        - proxies in requests format:
            for https proxy:
                {'https': 'https://user:pass@host:port/'}
            for socks proxy (you will also need requests[socks] package installed):
                {'https': 'socks5://user:pass@host:port'}

        Init will establish connection with rutracker.net or will raise an exception. You may be
        prompted to solve captcha during the first use. The captcha image will be saved as
        'captcha.jpg' in the working directry. After successful login, init will save cookies data
        to 'rt_cookies.txt' in the working directory. This data will be reused during the next
        sessions.
        """

        self.proxies = proxies
        self._setup_logging(logging_mode)
        self.tracker_path = tracker_url
        self.request_time = 0
        self.session_cookies = {}
        try:
            with open('rt_cookies.txt') as file:
                lines = file.read().splitlines()
            for line in lines:
                (key, value) = line.split(':')
                self.session_cookies[key] = value
            connected = self._test_connection()
        except:
            self.logger.warning('Error reading cookies from file')
            connected = False

        if not connected:
            cookies = self._login(login, password)
            self.session_cookies = cookies.get_dict()
            self._save_cookies(self.session_cookies)

    def _setup_logging(self, logging_mode):
        self.logger = logging.getLogger('rutracker')
        self.logger.setLevel(logging.DEBUG)

        if self.logger.handlers:
            return
        if logging_mode == 'console':
            handler = logging.StreamHandler()
        elif logging_mode == 'file':
            handler = logging.FileHandler('rutracker.log')
        else:
            return
        handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(name)s: %(asctime)s: %(message)s')

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.debug('Logging started')

    def _save_cookies(self, session_cookies):
        with open('rt_cookies.txt', 'w') as output:
            for key in session_cookies:
                line = ':'.join((key, self.session_cookies[key]))
                line += '\n'
                output.write(line)
            self.logger.info('Cookies saved to file')

    def search(self, search_line):
        """Search the tracker

        IN: Search line
        OUT: List of all result, each results a list of columns:
        - forum
        - topic
        - topic id
        - size (in bytes, approx.)
        - number of seeds (negative number means days without seeds)
        - number of leeches
        - number of downloads
        - date added (as UNIX time)

        """
        self.logger.info('Searching for \'{}\''.format(search_line))
        raw = self._ask_tracker('search', search=search_line)
        soup = BeautifulSoup(raw, 'html.parser')

        # How much pages have we got?
        found = soup.find_all('p', {'class': 'med bold'})
        for tag in found:
            if 'Результатов поиска:' in tag.text:
                total_found = int(re.findall(': (\d+) \(', tag.text)[0])
                pages = int((total_found / 50) + 1)
                self.logger.info('{} result(s) on {} page(s) found'.format(total_found, pages))
                break

        # Get search id, if more than one page
        if pages > 1:
            found = soup.find_all('script')
            for script in found:
                if 'PG_BASE_URL' in script.text:
                    search_id = re.findall('search_id=(\w+)', script.text)[0]
                    self.logger.debug('Search id is {}'.format(search_id))
                    break

        # Get data from the page
        search_results = self._parse_table(raw)

        # Get all other pages if any
        if pages == 1:
            return search_results

        for page in range(2, pages + 1):
            raw = self._ask_tracker('searchpage', search_id=search_id, page_no=page)
            search_results += self._parse_table(raw)

        if len(search_results) != total_found:
            raise ValueError('{} results found, but {} returned'.format(str(total_found), str(len(search_results))))

        return search_results

    def _parse_table(self, raw):
        # In: Raw psearch page; Out: Array of search results
        parse_only = SoupStrainer(['a', 'td'])
        soup = BeautifulSoup(raw, 'html.parser', parse_only=parse_only)

        # This part will break alot!
        try:
            boards = [i.text.strip('\n') for i in soup.findAll('td', {'class': 'row1 f-name-col'})]
            topics = [i.text.strip('\n') for i in soup.findAll('td', {'class': 'row4 med tLeft t-title-col tt'})]
            links = [int(i.get('data-topic_id')) for i in soup.findAll('a', {'class': 'med tLink tt-text ts-text hl-tags bold'})]
            sizes = [self._convert_size(i.text) for i in soup.findAll('td', {'class': 'row4 small nowrap tor-size'})]
            seeds = [int(i.text) for i in soup.findAll('td', {'class': 'row4 nowrap'})]
            leeches = [int(i.text) for i in soup.findAll('td', {'class': 'row4 leechmed bold'})]
            downloads = [int(i.text) for i in soup.findAll('td', {'class': 'row4 small number-format'})]
            added = [int(i.get('data-ts_text')) for i in soup.findAll('td', {'class': 'row4 small nowrap'})]
        except Exception as e:
            raise e

        search_results = [i for i in zip(boards, topics, links, sizes, seeds, leeches, downloads, added)]

        return search_results

    def _convert_size(self, size):
        size = unicodedata.normalize('NFKD', size)
        size = size.split(' ')[:2]
        ind = ['B', 'KB', 'MB', 'GB', 'TB']
        return int(float(size[0]) * 1024 ** ind.index(size[1]))

    def get_info(self, topic_id):
        """Get topic description

        IN: Topic_id
        OUT: Unformatted topic description text
        """
        raw = self._ask_tracker('viewtopic', topic_id=str(topic_id))
        soup = BeautifulSoup(raw, 'html.parser')
        description = soup.find('div', {'class': 'post_body'}).extract()

        return description.get_text()

    def get_torrent(self, topic_id, name='', path=''):
        """Get torrent file

        IN:
        Required:
        - Torrent id (topic_id).
        Optional:
        - Name (name will be used as a filename. Torrent id will be used otherwise)
        - Path (working directory will be used by default)

        OUT: name.torrent file path
        """

        torrent = self._ask_tracker('downloadtorrent', topic_id=str(topic_id))
        if not name:
            name = str(topic_id)
        name = os.path.join(path, name)
        filename = '{}.torrent'.format(name)
        with open(filename, 'wb') as file:
            for chunk in torrent:
                file.write(chunk)

        return filename

    def _ask_tracker(self, mode, search='', search_id='', page_no=1, topic_id=''):
        # Choose request type
        if mode == 'search':
            url = self.tracker_path + 'forum/tracker.php?nm={}'.format(search)
        elif mode == 'searchpage':
            page_no = int(page_no)
            url = self.tracker_path + 'forum/tracker.php?search_id={}&start={}'.format(search_id, (page_no - 1) * 50)
        elif mode == 'viewtopic':
            url = self.tracker_path + 'forum/viewtopic.php?t={}'.format(topic_id)
        elif mode == 'downloadtorrent':
            url = self.tracker_path + 'forum/dl.php?t={}'.format(topic_id)

        # Rate limiter (N per second)
        rate = 1
        since_last_request = time.time() - self.request_time
        if since_last_request < 1/rate:
            time.sleep(1/rate - since_last_request)

        # Apply cookies and get
        errors = 0
        status_code = 0
        while status_code != 200:
            try:
                with requests.session() as session:
                    session.cookies.update(self.session_cookies)
                    self.request_time = time.time()
                    response = session.get(url, proxies=self.proxies)
                    status_code = response.status_code
                    self.logger.debug(':'.join((str(status_code), url)))
            except:
                errors += 1
                self.logger.exception('Exception during request: {}'.format(sys.exc_info()))
                status_code = 0
            finally:
                if errors >= 2:
                    raise ValueError('Errors during requests')

            if status_code != 200:
                errors += 1
            if errors >= 2:
                raise ValueError('Wrong replies')

            if 'login-form-quick' in response.text:
                raise ValueError('Looks like i\'m no longer logged in')

            if mode == 'downloadtorrent':
                return response
            else:
                return response.text

    def _login(self, login_username, login_password):
        url = self.tracker_path + 'forum/login.php'
        login_data = {
            'login_username': login_username,
            'login_password': login_password,
            'login':'вход'
        }

        # Start session
        with requests.Session() as session:
            # Try to login
            post_response = session.post(url, data=login_data, proxies=self.proxies)

            # Solve captcha
            if 'captcha' in post_response.text:
                soup = BeautifulSoup(post_response.text, 'html.parser')
                # Search for captcha params
                inputs = soup.findAll('input')
                for i in inputs:
                    if not i.get('name'):
                        continue
                    if i.get('name') == 'cap_sid':
                        login_data['cap_sid'] = i.get('value')
                    if 'cap_code_' in i.get('name'):
                        cap_code = i.get('name')
                        login_data[cap_code] = ''

                # Search for captcha image and save it to the drive
                imgs = soup.findAll('img')
                for image in imgs:
                    if 'captcha' in image.get('src'):
                        caplink = image.get('src')
                        q = caplink.find('?')
                        caplink = caplink[:q]
                        break
                response = requests.get(caplink, stream=True, proxies=self.proxies)
                with open('captcha.jpg', 'wb') as file:
                    for chunk in response:
                        file.write(chunk)

                # Ask user to solve captcha from file
                captcha = input('Enter captcha:')
                login_data[cap_code] = captcha
                os.remove('captcha.jpg')

            # Login with captcha and test login status
            post_response = session.post(url, data=login_data, proxies=self.proxies)
            if 'logged-in-username' in post_response.text:
                self.logger.info('Login successful')
            else:
                raise ConnectionError('Failed to log in')

        return session.cookies

    def _test_connection(self):
        with requests.session() as session:
            session.cookies.update(self.session_cookies)
            response = session.get(self.tracker_path + 'forum/index.php', proxies=self.proxies)
            if response.status_code != 200:
                print('Wrong reply during connection test')
            if 'logged-in-username' in response.text:
                self.logger.info('Login successful')
                return True

        return False
