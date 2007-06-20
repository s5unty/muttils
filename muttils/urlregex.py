# $Id$

import util
import re

valid_protos = ['all', 'web', 'http', 'ftp', 'gopher', 'mailto', 'mid']
# finger, telnet, whois, wais?

reserved = r';/?:@&=+$,'
unreserved = r"-_.!~*'()a-z0-9"
escaped = r'(%[0-9a-f]{2})' # % 2 hex
# 1 or more unreserved|escaped + 0 or 1 reserved
uric = r'([%s%s]+|%s+)' % (unreserved, reserved, escaped)

def hostname(generic=False):
    '''Returns hostname pattern
    for all top level domains or just generic domains.'''
    domainlabel = r'[a-z0-9]+([-a-z0-9]+[a-z0-9])?'
    # generic domains
    generics = ['aero', 'arpa', 'biz', 'cat', 'com', 'coop',
                'edu', 'gov', 'info', 'int', 'jobs', 'mil', 'mobi', 'museum',
                'name', 'net', 'org', 'pro', 'root', 'travel']
    # top level domains
    tops = generics + ['a[cdefgilmnoqrstuwz]', 'b[abdefghijmnorstvwyz]',
                       'c[acdfghiklmnoruvxyz]', 'd[ejkmoz]', 'e[ceghrstu]',
                       'f[ijkmor]', 'g[abdefghilmnpqrstuwy]',
                       'h[kmnrtu]', 'i[delnmoqrst]', 'j[emop]',
                       'k[eghimnprwyz]', 'l[abcikrstuvy]',
                       'm[acdeghklmnopqrstuvwxyz]', 'n[acefgilopruz]', 'om',
                       'p[aefghklmnrstwy]', 'qa', 'r[eosuw]',
                       's[abcdeghijklmnortuvyz]',
                       't[cdfghjkmnoprtvwz]', 'u[agkmsyz]',
                       'v[acegivu]', 'w[fs]', 'y[etu]', 'z[amw]']
    if generic:
        tds = generics
    else:
        tds = tops
    # a sequence of domainlabels + top domain
    return r'(%s\.)+(%s)' % (domainlabel, '|'.join(tds))

def weburlpats(search, proto='', uric=uric):
    '''Creates 2 url patterns. The first according to protocol,
    The second may contain spaces but is enclosed in '<>'.
    If no protocol is given the pattern matches only
    generic top level domains:
        gmx.net:    counts as url
        gmx.de:     does not as url
        www.gmx.de: counts as url
    This seems a reasonable compromise between the goal to find
    malformed urls too and false positives -- especially as we
    treat "www" as sort of inofficial scheme.'''
    if search:
        hostport = r'%s(:\d+)?' % hostname(generic=not proto)
    else:
        hostnum = r'(\d+\.){3}\d+'
        hostport = r'(%s|%s)(:\d+)?' % (hostname(generic=not proto), hostnum)
    dom = r'''
        \b                  # start at word boundary
        %(proto)s           # protocol or empty
        %(hostport)s        # host and optional port (no login [yet])
        (                   # 0 or 1 group
          /                 #   slash
          %(uric)s +        #   1 or more uri chars
          (                 #   0 or 1 group
            \#              #     fragment separator
            %(uric)s +      #     1 or more uri chars
          ) ?
        ) ?
        (/|\b)              # slash or word boundary
        ''' % vars()
    spdom = r'''
        (?<=<)                # look behind for '<'
        %(proto)s             # protocol or empty
        %(hostport)s          # host and optional port (no login [yet])
        (                     # 0 or 1 group
          /                   #   slash
          (                   #   0 or 1 group
            (%(uric)s|\s) *   #   0 or more uri chars or space
            (                 #   0 or 1 group
              \#              #     fragment separator
              (%(uric)s|\s) + #     1 or more uri chars or space
            ) ?
          ) ?
        ) ?
        (?=>)                 # lookahead for '>'
        ''' % vars()
    return dom, spdom

def mailpat():
    '''Creates pattern for email addresses,
    grabbing those containing a subject first.'''
    address = '[-_.a-z0-9]+@%s' % hostname()
    return r'''
        \b(                 # word boundary and group open
          mailto:           #  mandatory mailto
          %(address)s       #  address
          \?subject=        #  ?subject=
          [^>]+             #  any except >
        |
          (mailto:) ?       #  optional mailto
          %(address)s       #  address
        )\b                 # close group and word boundary
        ''' % { 'address': address }

def nntppat():
    '''Creates pattern for either nntp protocol or
    attributions with message-ids.'''
    return r'''
        (                                              # 1 group
          msgid|news|nntp|message(-id)?|article|MID    #  attrib strings
        )
        (                                              # 1 group
          :\s*|\s+                                     # colon+optspace or space+
        )
        <{,2}                                          # 0--2 '<'
        '''

def midpat():
    '''Creates pattern for message ids.'''
    return r'[-_.a-z0-9#~?+=&%%!$[\]]+@%s' % hostname()

def declmidpat():
    '''Returns pattern for message id, prefixed with "attribution".'''
    return r'(\b%s%s\b)' % (nntppat(), midpat())

def wipepat():
    '''Creates pattern for useless headers in message _bodies_ (OLE!).'''
    headers = ('received', 'references', 'message-id', 'in-reply-to',
               'delivered-to', 'list-id', 'path', 'return-path',
               'newsgroups', 'nntp-posting-host', 'xref', 'x-id',
               'x-abuse-info', 'x-trace', 'x-mime-autoconverted')
    headers = r'(%s)' % '|'.join(headers)
    header = r'''
        (\n|^)          # newline or very start
        %s:             # header followed by colon &
        .+              # greedy anything (but newline)
        (               # 0 or more group
          \n            #  newline followed by
          [ \t]+        #  greedy spacetabs
          .+            #  greedy anything
        ) *?
        ''' % headers
    return r'%s|%s' % (header, declmidpat())

# regexes on demand
web_re = mail_re = ftp_re = None

def get_mailre():
    '''Returns email address pattern on demand.'''
    global mail_re
    if not mail_re:
        mail_re = re.compile(r'(%s)' % mailpat(), re.IGNORECASE|re.VERBOSE)
    return mail_re

def webschemecomplete(url):
    '''Returns url with protocol scheme prepended if needed.'''
    global web_re
    if not web_re:
        web_re = re.compile(r'(https?|s?ftp|gopher)://', re.IGNORECASE)
    if web_re.match(url):
        return url
    for scheme in ('ftp', 'gopher'):
        if url.startswith('%s.' % scheme):
            return '%s://%s' % (scheme, url)
    return 'http://%s' % url

def webcheck(url):
    '''Returns True if url is not email address.'''
    return not get_mailre().match(url)

def ftpcheck(url):
    '''Returns True if url is ftp location.'''
    global ftp_re
    if not ftp_re:
        ftp_re = re.compile(r'(s?ftp://|ftp\.)', re.IGNORECASE)
    return ftp_re.match(url)

def mailcheck(url):
    '''Returns True if url is email address.'''
    return get_mailre().match(url)

filterdict = { 'web':    webcheck, 'mailto': mailcheck }


class urlregex(object):
    '''
    Provides functions to extract urls from text,
    customized by attributes.
    Detects also www-urls that don't start with a protocol and
    urls spanning more than 1 line if they are enclosed in '<>'.
    '''
    def __init__(self, ui, uniq=True):
        self.ui = ui             # proto, decl
        self.uniq = uniq         # list only unique urls
        self.url_re = None       # that's what it's all about
        self.kill_re = None      # customized pattern to find non url chars
        self.protocol = ''       # pragmatic proto
                                 # (may include www., ftp., gopher.)
        self.proto_re = None
        self.items = []

    def setprotocol(self):
        mailto = 'mailto:\s?' # needed for proto=='all'
        http = r'(https?://|www\.)'
        ftp = r'(s?ftp://|ftp\.)'
        gopher = r'gopher(://|\.)'
        # finger, telnet, whois, wais?
        if self.ui.proto in ('all', 'web'):
            protocols = [http, ftp, gopher]
            if self.ui.proto == 'all':
                protocols.append(mailto)
            protocol = r'(%s)' % '|'.join(protocols)
        else:
            self.ui.decl = True
            protocol = eval(self.ui.proto)
        self.protocol = r'(url:\s?)?%s' % protocol

    def getraw(self, search):
        '''Returns raw patterns according to protocol.'''
        self.setprotocol()
        url, spurl = weburlpats(search, proto=self.protocol)
        if self.ui.decl:
            return r'(%s|%s)' % (spurl, url)
        any_url, any_spurl = weburlpats(search, proto='')
        return (r'(%s|%s|%s|%s|%s)'
                % (mailpat(), spurl, any_spurl, url, any_url))

    def unideluxe(self):
        '''remove duplicates deluxe:
        of http://www.blacktrash.org, www.blacktrash.org
        keep only the first, declared version.'''
        truncs = [self.proto_re.sub('', u) for u in self.items]
        deluxurls = []
        for i in xrange(len(self.items)):
            url = self.items[i]
            trunc = truncs[i]
            if truncs.count(trunc) == 1 or len(url) > len(trunc):
                deluxurls.append(url)
        self.items = deluxurls

    def urlfilter(self):
        if not self.ui.decl and self.ui.proto in filterdict:
            self.items = [i for i in self.items if filterdict[self.ui.proto](i)]
        if self.uniq:
            self.items = list(set(self.items))
            if self.ui.proto != 'mid' and not self.ui.decl:
                self.unideluxe()

    def urlobject(self, search=True):
        '''Creates customized regex objects of url.'''
        if self.ui.proto not in valid_protos:
            raise util.DeadMan(self.ui.proto,
                               ': invalid protocol parameter, use one of:\n',
                               ', '.join(valid_protos))
        if self.ui.proto == 'mailto':# be pragmatic and list not only declared
            self.url_re = get_mailre()
            self.proto_re = re.compile(r'^mailto:')
        elif self.ui.proto != 'mid':
            self.url_re = re.compile(self.getraw(search), re.IGNORECASE|re.VERBOSE)
            if search:
                self.kill_re = re.compile(r'^url:\s?|\s+', re.IGNORECASE)
                if not self.ui.decl:
                    self.proto_re = re.compile(r'^%s' % self.protocol,
                                               re.IGNORECASE)
        elif self.ui.decl:
            self.url_re = re.compile(declmidpat(), re.IGNORECASE|re.VERBOSE)
            if search:
                self.kill_re = re.compile(nntppat(), re.IGNORECASE|re.VERBOSE)
        else:
            self.url_re = re.compile(r'(\b%s\b)' % midpat(),
                                     re.IGNORECASE|re.VERBOSE)

    def findurls(self, text):
        '''Conducts a search for urls in text.
        Data is supposed to be text but tested whether
        it's a message/Mailbox (then passed to urlparser).'''
        self.urlobject() # compile url_re
        if self.ui.proto != 'mid':
            wipe_re = re.compile(wipepat(), re.IGNORECASE|re.VERBOSE)
            text = wipe_re.sub('', text)
            cpan = self.ui.configitem('net', 'cpan')
            ctan = self.ui.configitem('net', 'ctan')
            rawcan = r'C%sAN:\s*/?([a-zA-Z]+?)'
            for can in [(cpan, 'P'), (ctan, 'T')]:
                if can[0]:
                    cansub = r'%s/\1' % can[0].rstrip('/')
                    text = re.sub(rawcan % can[1], cansub, text)
        urls = [u[0] for u in self.url_re.findall(text)]
        if self.kill_re:
            urls = [self.kill_re.sub('', u) for u in urls]
        self.items += urls
        self.urlfilter()
        self.items.sort()
