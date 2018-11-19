#!/usr/bin/env python3

from inspect import getsourcefile
from os.path import dirname, realpath, abspath
import configparser
import argparse
import re

from handlers.DaisyHandler import DaisyHandler
from handlers.LdapHandler import LdapHandler
from handlers.EntitlementHandler import EntitlementHandler, EntitlementException

scriptpath = dirname(realpath(abspath(getsourcefile(lambda:0))))
config = configparser.ConfigParser()
config.read(scriptpath + '/config.ini')
config['ldap']['entbase'] = config['general']['entitlement_base']
config['entitlementAPI']['entbase'] = config['general']['entitlement_base']
config['entitlementAPI']['cachefile'] = scriptpath + '/ent-cache'

print('Setting up...', end='', flush=True)
ldap = LdapHandler(config['ldap'])
daisy = DaisyHandler(config['daisyAPI'])
api = EntitlementHandler(config['entitlementAPI'])
print('done.')

print('Reading entitlement map...', end='', flush=True)
entmappings = {}
with open(scriptpath + '/entmap.conf', 'r') as entmap:
    for line in entmap:
        temp = re.sub('([ \n]+|#.*)', '', line)
        if not temp:
            continue
        entitlement, definition = temp.split('=', 1)
        handler, query = definition.split(':', 1)
        if entitlement not in entmappings:
            entmappings[entitlement] = []
        entmappings[entitlement].append((handler,query))
print('done.')

failed = {}
def update_failed(entitlement, action, user):
    if entitlement not in failed:
        failed[entitlement] = {}
    if action not in failed[entitlement]:
        failed[entitlement][action] = []
    failed[entitlement][action].append(user)

print('Updating entitlements:')
with api.open() as sukat:
    for entitlement, definitions in entmappings.items():
        print(' Updating {}:'.format(entitlement))
        print('  Getting list of current members...',
              end='',
              flush=True)
        entitled_users = set(ldap.getEntitledUsers(entitlement))
        print('done.')
        print('  Found {} members.'.format(len(entitled_users)))
        print('  Getting list of expected members...',
              end='',
              flush=True)
        expected_users = set()
        for (handler, query) in definitions:
            temp_set = None
            if handler == 'ldap':
                temp_set = set(ldap.search(query))
            elif handler == 'daisy':
                temp_set = set(daisy.search(query))
            elif handler == 'user':
                temp_set = set([query])
            else:
                raise Exception('Unknown handler: {}'.format(handler))
            expected_users.update(temp_set)
        print('done.')
        print('  Found {} users.'.format(len(expected_users)))
        users_to_add = expected_users - entitled_users
        users_to_remove = entitled_users - expected_users
        print('  Updating values: {} to add, {} to remove...'.format(
            len(users_to_add),
            len(users_to_remove)), end='', flush=True)
        for user in users_to_add:
            success = sukat.add(entitlement, user)
            if not success:
                update_failed(entitlement, 'add', user)
        for user in users_to_remove:
            success = sukat.remove(entitlement, user)
            if not success:
                update_failed(entitlement, 'remove', user)
        print('done.')
        
if failed:
    print('')
    print('Problems were encountered with the following actions:')
    for entitlement, actions in failed.items():
        for action, users in actions.items():
            for user in users:
                print('{} {} {}'.format(user, action, entitlement))
    exit(1)
exit(0)
