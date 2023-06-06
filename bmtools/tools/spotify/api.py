import requests
import json
from datetime import date, datetime, timedelta
import os
from ..tool import Tool

from typing import Optional, Dict, Union, List


def build_tool(config) -> Tool:
    tool = Tool(
        "Spotify",
        "Search over millions of songs & podcasts, artists, albums, playlists and more.",
        name_for_model="Spotify",
        description_for_model="Plugin for looking up songs & podcasts, artists, albums, playlists and more.",
        logo_url="https://your-app-url.com/.well-known/logo.png",
        contact_email="hello@contact.com",
        legal_info_url="hello@legal.com"
    )

    BASE_URL = "https://spotify23.p.rapidapi.com"
    KEY = config["subscription_key"]
    HEADERS = {
            "X-RapidAPI-Key": KEY,
            "X-RapidAPI-Host": "spotify23.p.rapidapi.com"
        }

    @tool.get("/spotify_search")
    def spotify_search(query: str, query_type: str) -> dict:
        """
        Search for songs & podcasts, artists, albums, playlists and more on Spotify.

        :param query: Free-form spotify search query.
        :param query_type: Type of the query, `albums`, `artists`, etc., best with `multi`.
        :return: A dictionary with the response from the API.
        """

        query_params = {
            "q": query,
            "type": query_type,
        }

        response = requests.get(BASE_URL + "/search/", headers=HEADERS, params=query_params)

        return response.json()
    
    return tool
