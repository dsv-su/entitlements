#!/usr/bin/env python3

from inspect import getsourcefile
from os.path import dirname, realpath, abspath
import argparse
import configparser
import logging
import sys

from handlers.LdapHandler import LdapHandler
from handlers.DaisyHandler import DaisyHandler
from handlers.UserHandler import UserHandler
from handlers.NoneHandler import NoneHandler

from util.EntitlementHandler import EntitlementHandler
from util.EntmapHandler import EntmapHandler

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
parser.add_argument('entitlements',
                    nargs='*',
                    metavar='<entitlement>',
                    help="If present, only act on these entitlements. \
                    If not present, act on all entitlements.")
args = parser.parse_args()

config = configparser.ConfigParser()
config.read(scriptpath + '/config.ini')

loglevel = config['general'].get('log_level', 'INFO')
if args.debug:
    loglevel = 'DEBUG'

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))
log.setLevel(loglevel)

if args.dry_run:
    log.info('Dry run requested. No changes will actually be applied.')

log.debug('Initializing...')
config['ldap']['entbase'] = config['general']['entitlement_base']
config['entitlementAPI']['entbase'] = config['general']['entitlement_base']
config['entitlementAPI']['cachefile'] = scriptpath + '/ent-cache'
keytab = config['entitlementAPI']['keytab']
if not keytab.startswith('/'):
    config['entitlementAPI']['keytab'] = '{}/{}'.format(scriptpath, keytab)

ldap = LdapHandler(config['ldap'])
daisy = DaisyHandler(config['daisyAPI'])
user = UserHandler()
none = NoneHandler()
api = EntitlementHandler(config['entitlementAPI'])
log.debug('Initialization done.')

log.debug('Parsing entitlement map...')
mapfile = config['general']['entitlement_map']
if not mapfile.startswith('/'):
    mapfile = '{}/{}'.format(scriptpath, mapfile)
entmaphandler = EntmapHandler(mapfile)
entmappings = entmaphandler.read(args.entitlements)
log.debug('Finished parsing entitlement map.')

failed = []

log.debug('Updating entitlements:')
with api.open() as sukat:
    for entitlement, definitions in sorted(entmappings.items()):
        log.info(' Updating %s:', entitlement)
        log.debug('  Getting list of current members...')
        entitled_users = set(ldap.getEntitledUsers(entitlement))
        log.debug('  Found %s current members.', len(entitled_users))
        log.debug('  Getting list of expected members...')
        expected_users = set()
        for (handler, query) in definitions:
            temp_set = None
            if handler == 'ldap':
                temp_set = set(ldap.search(query))
            elif handler == 'daisy':
                temp_set = set(daisy.search(query))
            elif handler == 'user':
                temp_set = set(user.search(query))
            elif handler == 'none':
                temp_set = set(none.search(query))
            else:
                raise Exception('Unknown handler: {}'.format(handler))
            expected_users.update(temp_set)
        log.debug('  Found %s expected members.', len(expected_users))
        users_to_add = expected_users - entitled_users
        users_to_remove = entitled_users - expected_users
        num_to_add = len(users_to_add)
        num_to_remove = len(users_to_remove)
        if num_to_add > 0:
            if not args.only_remove:
                log.info('  Adding %s users...', num_to_add)
                if not args.dry_run:
                    for u in users_to_add:
                        log.debug('   %s', u)
                        try:
                            sukat.add(entitlement, u)
                        except Exception as e:
                            failed.append((entitlement, 'add', u, e))
            else:
                log.info('  %s users can be added.', num_to_add)
        else:
            log.info('  No users to add.')
        if num_to_remove:
            if not args.only_add:
                log.info('  Removing %s users...', num_to_remove)
                if not args.dry_run:
                    for u in users_to_remove:
                        log.debug('   %s', u)
                        try:
                            sukat.remove(entitlement, u)
                        except Exception as e:
                            failed.append((entitlement, 'remove', u, e))
            else:
                log.info('  %s users can be removed.', num_to_remove)
        else:
            log.info('  No users to remove.')

if failed:
    log.error('')
    log.error('Problems were encountered with the following actions:')
    for (ent, action, user, error) in failed:
        log.error('%s %s %s\n  %s', ent, action, user, error)
    exit(1)
exit(0)
