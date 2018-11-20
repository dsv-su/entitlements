#!/usr/bin/env python3

from inspect import getsourcefile
from os.path import dirname, realpath, abspath
import configparser
import argparse
import sys

from handlers.EntitlementHandler import EntitlementHandler, EntitlementException

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
addhelp = "Add one or more entitlements to the given user(s)."
delhelp = "Delete one or more entitlements from the given users(s)."

parser.add_argument('user',
                    nargs='*',
                    metavar='<username>',
                    help=userhelp)
parser.add_argument('--add',
                    action='append',
                    nargs='*',
                    metavar='<entitlement>',
                    help=addhelp)
parser.add_argument('--remove',
                    action='append',
                    nargs='*',
                    metavar='<entitlement>',
                    help=delhelp)
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
with api.open() as sukat:
    for user in users:
        if not toadd and not todel:
            print('No actions specified.')
            exit(1)
        for ent in todel:
            success = sukat.remove(ent, user)
            if not success:
                print('Failed: remove {} from {}'.format(ent, user))
        for ent in toadd:
            success = sukat.add(ent, user)
            if not success:
                print('Failed: add {} to {}'.format(ent, user))
