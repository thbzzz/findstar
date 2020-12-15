#!/usr/bin/env python3

from os import get_terminal_size, mkdir
from os.path import isdir, isfile, join

import requests
import json

from argparse import ArgumentParser
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

        self.per_page = 50
        self.last_page = 1
        self.endpoint = f"https://api.github.com/users/{self.username}/starred?per_page={self.per_page}"

        self.cache_dir = "cache"
        self.cache_file = join(self.cache_dir, self.username + ".json")

        self.stars = []

        if not isdir(self.cache_dir):
            mkdir(self.cache_dir, mode=0o755)

        # User wants to flush the cache
        if self.flush:
            # Does the cache exist?
            if self._has_cache:
                # If yes, empty it
                self._empty_cache()
            else:
                # If no, create it
                self._init_cache()
            # Then fetch stars from GitHub and write cache
            self._fetch_stars()
            self._write_cache()
        # User just wants to use the cache
        else:
            # Does the cache exist?
            if not self._has_cache():
                # If no, create it, fetch stars from GitHub and write cache
                self._init_cache()
                self._fetch_stars()
                self._write_cache()

        # Read stars from cache
        self.stars = self._read_cache()

        # Get stars matching grep
        self.matching_stars = self._match_grep()

        # Display matched stars
        self.display()

    def display(self):
        """Output the matching repositories.
        The repo names are in bold green.
        The repo url are in blue.
        The matching lines are normal, only grepped keywords are red.
        """
        for star in self.matching_stars:
            name = Style.BRIGHT + Fore.GREEN + \
                star["name"] + Fore.RESET + Style.RESET_ALL
            html_url = Fore.BLUE + star["html_url"] + Fore.RESET

            print(f"{name} ({html_url})")

            for match in star["matches"]:
                for grep in self.greps:
                    match = match.replace(
                        grep,
                        Fore.RED + grep + Fore.RESET
                    ).strip()
                print(f"- {match}")

            print()

    def _print_loading(self, string):
        """Print loading messages on the same line.

        Args:
            string (str): String to print.
        """
        print(
            Fore.MAGENTA + string.ljust(
                get_terminal_size()[0]
            ) + Fore.RESET, end="\r", flush=True
        )

    def _match_grep(self):
        """Filter the starred repositories according to provided keywords.

        Returns:
            list: List of stars matching keywords.
        """
        matching_stars = []

        for star in self.stars:
            matches = []

            # Search for greps in the repo's description and readme
            for key in ["description", "readme"]:
                if star[key]:  # Maybe the description or readme is empty
                    for line in star[key].split("\n"):
                        if any(g in line for g in self.greps):
                            matches.append(line)

            if matches:
                star["matches"] = matches

                if self.filter_and:
                    # Match by AND (if "--and" argument is specified): select
                    # the repo if all of greps are present
                    if all(
                        [any(
                            [g in line for line in star["matches"]]
                        ) for g in self.greps]
                    ):
                        matching_stars.append(star)
                else:
                    # Match by OR: select the repo if any of greps is present,
                    matching_stars.append(star)

        return matching_stars

    def _fetch_stars(self):
        """Fetch all starred repositories of a GitHub user.
        """
        self._print_loading(f"Fetching page 1/x...")
        self.stars = self._fetch_page(1)

        if self.last_page > 1:
            for page in range(2, self.last_page+1):
                self._print_loading(
                    f"Fetching page {page} of {self.last_page}...")
                self.stars += self._fetch_page(page)

        self._print_loading("Fetch complete\n")

    def _fetch_page(self, page):
        """Fetch starred respositories contained in a page of the GitHub API.

        Args:
            page (int): Page number. The first page number is 1.

        Returns:
            list: List of fetched stars on the page.
        """
        endpoint = f"{self.endpoint}&page={page}"
        r = requests.get(endpoint)

        if page == 1:
            self.last_page = self._parse_link_header(r)

        fetched_stars = json.loads(r.text)

        stars = [{
            "id": star["id"],
            "name": star["name"],
            "owner": star["owner"]["login"],
            "full_name": star["full_name"],
            "html_url": star["html_url"],
            "default_branch": star["default_branch"],
            "description": star["description"],
            "readme": self._fetch_readme(star["full_name"], star["default_branch"])
        } for star in fetched_stars]

        return stars

    def _has_cache(self):
        """Check if a cache file exists for the provided user.

        Returns:
            bool: True/False
        """
        return isfile(self.cache_file)

    def _read_cache(self):
        """Read the cached data for the provided user.

        Returns:
            list: List of cached stars.
        """
        with open(self.cache_file) as f:
            try:
                return json.loads(f.read())
            except json.JSONDecodeError:
                return []

    def _write_cache(self):
        """Write the cached data for the provided user.
        """
        with open(self.cache_file, 'w') as f:
            f.write(json.dumps(self.stars))

    def _init_cache(self):
        """Create the cache file for the provided user.
        """
        open(self.cache_file, "w").close()

    def _empty_cache(self):
        """Empty the cache file for the provided user.
        """
        open(self.cache_file, "w").close()

    def _parse_link_header(self, response):
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

    def _fetch_readme(self, full_name, default_branch):
        """Fetch a repositories README.md's content, if found.

        Args:
            full_name (str): Full name of the repository: owner/name.
            default_branch (str): Generally "master" or "main".

        Returns:
            str: README.md content if it exists, empty otherwise.
        """
        self._print_loading(f"Fetching README.md for {full_name}...")
        url = "https://raw.githubusercontent.com/{}/{}/README.md".format(
            full_name,
            default_branch
        )

        r = requests.get(url, allow_redirects=True)
        if r.status_code == 200:
            return r.text
        else:
            return ""


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
