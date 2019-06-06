#!/usr/bin/env python3

from inspect import getsourcefile
from os.path import dirname, realpath, abspath
import argparse
from enum import Enum
import configparser

from handlers.DaisyHandler import DaisyHandler
from handlers.LdapHandler import LdapHandler
from handlers.EntitlementHandler import EntitlementHandler, EntitlementException
from handlers.EntmapHandler import EntmapHandler

scriptpath = dirname(realpath(abspath(getsourcefile(lambda:0))))

mainhelp = 'Update entitlements in SUKAT according to entmap.conf.'
parser = argparse.ArgumentParser(description=mainhelp)
parser.add_argument('--dry-run',
                    action='store_true',
                    help="Don't make any changes, only print what would be done.")
parser.add_argument('--debug',
                    action='store_true',
                    help="Show extra output for debug purposes.")
group = parser.add_mutually_exclusive_group()
group.add_argument('--only-add',
                   action='store_true',
                   help="Only add entitlements, don't remove any.")
group.add_argument('--only-remove',
                   action='store_true',
                   help="Only remove entitlements, don't add any.")
args = parser.parse_args()

class Msglevel(Enum):
    ERROR, INFO, DEBUG = range(3)
    
def show(message, message_level=Msglevel.INFO, linefeed=True):
    args = {}
    if(not linefeed):
        args['end'] = ''
        args['flush'] = True
    if(info_level.value >= message_level.value):
        print(message, **args)

info_level = Msglevel.INFO
if args.debug:
    info_level = Msglevel.DEBUG
    
if args.dry_run:
    show('Dry run requested. No changes will actually be applied.',
         Msglevel.INFO)

show('Setting up...', Msglevel.DEBUG, linefeed=False)
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
show('done.', Msglevel.DEBUG)

show('Reading entitlement map...', Msglevel.DEBUG, linefeed=False)
mapfile = config['general']['entitlement_map']
if not mapfile.startswith('/'):
    mapfile = '{}/{}'.format(scriptpath, mapfile)
entmaphandler = EntmapHandler(mapfile)
entmappings = entmaphandler.read()
show('done.', Msglevel.DEBUG)

failed = {}
def update_failed(entitlement, action, user):
    if entitlement not in failed:
        failed[entitlement] = {}
    if action not in failed[entitlement]:
        failed[entitlement][action] = []
    failed[entitlement][action].append(user)

show('Updating entitlements:', Msglevel.DEBUG)
with api.open() as sukat:
    for entitlement, definitions in sorted(entmappings.items()):
        show(' Updating {}:'.format(entitlement))
        show('  Getting list of current members...',
             Msglevel.DEBUG, linefeed=False)
        entitled_users = set(ldap.getEntitledUsers(entitlement))
        show('done.', Msglevel.DEBUG)
        show('  Found {} members.'.format(len(entitled_users)),
             Msglevel.DEBUG)
        show('  Getting list of expected members...',
             Msglevel.DEBUG, linefeed=False)
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
        show('done.', Msglevel.DEBUG)
        show('  Found {} users.'.format(len(expected_users)),
             Msglevel.DEBUG)
        users_to_add = expected_users - entitled_users
        users_to_remove = entitled_users - expected_users
        num_to_add = len(users_to_add)
        num_to_remove = len(users_to_remove)
        if num_to_add:
            if not args.only_remove:
                show('  Adding {} users...'.format(num_to_add),
                     linefeed=False)
                if not args.dry_run:
                    for user in users_to_add:
                        success = sukat.add(entitlement, user)
                        if not success:
                            update_failed(entitlement, 'add', user)
                show('done.')
            else:
                show('  {} users can be added.'.format(num_to_add))
        else:
            show('  No users to add.')
        if num_to_remove:
            if not args.only_add:
                show('  Removing {} users...'.format(num_to_remove),
                     linefeed=False)
                if not args.dry_run:
                    for user in users_to_remove:
                        success = sukat.remove(entitlement, user)
                        if not success:
                            update_failed(entitlement, 'remove', user)
                show('done.')
            else:
                show('  {} users can be removed.'.format(num_to_remove))
        else:
            show('  No users to remove.')

if failed:
    show('', Msglevel.ERROR)
    show('Problems were encountered with the following actions:',
         Msglevel.ERROR)
    for entitlement, actions in failed.items():
        for action, users in actions.items():
            for user in users:
                show('{} {} {}'.format(entitlement, action, user),
                     Msglevel.ERROR)
    exit(1)
exit(0)
