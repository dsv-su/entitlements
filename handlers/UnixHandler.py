import re

from handlers.Handler import Handler

class UnixHandler(Handler):
    def __init__(self, conf):
        self.passwdfile = conf['passwd_file']
        self.groupfile = conf['group_file']
        self.cache = {}

    def search(self, groupname):
        if groupname not in self.cache:
            self.cache[groupname] = self._read_groupinfo(groupname)
        return self.cache[groupname]

    def _read_groupinfo(self, groupname):
        groupset = set()
        with open(self.groupfile, 'r') as f:
            for line in f:
                if not line.startswith(f'{groupname}:'):
                    continue
                line = line.rstrip()

                # The format of a group line is:
                # groupname:*:gid:users
                _, _, gid, userstring = line.split(':')

                # The format of a userstring is:
                # uid1,uid2,...
                userlist = userstring.split(',')
                groupset.update(userlist)

        if gid:
            # The format of a passwd line is:
            # username:*:uid:gid:name:homedir:shell
            passwdpattern = re.compile(f'^(.*):.*:.*:{gid}')
            with open(self.passwdfile, 'r') as f:
                for line in f:
                    result = passwdpattern.match(line)
                    if result:
                        groupset.add(result.group(1))

        return groupset
