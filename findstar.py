#!/usr/bin/env python3

import json
from argparse import ArgumentParser
from os import get_terminal_size, mkdir, remove
from os.path import dirname, isdir, isfile, join, realpath
from zlib import compress, decompress

import requests
from colorama import Fore, Style


class Findstar:
    """Class for finding GitHub starred repositories by searching for strings
    in their description and README.md.
    """

    def __init__(self, username, greps, filter_and=False, flush=False):
        """Perform cache operations to access stored data, or communicate with
        the GitHub API if flush in set to True.
        Then, display the filtered repositories.

        Args:
            username (str): GitHub username.
            greps (list): List of strings to grep for.
            filter_and (bool, optional): Match repositories according to
                greps using AND instead of OR. Defaults to False.
            flush (bool, optional): Refresh cache data before searching for
                greps. Defaults to False.
        """
        self.username = username
        self.greps = greps
        self.filter_and = filter_and
        self.flush = flush

        self.cache = Cache(self.username)

        self.per_page = 50
        self.last_page = 1
        self.endpoint = "https://api.github.com/users/{}/starred?per_page={}".format(
            self.username,
            self.per_page
        )

        self.stars = []
        self.matching_stars = []

        # User wants to flush the cache
        if self.flush:
            # Does the cache exist?
            if self.cache.file_exists():
                # If yes, empty it
                self.cache.empty()
            else:
                # If no, create it
                self.cache.create_file()
            # Then fetch stars from GitHub and write cache
            self.fetch_stars()
            self.cache.write(self.stars)
        # User just wants to use the cache
        else:
            # Does the cache exist?
            if not self.cache.file_exists():
                # If no, fetch stars, create it, from GitHub and write cache
                self.fetch_stars()
                self.cache.create_file()
                self.cache.write(self.stars)
            else:
                # If yes, read stars from cache
                self.stars = self.cache.read()

        # Get stars matching grep
        self.matching_stars = self.filter_stars()

        # Display matched stars
        for star in self.matching_stars:
            star.display(self.greps)

    def loading(self, string):
        """Print loading messages on the same line.

        Args:
            string (str): String to print.
        """
        print(
            Fore.MAGENTA + string.ljust(
                get_terminal_size()[0]
            ) + Fore.RESET, end="\r", flush=True
        )

    def filter_stars(self):
        """Filter the starred repositories according to provided keywords.

        Returns:
            list: List of stars matching keywords.
        """
        matching_stars = []

        for star in self.stars:
            matches = []

            # Search for greps in the repo's description and readme
            for key in ["description", "readme"]:
                try:
                    for line in getattr(star, key).split("\n"):
                        if any(g in line for g in self.greps):
                            matches.append(line)
                except AttributeError:
                    pass

            if matches:
                star.matches = matches

                if self.filter_and:
                    # Match by AND (if "--and" argument is specified): select
                    # the repo if all of greps are present
                    if all(
                        [any(
                            [g in line for line in star.matches]
                        ) for g in self.greps]
                    ):
                        matching_stars.append(star)
                else:
                    # Match by OR: select the repo if any of greps is present,
                    matching_stars.append(star)

        return matching_stars

    def fetch_stars(self):
        """Fetch all starred repositories of a GitHub user.
        """
        self.loading(f"Fetching page 1...")
        self.stars = self.fetch_page(1)

        if self.last_page > 1:
            for page in range(2, self.last_page+1):
                self.loading(
                    f"Fetching page {page} of {self.last_page}...")
                self.stars += self.fetch_page(page)

    def fetch_page(self, page):
        """Fetch starred respositories contained in a page of the GitHub API.

        Args:
            page (int): Page number. The first page number is 1.

        Returns:
            list: List of fetched stars on the page.
        """
        endpoint = f"{self.endpoint}&page={page}"
        r = requests.get(endpoint)

        if page == 1:
            self.last_page = self.parse_link_header(r)

        fetched_stars = json.loads(r.text)

        page_stars = [
            Star(
                id=star["id"],
                name=star["name"],
                owner=star["owner"]["login"],
                full_name=star["full_name"],
                html_url=star["html_url"],
                default_branch=star["default_branch"],
                description=star["description"],
                readme=self.fetch_readme(
                    star["full_name"], star["default_branch"]
                )
            ) for star in fetched_stars
        ]

        self.loading("Fetch complete")

        return page_stars

    def fetch_readme(self, full_name, default_branch):
        """Fetch a repositories README.md's content, if found.

        Args:
            full_name (str): Full name of the repository: owner/name.
            default_branch (str): Generally "master" or "main".

        Returns:
            str: README.md content if it exists, empty otherwise.
        """
        self.loading(f"Fetching README.md for {full_name}...")
        url = "https://raw.githubusercontent.com/{}/{}/README.md".format(
            full_name,
            default_branch
        )

        r = requests.get(url, allow_redirects=True)
        if r.status_code == 200:
            return r.text
        else:
            return ""

    def parse_link_header(self, response):
        """Parse the "link" HTTP header sent by GitHub API to determine the
        last page containing user's starred repositories.

        Args:
            response (requests.Response): HTTP response from GitHub API.

        Returns:
            int: Last page number.
        """
        if "link" in response.headers.keys():
            link = requests.utils.parse_header_links(
                response.headers["link"]
            )
            for rel in link:
                if rel["rel"] == "last":
                    last_page = int(rel["url"].split("&page=")[1])
        else:
            last_page = 1

        return last_page


class Star:
    """Class representing a starred GitHub repository.
    """

    def __init__(self, *args, **kwargs):
        self.id = kwargs["id"]
        self.name = kwargs["name"]
        self.owner = kwargs["owner"]
        self.full_name = kwargs["full_name"]
        self.html_url = kwargs["html_url"]
        self.default_branch = kwargs["default_branch"]
        self.description = kwargs["description"]
        self.readme = kwargs["readme"]
        self.matches = []  # Set by Findstar.filter_stars method

    def display(self, greps):
        """Output the matching repositories.
        The repo names are in bold green.
        The repo url are in blue.
        The matching lines are normal, only grepped keywords are red.
        """
        name = Style.BRIGHT + Fore.GREEN + \
            self.name + Fore.RESET + Style.RESET_ALL
        html_url = Fore.BLUE + self.html_url + Fore.RESET

        print(f"{name} ({html_url})")

        for match in self.matches:
            for grep in greps:
                match = match.replace(
                    grep, Fore.RED + grep + Fore.RESET
                ).strip()
            print(f"- {match}")

        print()


class Cache:
    """Class for performing cache operations on Star objects.
    """

    def __init__(self, username):
        self.username = username
        self.dir = join(dirname(realpath(__file__)), "cache")
        self.file = join(self.dir, self.username)

        # On first run, create the cache directory
        if not self.dir_exists():
            self.create_dir()

    def dir_exists(self):
        """Check if the cache dir exists.

        Returns:
            bool: True/False.
        """
        return isdir(self.dir)

    def file_exists(self):
        """Check if a cache file exists for the provided user.

        Returns:
            bool: True/False.
        """
        return isfile(self.file)

    def create_dir(self):
        """Create the cache dir.
        """
        mkdir(self.dir, mode=0o755)

    def create_file(self):
        """Create the cache file for the provided user.
        """
        open(self.file, "w").close()

    def read(self):
        """Read the cached data for the provided user.

        Returns:
            list: List of cached stars.
        """
        with open(self.file, "rb") as f:
            try:
                stars = json.loads(decompress(f.read()).decode())
                return [Star(**star) for star in stars]
            except json.JSONDecodeError:
                return []

    def write(self, stars):
        """Write the fetched stars for the provided user.
        """
        stars_json = json.dumps([vars(star) for star in stars])
        stars_compressed = compress(stars_json.encode())
        with open(self.file, 'wb') as f:
            f.write(stars_compressed)

    def empty(self):
        """Empty the cache file for the provided user.
        """
        open(self.file, "w").close()

    def delete(self):
        """Delete the cache file for the provided user.
        """
        remove(self.file)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Grep over your github starred repositories!"
    )
    parser.add_argument(
        "-u",
        "--username",
        help="github username",
        required=True
    )
    parser.add_argument(
        "-f",
        "--flush",
        action="store_true",
        help="refresh cache"
    )
    parser.add_argument(
        "-a",
        "--and",
        action="store_true",
        dest="filter_and",
        help="match greps using AND instead of OR"
    )
    parser.add_argument(
        "greps",
        nargs="*",
        help="strings to grep for",
    )

    findstar = Findstar(**vars(parser.parse_args()))
