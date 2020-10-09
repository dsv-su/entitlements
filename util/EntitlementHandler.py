import requests
from requests_kerberos import HTTPKerberosAuth
from subprocess import call
import os

class EntitlementHandler:
    def __init__(self, conf):
        class Requestor:
            def __init__(self, conf):
                self.active = False
                self.entbase = conf['entbase']
                self.cache = conf['cachefile']
                self.princ = conf['principal']
                self.key = conf['keytab']
                self.url = conf['url'].rstrip('/')
                self.session = requests.Session()
                self.session.auth = HTTPKerberosAuth()
            
            def __enter__(self):
                os.environ['KRB5CCNAME'] = self.cache
                call(['kinit', '-t', self.key, self.princ])
                self.active = True
                return self
            
            def __exit__(self, exc_type, exc_value, traceback):
                call(['kdestroy'])
                del os.environ['KRB5CCNAME']
                self.active = False

            def __update(self, method, user, entitlement):
                if not self.active:
                    raise Exception('This object is not in a usable state for this operation')
                path = '{}/{}/{}'.format(self.url,
                                         user,
                                         self.entbase + entitlement)
                r = self.session.request(method,
                                         path)
                if r.status_code in range(200, 299):
                    return True
                return False
        
            def add(self, entitlement, user):
                return self.__update('PUT', user, entitlement)
            
            def remove(self, entitlement, user):
                return self.__update('DELETE', user, entitlement)

            def get(self, user):
                path = '{}/{}'.format(self.url, user)
                r = self.session.get(path)
                if r.status_code in range(200, 299):
                    return r.json()['entitlements']
                return False
    
        self.requestor = Requestor(conf)

    def open(self):
        return self.requestor

class EntitlementException(Exception):
    def __init__(self, request):
        self.request = request

    def getRequest(self):
        return self.request
    
