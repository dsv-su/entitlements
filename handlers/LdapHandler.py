from handlers.Handler import Handler
from ldap3 import Server, Connection

class LdapHandler(Handler):
    def __init__(self, conf):
        self.base = 'dc=su,dc=se'
        self.entbase = conf['entbase']
        self.url = conf['url'].rstrip('/')
        self.conn = Connection(self.url,
                               user=conf['user'],
                               password=conf['password'],
                               read_only=True,
                               auto_range=True,
                               auto_bind=True)

    def search(self, query):
        # possibly relevant attributes:
        # ['uid', 'eduPersonEntitlement', 'memberOf']
        result = self.conn.search(
            self.base,
            query,
            attributes=['uid'])
        out = []
        if not result:
            return out
        for item in self.conn.entries:
            out.append(str(item.uid))
        return out
        
    def getEntitledUsers(self, entitlement):
        fqe = self.entbase + entitlement
        query = '(eduPersonEntitlement={})'.format(fqe)
        return self.search(query)

    def getStaff(self):
        query = '(memberOf=cn=dsv-staff,dc=dsv,dc=su,dc=se)'
        return self.search(query)

    def getUser(self, uid):
        query = '(uid={})'.format(uid)
        return self.search(query)
