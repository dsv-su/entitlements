import fileinput
from shutil import copyfile
import re

class EntmapHandler:
    def __init__(self, mapfile):
        self.mapfile = mapfile
        self.filehandler = FileHandler(self.mapfile)

    def open(self):
        return self.filehandler

    def read(self):
        entmappings = {}
        with open(self.mapfile, 'r') as mapfile:
            for line in mapfile:
                entitlement, handler, query = _parse_line(line)
                if not entitlement:
                    continue
                if entitlement not in entmappings:
                    entmappings[entitlement] = []
                entmappings[entitlement].append((handler,query))
        return entmappings

class FileHandler:
    def __init__(self, mapfile):
        self.mapfile = mapfile
        self.addmap = {}
        self.removemap = {}
        
    def __enter__(self):
        self.active = True
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.active = False
        if exc_type is None:
            self._commit()
        else:
            raise exc_value
        
    def _commit(self):
        entmaplines = []
        with open(self.mapfile, 'r') as mapfile:
            for line in mapfile:
                ent, handler, query = _parse_line(line)
                entmaplines.append((line, ent, handler, query))
        entmaplines.reverse()
        longest = 0
        for _, ent, _, _ in entmaplines:
            if ent and len(ent) > longest:
                longest = len(ent)
        out = []
        for line, ent, handler, query in entmaplines:
            if   (ent in self.removemap
                  and query in self.removemap[ent]):
                continue
            elif (ent in self.addmap):
                for user in self.addmap[ent]:
                    out.append(_format_line(ent.ljust(longest),
                                            'user',
                                            user))
                del self.addmap[ent]
            out.append(line)
        out.reverse()
        for ent in self.addmap:
            for user in self.addmap[ent]:
                out.append(_format_line(ent.ljust(longest),
                                        'user',
                                        user))
        out = ''.join(out)
        with open(self.mapfile, 'w') as mapfile:
            mapfile.write(out)
        return True
        
    def _check_active(self):
        if not self.active:
            raise Exception('This object is not in a usable state for this operation')

    def add(self, entitlement, user):
        self._check_active()
        if entitlement not in self.addmap:
            self.addmap[entitlement] = []
            self.addmap[entitlement].append(user)

    def remove(self, entitlement, user):
        self._check_active()
        if entitlement not in self.removemap:
            self.removemap[entitlement] = []
            self.removemap[entitlement].append(user)

def _parse_line(line):
    stripped = re.sub('(\s+|#.*)', '', line)
    if not stripped:
        return (None, '', '')
    entitlement, _, definition = stripped.partition('=')
    handler, _, query = definition.partition(':')
    return (entitlement, handler, query)

def _format_line(ent, handler, query):
    return '{} = {}:{}\n'.format(ent, handler, query)
    
