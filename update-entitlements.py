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

mainhelp = 'Update entitlements in SUKAT according to a mapping file.'
parser = argparse.ArgumentParser(description=mainhelp)
maphelp = "Read entitlement mappings from this file. If omitted, mappings will be read from entmap.conf."
parser.add_argument('--mapfile',
                    default='entmap.conf',
                    help=maphelp)
parser.add_argument('--dry-run',
                    action='store_true',
                    help="Don't make any changes, only print what would be done.")
group = parser.add_mutually_exclusive_group()
group.add_argument('--only-add',
                   action='store_true',
                   help="Only add entitlements, don't remove any.")
group.add_argument('--only-remove',
                   action='store_true',
                   help="Only remove entitlements, don't add any.")
args = parser.parse_args()

print('Setting up...', end='', flush=True)
config = configparser.ConfigParser()
config.read(scriptpath + '/config.ini')
config['ldap']['entbase'] = config['general']['entitlement_base']
config['entitlementAPI']['entbase'] = config['general']['entitlement_base']
config['entitlementAPI']['cachefile'] = scriptpath + '/ent-cache'
keytab = config['entitlementAPI']['keytab']
if not keytab.startswith('/'):
    config['entitlementAPI']['keytab'] = '{}/{}'.format(scriptpath, keytab)

ldap = LdapHandler(config['ldap'])
daisy = DaisyHandler(config['daisyAPI'])
api = EntitlementHandler(config['entitlementAPI'])
print('done.')

print('Reading entitlement map...', end='', flush=True)
mapfile = args.mapfile
if not mapfile.startswith('/'):
    mapfile = '{}/{}'.format(scriptpath, mapfile)
entmappings = {}
with open(mapfile, 'r') as entmap:
    for line in entmap:
        stripped = re.sub('(\s+|#.*)', '', line)
        if not stripped:
            continue
        entitlement, _, definition = stripped.partition('=')
        handler, _, query = definition.partition(':')
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
            elif handler == 'none':
                temp_set = set()
            else:
                raise Exception('Unknown handler: {}'.format(handler))
            expected_users.update(temp_set)
        print('done.')
        print('  Found {} users.'.format(len(expected_users)))
        users_to_add = expected_users - entitled_users
        users_to_remove = entitled_users - expected_users
        num_to_add = len(users_to_add)
        num_to_remove = len(users_to_remove)
        if num_to_add:
            if not args.only_remove:
                print('  Adding {} users...'.format(num_to_add),
                      end='', flush=True)
                if not args.dry_run:
                    for user in users_to_add:
                        success = sukat.add(entitlement, user)
                        if not success:
                            update_failed(entitlement, 'add', user)
                print('done.')
            else:
                print('  {} users can be added.'.format(num_to_add))
        else:
            print('  No users to add.')
        if num_to_remove:
            if not args.only_add:
                print('  Removing {} users...'.format(num_to_remove),
                      end='', flush=True)
                if not args.dry_run:
                    for user in users_to_remove:
                        success = sukat.remove(entitlement, user)
                        if not success:
                            update_failed(entitlement, 'remove', user)
                print('done.')
            else:
                print('  {} users can be removed.'.format(num_to_remove))
        else:
            print('  No users to remove.')

if failed:
    print('')
    print('Problems were encountered with the following actions:')
    for entitlement, actions in failed.items():
        for action, users in actions.items():
            for user in users:
                print('{} {} {}'.format(entitlement, action, user))
    exit(1)
exit(0)
