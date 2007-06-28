# $Id$

import conny, ui, urlregex, util
import os, re, socket, sys, webbrowser

# textbrowsers
textbrowsers = ('w3m', 'lynx', 'links', 'elinks')
# gopher capable browsers that do not need gopher proxy
gophers = ('lynx', 'firefox')

def getlocals():
    '''Returns valid local addresses.'''
    l = socket.gethostbyaddr(socket.gethostname())
    localaddresses = ['127.0.0.1']
    for i in l:
        if isinstance(i, str):
            i = [i]
        localaddresses += i
    return localaddresses

def weburlregex(ui):
    '''Returns regex matching web url.'''
    u = urlregex.urlregex(ui, uniq=False)
    u.urlobject(search=False)
    return u.url_re


class browser(object):
    '''
    Visits items with default or given browser.
    '''
    def __init__(self, parentui=None, items=None, app=''):
        self.ui = parentui or ui.ui()
        self.ui.updateconfig()
        self.items = items             # urls
        if app:
            self.ui.app = app          # browser app
        self.ui.proto = 'web'
        self.weburl_re = weburlregex(self.ui) # check remote url protocol scheme
        self.conn = False              # try to connect to net
        self.local_re = None           # check local protocol scheme
        self.file_re = None            # strip file url

    def get_localre(self):
        '''Compiles local_re on demand and returns it.'''
        if not self.local_re:
            self.local_re = re.compile('http://(%s)'
                    % '|'.join(re.escape(a) for a in getlocals()),
                    re.IGNORECASE)
        return self.local_re

    def mkfileurl(self, url):
        '''Compiles file_re on demand and returns it.'''
        if not self.file_re:
            self.file_re = re.compile(r'file:/+', re.IGNORECASE)
        # strip url to pure pathname
        url = self.file_re.sub('/', url, 1)
        url = util.absolutepath(url)
        if not os.path.exists(url):
            raise util.DeadMan('%s: file not found' % url)
        return 'file://%s' % url

    def urlcomplete(self, url):
        '''Adapts possibly short url to pass as browser argument.'''
        if self.weburl_re.match(url):
            self.conn = True
            url = urlregex.webschemecomplete(url)
            if url.startswith('gopher://') and self.ui.app not in gophers:
                # use gateway when browser is not gopher capable
                url = url.replace('gopher://',
                        'http://gopher.floodgap.com/gopher/gw?')
        elif not self.get_localre().match(url):
            url = self.mkfileurl(url)
        return url

    def urlvisit(self):
        '''Visit url(s).'''
        if not self.items:
            self.items = [self.ui.configitem('net', 'homepage')]
        self.items = [self.urlcomplete(url) for url in self.items]
        if self.conn:
            conny.goonline(self.ui)
        app = os.path.basename(self.ui.app)
        notty = not util.termconnected()
        screen = app in textbrowsers and 'STY' in os.environ
        # w3m does not need to be connected to terminal
        # but has to be connected if called into another screen instance
        if screen or app in textbrowsers[1:] and notty:
            for url in self.items:
                util.systemcall([self.ui.app, url], notty=notty, screen=screen)
        else:
            try:
                if self.ui.app:
                    b = webbrowser.get(self.ui.app)
                else:
                    b = webbrowser.get()
                for url in self.items:
                    b.open(url)
            except webbrowser.Error, inst:
                raise util.DeadMan(inst)
