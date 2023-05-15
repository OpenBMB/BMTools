
import requests
import os
import json
from ..tool import Tool

def build_tool(config) -> Tool:
    tool = Tool(
        "Map Info",
        "Look up map information",
        name_for_model="Map",
        description_for_model="Plugin for look up map information",
        logo_url="https://your-app-url.com/.well-known/logo.png",
        contact_email="hello@contact.com",
        legal_info_url="hello@legal.com"
    )

    KEY = config["subscription_key"]
    BASE_URL = 'http://dev.virtualearth.net/REST/V1/'

    @tool.get("/get_distance")
    def get_distance(start:str, end:str):
        # Request URL
        url = BASE_URL + "Routes/Driving?o=json&wp.0=" + start + "&wp.1=" + end + "&key=" + KEY
        # GET request
        r = requests.get(url)
        data = json.loads(r.text)
        # Extract route information
        route = data["resourceSets"][0]["resources"][0]
        # Extract distance in miles
        distance = route["travelDistance"]
        return distance
    
    @tool.get("/get_route")
    def get_route(start:str, end:str):
        # Request URL
        url = BASE_URL + "Routes/Driving?o=json&wp.0=" + start + "&wp.1=" + end + "&key=" + KEY
        # GET request
        r = requests.get(url)
        data = json.loads(r.text)
        # Extract route information
        route = data["resourceSets"][0]["resources"][0]
        itinerary = route["routeLegs"][0]["itineraryItems"]
        # Extract route text information
        route_text = []
        for item in itinerary:
            if "instruction" in item:
                route_text.append(item["instruction"]["text"])
        return route_text
    
    @tool.get("/get_lat_lon")
    def get_lat_lon(location):
        url = BASE_URL + "Locations"
        params = {
            "query": location,
            "key": KEY
        }
        response = requests.get(url, params=params)
        json_data = response.json()
        lat_lon = json_data["resourceSets"][0]["resources"][0]["point"]["coordinates"]
        return lat_lon
    
    @tool.get("/search_nearby")
    def search_nearyby(search_term="restaurant", latitude = 0.0, longitude = 0.0, places='unknown', radius = 5000): #  radius in meters)
        url = BASE_URL + "LocalSearch"
        if places != 'unknown':
            latitude = get_lat_lon(places)[0]
            longitude = get_lat_lon(places)[1]
        # Build the request query string
        params = {
        "query": search_term,
        "userLocation": f"{latitude},{longitude}",
        "radius": radius,
        "key": KEY
        }

        # Make the request
        response = requests.get(url, params=params)

        # Parse the response
        response_data = json.loads(response.content)

        # Get the results
        results = response_data["resourceSets"][0]["resources"]
        return results
    
    return tool
