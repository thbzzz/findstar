#!/usr/bin/env python3

import json
import os
import os.path
import re

import requests
from colorama import Fore


class Findstar:
    def __init__(self, username, per_page=50, flush_cache=False):
        self.username = username
        self.per_page = per_page
        self.last_page = 1
        self.endpoint = f"https://api.github.com/users/{self.username}/starred?per_page={self.per_page}"

        self.cache_dir = "cache"
        self.cache_file = os.path.join(self.cache_dir, self.username + ".json")
        self.flush_cache = flush_cache

        self.stars = []

        if not os.path.isdir(self.cache_dir):
            os.mkdir(self.cache_dir, mode=0o755)

        # User wants to flush the cache
        if self.flush_cache:
            # Does the cache exist?
            if self._has_cache:
                # If yes, empty it
                self._empty_cache()
            else:
                # If no, create it, fetch stars from GitHub and write cache
                self._init_cache()
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

    def _fetch_stars(self):
        self.stars = self._fetch_page(1)
        if self.last_page > 1:
            for page in range(2, self.last_page+1):
                self.stars += self._fetch_page(page)

    def _fetch_page(self, page):
        endpoint = f"{self.endpoint}&page={page}"
        r = requests.get(endpoint)

        if page == 1:
            self.last_page = self._parse_last_page(r)

        fetched_stars = json.loads(r.text)

        stars = [{
            "id": star["id"],
            "name": star["name"],
            "owner": star["owner"]["login"],
            "full_name": star["full_name"],
            "html_url": star["html_url"],
            "description": star["description"],
            "readme": self._fetch_readme(star["html_url"])
        } for star in fetched_stars]

        return stars

    def _has_cache(self):
        return os.path.isfile(self.cache_file)

    def _read_cache(self):
        with open(self.cache_file) as f:
            try:
                return json.loads(f.read())
            except json.JSONDecodeError:
                return ""

    def _write_cache(self):
        with open(self.cache_file, 'w') as f:
            f.write(json.dumps(self.stars))

    def _init_cache(self):
        open(self.cache_file, "w").close()

    def _empty_cache(self):
        open(self.cache_file, "w").close()

    def _parse_last_page(self, response):
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

    def _fetch_readme(self, html_url):
        # r = requests.get()
        return ""


if __name__ == "__main__":
    findstar = Findstar("thbzzz", per_page=20)
    # findstar.stars contains every star
