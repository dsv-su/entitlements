# entitlements
A tool to manage entitlements in SUKAT

## Setup

 * Clone the repo
 * Make sure you have the python packages listed in dependencies.list installed on 
 your system.
 * Copy ```config.ini.example``` to ```config.ini``` and update with real credentials.
 * Create your entitlement map file according to the value of ```entitlement_map``` in 
 ```config.ini```. See ```entmap.conf.example``` and the section below for details on 
 the format.
 * Run update-entitlements.py to synchronize with SUKAT.
 
## update-entitlements.py

Synchronizes the entitlements in SUKAT with the desired state from entmap.conf.

```
usage: update-entitlements.py [-h] [--dry-run] [--debug]
                              [--only-add | --only-remove]
                              [<entitlement> [<entitlement> ...]]

Update entitlements in SUKAT according to entmap.conf.

positional arguments:
  <entitlement>  If present, only act on these entitlements. If none present,
                 act on all entitlements.

optional arguments:
  -h, --help     show this help message and exit
  --dry-run      Don't make any changes, only print what would be done.
  --debug        Show extra output for debug purposes.
  --only-add     Only add entitlements, don't remove any.
  --only-remove  Only remove entitlements, don't add any.
```
  
## manage-entitlements.py
 
Adds and/or removes entitlements to/from a given user or list of users and updates 
entmap.conf to reflect the changes made.

```
Usage: manage-entitlements.py [--no-entmap-update]
                              [<username> [<username> ...]]
                              [--add, -a [<entitlement> [<entitlement> ...]]]
                              [--remove, -r [<entitlement> [<entitlement> ...]]]
       manage-entitlements.py -h|--help

Positional arguments:
  <username>            The user(s) to be acted upon. If no users given, read
                        users from stdin.

Optional arguments:
  -h, --help            Show this help message and exit.
  --add, -a [<entitlement> [<entitlement> ...]]
                        Add one or more entitlements to the given user(s). Can
                        be specified multiple times.
  --remove, -r [<entitlement> [<entitlement> ...]]
                        Delete one or more entitlements from the given
                        users(s). Can be specified multiple times.
  --no-entmap-update    Don't update entmap.conf to reflect the changes made.
```
(Due to a quirk in argparse, the help message printed when the program is run with 
the ```--help``` argument is slightly misleading. The above is the actual correct 
invocation description.)

Additions to ```entmap.conf``` will be placed after the last occurrence of the given
entitlement, or at the end of the file if it doesn't exist in the file already.
Removals simply delete the relevant line if it exists. If the line contains a comment,
it will disappear as well.

## entmap.conf

This file lists all entitlement mappings for update-entitlements.py to maintain.
If an entitlement doesn't occur at all in the file, update-entitlements.py will 
not touch it.

A ```#``` character starts a comment, which runs to the end of the line. There is
no multiline comment facility.

All whitespace except newline (```\n```) is ignored. Blank lines are allowed.

Each non-comment should match the following format:
```entitlement = handler:query```

 * ```entitlement``` - An entitlement. Will be concatenated with the value of 
 ```entitlement_base``` in config.ini. The same entitlement may be specified several 
 times with different handler/query combinations.
 * ```handler``` - The facility to be used to process ```query```.
 * ```query``` - A handler-dependent description of who should be granted the 
 entitlement.
 
There are four handlers:
 * ```ldap``` - Takes an LDAP search string as a query. The query should result in a 
 list of users who will then be granted the given entitlement.
 * ```daisy``` - Accepts two kinds of queries:
   - ```students```: Will return all students who have had an active registration at DSV
  at any time during the last 10 semesters.
   - ```course:<id>```: Requires a Daisy courseSegment ID as a parameter, and will return 
  all students currently registered on that courseSegment.
 * ```user``` - Accepts a username as a query. The given user will be granted the given 
 entitlement.
 * ```none``` - Does not take a query (the :query part will be ignored if it exists). 
 Indicates that no users should have the given entitlement. Useful for removing outdated 
 entitlements.
