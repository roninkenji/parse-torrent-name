import re

from .patterns import patterns, types


class PTN:

    def _escapeRegex(self, string):
        return re.sub('[\-\[\]{}()*+?.,\\\^$|#\s]', '\\$&', string)

    def __init__(self):
        self.torrent = None
        self.excess_raw = None
        self.groupRaw = None
        self.start = None
        self.end = None
        self.title_raw = None
        self.parts = None

    def _part(self, name, match, raw, clean):
        # The main core instructuions
        self.parts[name] = clean

        if len(match) != 0:
            # The instructions for extracting title
            index = self.torrent['name'].find(match[0])
            if index == 0:
                self.start = len(match[0])
            elif self.end is None or index < self.end:
                self.end = index

        if name != 'excess':
            # The instructions for adding excess
            if name == 'group':
                self.groupRaw = raw

            if raw is not None:
                self.excess_raw = self.excess_raw.replace(raw, '')

    def _late(self, name, clean):
        if name == 'group':
            self._part(name, [], None, clean)
        elif name == 'episodeName':
            clean = re.sub('[\._]', ' ', clean)
            clean = re.sub('_+$', '', clean)
            self._part(name, [], None, clean.strip())

    def parse(self, name):
        self.parts = {}
        self.torrent = {'name': name}
        self.excess_raw = name
        self.groupRaw = ''
        self.start = 0
        self.end = None
        self.title_raw = None

        for key, pattern in patterns.iteritems():
            if key == 'codec':
                match = re.findall(pattern, self.torrent['name'], re.I)
            else:
                match = re.findall(pattern, self.torrent['name'])
            if len(match) == 0:
                continue

            index = {}
            if isinstance(match[0], tuple):
                match = list(match[0])
            if len(match) > 1:
                index['raw'] = 0
                index['clean'] = 1
            else:
                index['raw'] = 0
                index['clean'] = 0

            if key in types.keys() and types[key] == 'boolean':
                clean = True
            else:
                clean = match[index['clean']]

                if key in types.keys() and types[key] == 'integer':
                    clean = int(clean)

            if key == 'group':
                if re.search(patterns['codec'], clean, re.I) \
                        or re.search(patterns['quality'], clean):
                    continue

                if re.match('[^ ]+ [^ ]+ .+', clean):
                    key = 'episodeName'

            if key == 'episode':
                self.torrent['map'] = re.sub(match[index['raw']], '{episode}',
                                             self.torrent['name'])

            self._part(key, match, match[index['raw']], clean)

        # Start process for title
        raw = self.torrent['name']
        if self.end is not None:
            raw = raw[self.start:self.end].split('(')[0]

        clean = re.sub('^ -', '', raw)

        if clean.find(' ') == -1 and clean.find('.') != -1:
            clean = re.sub('\.', ' ', clean)

        clean = re.sub('_', ' ', clean)
        clean = re.sub('([\(_]|- )$', '', clean).strip()

        self._part('title', [], raw, clean)

        # Start process for end
        clean = re.sub('(^[-\. ]+)|([-\. ]+$)', '', self.excess_raw)
        clean = re.sub('[\(\)\/]', ' ', clean)
        match = re.split('\.\.+| +', clean)
        if len(match) > 0 and isinstance(match[0], tuple):
            match = list(match[0])
        clean = filter(bool, match)

        if len(clean) != 0:
            groupPattern = clean[-1] + self.groupRaw
            if self.torrent['name'].find(groupPattern) == \
                    len(self.torrent['name']) - len(groupPattern):
                self._late('group', clean.pop() + self.groupRaw)

            if 'map' in self.torrent.keys() and len(clean) != 0:
                episodeNamePattern = (
                    '{episode}'
                    '' + re.sub('_+$', '', clean[0])
                )

                if self.torrent['map'].find(episodeNamePattern) != -1:
                    self._late('episodeName', clean.pop(0))

        if len(clean) != 0:
            if len(clean) == 1:
                clean = clean[0]

            self._part('excess', [], self.excess_raw, clean)

        return self.parts