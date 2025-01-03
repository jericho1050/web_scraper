import csv
import logging
import os
import json
import requests
import pprint
from typing import Optional
from apify_client import ApifyClient
from apify_client._errors import ApifyApiError
from dotenv import load_dotenv
from helper import get_actor_config
from models import LinkedInProfile, GitHubProfile

load_dotenv()


class LinkedinWebScraper:
    """
    Steps for initializing and running the Apify scraper:
      1. Load environment variables (token, etc.).
      2. Read and parse scraper config (actor name, actor input).
      3. Create an ApifyClient instance using the token.
      4. Run the desired actor with input config.
      5. Retrieve and process the Dataset results.
    """

    def __init__(self, config_path="linkedin_config.json", page_size=100):
        try:
            config = get_actor_config(config_path)
        except FileNotFoundError:
            logging.error(f"Configuration file {config_path} not found.")
            config = None
        except Exception as e:
            logging.error(f"Error reading configuration file {config_path}: {str(e)}")
            config = None
        self.apify_client = ApifyClient(os.getenv("MY_API_TOKEN"))
        self.page_size = page_size

        try:
            self.actor_call = self.apify_client.actor(config["actor_name"]).call(
                run_input=config["actor_input"]
            )
        except ApifyApiError as e:
            print(f"Error while running actor: {e}")
            if "rate-limit" in str(e).lower() or "429" in str(e):
                print("Detected possible rate limit or scraping block.")
            # Address invalid or inaccessible profile URLs in the data or logs
            self.actor_call = None

        if self.actor_call:
            self.dataset_client = self.apify_client.dataset(
                self.actor_call["defaultDatasetId"]
            )

        else:
            self.dataset_client = None

    def get_profiles_page(self, offset=0, limit=100):
        """Get a single page of profiles"""
        try:
            return self.dataset_client.list_items(offset=offset, limit=limit).items
        except ApifyApiError as e:
            logging.error(f"Failed to fetch page: {str(e)}")
            return []

    def get_all_profiles(self):
        """Fetch all profiles with pagination"""
        all_profiles = []
        offset = 0

        while True:
            profiles_page = self.get_profiles_page(offset=offset, limit=self.page_size)

            if not profiles_page:
                break

            all_profiles.extend(profiles_page)
            offset += self.page_size

            logging.info(
                f"Fetched {len(profiles_page)} profiles. Total: {len(all_profiles)}"
            )

        return all_profiles

    def get_formatted_results(self):
        """Return formatted scraped profiles in specified format"""
        profiles = self.get_all_profiles()
        formatted_profiles = []

        for raw_profile in profiles:
            # Convert raw API data to LinkedInProfile object
            profile = LinkedInProfile.from_api_response(raw_profile)
            # Now we can use __dict__ since it's a dataclass
            formatted_profiles.append(profile.__dict__)

        return json.dumps(formatted_profiles, indent=2)

    def save_results(self, filename: str = "linkedin_profiles.csv") -> None:
        """
        Save LinkedIn profiles to CSV file.

        Args:
            filename: Output CSV filename

        Example:
            >>> scraper = LinkedinWebScraper()
            >>> scraper.save_results("profiles.csv")
        """
        try:
            all_profiles = self.get_all_profiles()
            profiles = [LinkedInProfile.from_api_response(p) for p in all_profiles]

            with open(filename, "w", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "name",
                        "position",
                        "company",
                        "location",
                        "connections",
                        "education",
                    ],
                )
                writer.writeheader()
                for profile in profiles:
                    writer.writerow(profile.__dict__)

            logging.info(f"Successfully saved {len(profiles)} profiles to {filename}")

        except Exception as e:
            logging.error(f"Failed to save profiles: {str(e)}")
            raise


class GitHubWebScraper:
    """
    A class to scrape GitHub user profiles using the GitHub API.

    Attributes:
        BASE_URL (str): The base URL for the GitHub API.
        token (str): The GitHub API token for authentication.
        headers (dict): The headers for the API requests.
        github_profiles (list): A list to store fetched GitHub profiles.
        usernames (list[str]): A list of GitHub usernames to fetch profiles for.
        page_size (int): The number of profiles to fetch per page.

    Methods:
        __init__(usernames: list[str], page_size: int = 30):
            Initializes the GitHubWebScraper with the given usernames and page size.

        fetch_profiles() -> None:
            Fetches GitHub profiles for the stored usernames and stores them in github_profiles.

        get_formatted_results() -> str:
            Returns the fetched GitHub profiles in a formatted JSON string.

        save_results(filename: str = "github_profile.csv") -> None:
            Saves the fetched GitHub profiles to a CSV file with the given filename.
    """

    BASE_URL = "https://api.github.com/users"

    def __init__(self, usernames: list[str], page_size: int = 30):
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}",
        }
        self.github_profiles = []
        self.usernames = usernames
        self.page_size = page_size

        # Fetch profiles during initialization
        logging.info(f"Initializing GitHub scraper for {len(usernames)} users")
        self.fetch_profiles()

    def fetch_profiles(self) -> None:
        """Fetch GitHub profiles for stored usernames"""
        for username in self.usernames:
            try:
                response = requests.get(
                    f"{self.BASE_URL}/{username}", headers=self.headers
                )
                response.raise_for_status()
                data = response.json()

                self.github_profiles.append(
                    GitHubProfile(
                        username=data["login"],
                        full_name=data.get("name"),
                        bio=data.get("bio"),
                        public_repos=data["public_repos"],
                        followers=data["followers"],
                    )
                )
                logging.info(f"Fetched profile for {username}")

            except requests.exceptions.RequestException as e:
                if response.status_code == 404:
                    logging.error(f"User {username} not found")
                elif response.status_code == 403:
                    logging.error("API rate limit exceeded")
                else:
                    logging.error(f"Error: {str(e)}")

    def get_formatted_results(self):
        """Return formatted GitHub profiles"""
        formatted_profiles = []
        for profile in self.github_profiles:
            formatted_profiles.append(
                {
                    "username": profile.username,
                    "full_name": profile.full_name,
                    "bio": profile.bio,
                    "public_repos": profile.public_repos,
                    "followers": profile.followers,
                }
            )
        return json.dumps(formatted_profiles, indent=2)

    def save_results(self, filename: str = "github_profile.csv"):
        """
        Save Github profiles to CSV file.

        Args:
            filename: Output CSV filename

        Example:
            >>> scraper = GitHubinWebScraper()
            >>> scraper.save_results("profiles.csv")
        """
        with open(filename, "w") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "Username",
                    "Fullname",
                    "Bio",
                    "Number of public repositories",
                    "Number of followers",
                ],
            )
            writer.writeheader()
            # Convert dataclass objects to dictionaries with mapped field names
            rows = [
                {
                    "Username": profile.username,
                    "Fullname": profile.full_name,
                    "Bio": profile.bio,
                    "Number of public repositories": profile.public_repos,
                    "Number of followers": profile.followers,
                }
                for profile in self.github_profiles
            ]

            writer.writerows(rows)


# Instiate LinkedinWebScraper to start scraping!
linkedin_scraper = LinkedinWebScraper()
# invoke save_results method to save in a CSV file
linkedin_scraper.save_results()
print("Linkedin Output:")
print(linkedin_scraper.get_formatted_results())

# Instiate GitHubWebScraper to start scraping!
github_scraper = GitHubWebScraper(
    usernames=["wincent", "jericho1050", "brianyu2", "dmalan", "torvalds"]
)
# invoke save_results method to save in a CSV file
github_scraper.save_results()
print("Github Output:")
print(github_scraper.get_formatted_results())
