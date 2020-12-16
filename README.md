# findstar

Findstar is a Python CLI utility to quickly retrieve a repository that you starred on GitHub.

You can search through every user's starred repositories for keywords, kind of like grep.

## Installation

Clone the repo and install requirements.

```bash
git clone https://github.com/thbzzz/findstar.git
cd findstar
pip3 install --user -r requirements.txt
```

## Usage

```
findstar.py [-h] -u USERNAME [-f] [-a] [greps [greps ...]]

Grep over your github starred repositories!

positional arguments:
  greps                 strings to grep for

optional arguments:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        github username
  -f, --flush           refresh cache
  -a, --and             match greps using AND instead of OR
```

At first run with each username, its starred repositories are fetched from the GitHub's API, and cached in the file `cache/{username}` as zlib-compressed json data.

Next times you run `findstar.py -u {username}`, the default behavior is to get the starred repos list from the username's cache file. You can however force fetching stars from GitHub's API by adding the `-f` flag.


## Examples

```bash
findstar.py -u thbzzz kerberos
findstar.py -u thbzzz kerberos samba
findstar.py -u thbzzz -a kerberos samba
findstar.py -u thbzzz -f -a kerberos samba
findstar.py -u thbzzz -a kerberos samba thegame ldap
```

## Contributing
Pull requests are welcome.

## Authors and acknowledgment
The original idea is from [switch](https://github.com/0xswitch), with [starscrawler](https://github.com/0xswitch/starscrawler). I reimplemented the concept with a more maintanable code base.

## License
[The Unlicense](https://unlicense.org/)