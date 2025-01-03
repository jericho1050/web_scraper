import pytest
import requests
import json
from unittest.mock import MagicMock, patch
import httpx
from apify_client._errors import ApifyApiError
from main import LinkedinWebScraper, GitHubWebScraper


# LINKEDIN TESTING STARTS HERE
@patch("main.get_actor_config")
@patch("main.ApifyClient")
def test_error_handling(mock_client, mock_get_actor_config):
    # Mock a minimal config to avoid FileNotFoundError
    mock_get_actor_config.return_value = {
        "actor_name": "curious_coder/linkedin-profile-scraper",
        "actor_input": {},
    }
    # Simulate a 429 rate limit error
    mock_response = httpx.Response(
        status_code=429,
        content=b"Too Many Requests",
        request=httpx.Request("GET", "https://api.apify.com"),
    )
    mock_client.return_value.actor.return_value.call.side_effect = ApifyApiError(
        mock_response, 1
    )

    scraper = LinkedinWebScraper(config_path="invalid_config.json")
    assert scraper.actor_call is None


@patch("main.ApifyClient")
def test_actor_call_success(mock_client):
    # Setup mock
    mock_actor = MagicMock()
    mock_actor.call.return_value = {"defaultDatasetId": "test-dataset-id"}
    mock_client_inst = MagicMock()
    mock_client_inst.actor.return_value = mock_actor
    mock_dataset = MagicMock()
    mock_dataset.list_items.return_value.items = [{"company": "TestCorp"}]
    mock_client_inst.dataset.return_value = mock_dataset
    mock_client.return_value = mock_client_inst

    # Test
    scraper = LinkedinWebScraper()
    assert scraper.actor_call is not None
    assert scraper.dataset_client is not None

    # Test get_profiles_page
    profiles = scraper.get_profiles_page()
    assert len(profiles) == 1
    assert profiles[0]["company"] == "TestCorp"


@patch("main.get_actor_config")
@patch("main.ApifyClient")
def test_actor_call_rate_limit_error(mock_client, mock_get_actor_config):
    # Same approach to avoid FileNotFoundError
    mock_get_actor_config.return_value = {
        "actor_name": "curious_coder/linkedin-profile-scraper",
        "actor_input": {},
    }
    # Simulate 429 error again
    mock_response = httpx.Response(
        status_code=429,
        content=b"Too Many Requests",
        request=httpx.Request("GET", "https://api.apify.com"),
    )
    mock_client.return_value.actor.return_value.call.side_effect = ApifyApiError(
        mock_response, 1
    )

    scraper = LinkedinWebScraper(config_path="invalid_config.json")
    assert scraper.actor_call is None


@patch("main.ApifyClient")
def test_empty_dataset(mock_client):
    # Setup mock
    mock_actor = MagicMock()
    mock_actor.call.return_value = {"defaultDatasetId": "test-empty-dataset"}
    mock_client_inst = MagicMock()
    mock_client_inst.actor.return_value = mock_actor
    mock_dataset = MagicMock()
    mock_dataset.list_items.return_value.items = []
    mock_client_inst.dataset.return_value = mock_dataset
    mock_client.return_value = mock_client_inst

    # Test
    scraper = LinkedinWebScraper()
    assert scraper.actor_call is not None
    assert scraper.dataset_client is not None

    # Test empty results
    profiles = scraper.get_profiles_page()
    assert len(profiles) == 0


@patch("main.ApifyClient")
def test_get_formatted_results(mock_client):
    mock_actor = MagicMock()
    mock_actor.call.return_value = {"defaultDatasetId": "test-format-dataset"}
    mock_client_inst = MagicMock()
    mock_client_inst.actor.return_value = mock_actor
    mock_dataset = MagicMock()
    mock_dataset.list_items.return_value.items = [
        {"name": "Profile1"},
        {"name": "Profile2"},
    ]
    mock_client_inst.dataset.return_value = mock_dataset
    mock_client.return_value = mock_client_inst

    scraper = LinkedinWebScraper()
    formatted = scraper.get_formatted_results()
    assert '"name": "Profile1"' in formatted
    assert '"name": "Profile2"' in formatted


# LINKEDIN TESTING ENDS HERE

##################################################################################################

# GITHUB TESTING HERE


@pytest.fixture
def mock_github_response():
    return {
        "login": "testuser",
        "name": "Test User",
        "bio": "Test Bio",
        "public_repos": 10,
        "followers": 20,
    }


@pytest.fixture
def mock_failed_response():
    mock_response = MagicMock()
    mock_response.status_code = 404
    return mock_response


@patch("requests.get")
def test_github_scraper_init_success(mock_get, mock_github_response):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = mock_github_response
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    # Test initialization and fetch
    scraper = GitHubWebScraper(["testuser"])
    assert len(scraper.github_profiles) == 1
    assert scraper.github_profiles[0].username == "testuser"
    assert scraper.page_size == 30


@patch("requests.get")
def test_github_scraper_user_not_found(mock_get, mock_failed_response):
    mock_get.return_value = mock_failed_response

    # Should log error but not raise exception
    scraper = GitHubWebScraper(["nonexistent"])
    assert len(scraper.github_profiles) == 0


@patch("requests.get")
def test_github_scraper_format_results(mock_get, mock_github_response):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = mock_github_response
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    scraper = GitHubWebScraper(["testuser"])
    results = json.loads(scraper.get_formatted_results())

    assert len(results) == 1
    assert results[0]["username"] == "testuser"
    assert results[0]["public_repos"] == 10


@patch("requests.get")
def test_github_scraper_save_results(mock_get, mock_github_response, tmp_path):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = mock_github_response
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    scraper = GitHubWebScraper(["testuser"])
    test_file = tmp_path / "test_profiles.csv"
    scraper.save_results(str(test_file))

    # Verify CSV contents
    assert test_file.exists()
    content = test_file.read_text()
    assert (
        "Username,Fullname,Bio,Number of public repositories,Number of followers"
        in content
    )
    assert "testuser,Test User,Test Bio,10,20" in content.replace("\n", "")


# GITHUB TESTING ENDS HERE
