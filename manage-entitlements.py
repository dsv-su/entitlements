#!/usr/bin/env python3

from inspect import getsourcefile
from os.path import dirname, realpath, abspath
import argparse
import configparser
import sys

from util.EntitlementHandler import EntitlementHandler
from util.EntmapHandler import EntmapHandler

scriptpath = dirname(realpath(abspath(getsourcefile(lambda:0))))
config = configparser.ConfigParser()
config.read(scriptpath + '/config.ini')
config['entitlementAPI']['entbase'] = config['general']['entitlement_base']
config['entitlementAPI']['cachefile'] = scriptpath + '/ent-cache'
keytab = config['entitlementAPI']['keytab']
if not keytab.startswith('/'):
    config['entitlementAPI']['keytab'] = '{}/{}'.format(scriptpath, keytab)

parser = argparse.ArgumentParser(description='Manage entitlements in SUKAT')
userhelp = "The user(s) to be acted upon. If no users given, read users from stdin."
addhelp = "Add one or more entitlements to the given user(s). Can be specified multiple times."
delhelp = "Delete one or more entitlements from the given users(s). Can be specified multiple times."
maphelp = "Don't update entmap.conf to reflect the changes made."

parser.add_argument('user',
                    nargs='*',
                    metavar='<username>',
                    help=userhelp)
parser.add_argument('--add', '-a',
                    action='append',
                    nargs='*',
                    metavar='<entitlement>',
                    help=addhelp)
parser.add_argument('--remove', '-r',
                    action='append',
                    nargs='*',
                    metavar='<entitlement>',
                    help=delhelp)
parser.add_argument('--no-entmap-update',
                    action='store_true',
                    help=maphelp)
args = parser.parse_args()  

def flatten(l):
    out=[]
    if not l:
        return []
    for item in l:
        if isinstance(item, list):
            out.extend(item)
        else:
            out.append(item)
    return out

users = args.user
if not users:
    users = sys.stdin.read().split()

toadd = flatten(args.add)
todel = flatten(args.remove)

api = EntitlementHandler(config['entitlementAPI'])
maphandler = EntmapHandler(config['general']['entitlement_map'])
with api.open() as sukat, maphandler.open() as entmap:
    for user in users:
        if not toadd and not todel:
            print('No actions specified.')
            exit(1)
        for ent in todel:
            success = sukat.remove(ent, user)
            if not success:
                print('Failed: remove {} from {}'.format(ent, user))
            else:
                if not args.no_entmap_update:
                    entmap.remove(ent, user)
        for ent in toadd:
            success = sukat.add(ent, user)
            if not success:
                print('Failed: add {} to {}'.format(ent, user))
            else:
                if not args.no_entmap_update:
                    entmap.add(ent, user)
