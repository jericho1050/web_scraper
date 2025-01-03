from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class LinkedInProfile:
    """Structure for LinkedIn profile data"""
    name: str
    position: str
    company: str
    location: str
    connections: int
    education: str

    @classmethod
    def from_api_response(cls, profile: Dict[str, Any]) -> 'LinkedInProfile':
        """Create profile from API response"""
        return cls(
            name=f"{profile.get('firstName','')} {profile.get('lastName','')}".strip(),
            position=cls._get_position(profile),
            company=cls._get_company(profile),
            location=profile.get('geoLocationName', ''),
            connections=profile.get('connectionsCount', 0),
            education=cls._get_education(profile)
        )

    @staticmethod
    def _get_position(profile: Dict[str, Any]) -> str:
        """Extract position from profile data"""
        if "positions" in profile and profile["positions"]:
            return profile["positions"][0].get("title", "")
        return profile.get("occupation", "")

    @staticmethod
    def _get_company(profile: Dict[str, Any]) -> str:
        """Extract company from profile data"""
        if "positions" in profile and profile["positions"]:
            return profile["positions"][0].get("companyName", "")
        return ""

    @staticmethod
    def _get_education(profile: Dict[str, Any]) -> str:
        """Extract education from profile data"""
        if "educations" in profile and profile["educations"]:
            return profile["educations"][0].get("schoolName", "")
        return ""

@dataclass
class GitHubProfile:
    """Structure for GitHub profile data"""
    username: str
    full_name: Optional[str]
    bio: Optional[str]
    public_repos: int
    followers: int