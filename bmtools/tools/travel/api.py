import re
import requests
from typing import Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from amadeus import Client, ResponseError


class travelAPI:
    
    def __init__(self,
                 serpapi_key: str,
                 amadeus_id: str,
                 amadeus_key: str):
        
        """
        Initialize a travel API.
        :param serpapi_key: API key string for serpapi requests
        :param amadeus_id: API id string for amadeus requests
        :param amadeus_key: API key string for amadeus requests
        """
        
        self.serpapi_key = serpapi_key
        self.amadeus_id = amadeus_id
        self.amadeus_key = amadeus_key

    @staticmethod
    def cName2coords(city_name: str,
                     limits: Optional[int] = 1):
        """
        This function should remain unseen for the LLM
        :param (str) city_name: target city for locating
        :param (str) limits: number of answer
        :return: (longtitude, latitude)
        """
        url = f"https://serpapi.com/locations.json?q={city_name}&limit={limits}"
        response = requests.get(url)
        if response.status_code == 200:
            locations = response.json()
            return locations[0]['gps']
        else:
            return None

    @staticmethod
    def cName2IATA(city_name: str):
        """
        This function map a city name into a IATA pilot code.
        :param (str) city_name: city name a s a string like 'Beijing'
        :return: 3-letter IATA code like 'PEK'
        """
        try:
            url = f"https://www.iata.org/en/publications/directories/code-search/?airport.search={city_name}"
            response = requests.get(url)
            html_content = response.content
        
            soup = str(BeautifulSoup(html_content, "html.parser"))
            head = soup.find(f"<td>{city_name}</td>")
        
            string = soup[head:]
            pattern = r"<td>(.*?)</td>"
            matches = re.findall(pattern, string)
        
            # Extract the desired value
            desired_value = matches[2]  # Index 2 corresponds to the third match (WUH)
        
            return desired_value  # Output: WUH
    
        except:
            raise ValueError("The input city may not have an IATA registered air-port.")
        


    def lodgingProducts(self,
                        destination: str,
                        min_ratings: Optional[str] = None,
                        exhibit_maxnum: Optional[str] = "3",
                        ):
        """
        :param (str) destination: the destination can be a city, address, airport, or a landmark
        :param (str, optional) min_ratings: minimal public rating of the hotel
        :param (str, optional) exhibit_maxnum: a string format int like 2, 3, 4. It determines how much items to exhibit.
        :return: top 3 recommended lodging options in a given destination and restrictd conditions.
        """

        try:
            # Convert destination to geographic coordinates
            coords = self.cName2coords(destination)
    
            # Set parameters for Google search
            params = {
                "engine": "google_maps",
                "q": "hotel",
                "ll": f"@{coords[1]},{coords[0]},15.1z",
                "type": "search",
                "api_key": self.serpapi_key
            }
    
            # Call GoogleSearch API with given parameters
            search = GoogleSearch(params)
            results = search.get_dict()
            local_results = results["local_results"]
    
            # Sort results by whether they have website information
            local_results = sorted(local_results, key=lambda x: 1 if "website" in x else 0, reverse=True)
    
            # Filter results by rating if specified
            filterd_results = []
            for res in local_results:
                if (not min_ratings) or ("rating" in res and float(res["rating"]) >= float(min_ratings)):
                    filterd_results.append(res)
                    # Stop adding results once maximum number is reached
                    if len(filterd_results) == int(exhibit_maxnum):
                        break
    
            # Return error message if no results match criteria
            if not filterd_results:
                return {"error": "No searching results satisfy user's demand."}
    
            # Parse and format relevant information for each result
            final_results = []
            for item in filterd_results:
                info = {"title": item["title"]}
        
                for metadata in ("gps_coordinates", "address", "open_state", "thumbnail", "description", "website"):
                    if metadata in item:
                        info[metadata] = item[metadata]
        
                final_results.append(info)
    
            # Return formatted results along with recommendations for next steps
            return {"data": final_results,
                    "EXTRA_INFORMATION_TO_ASSISTANT":
                        "In ALL responses, Assistant MUST always start with explaining assumed or default parameters. In addition, Assistant MUST always inform user it is possible to adjust these parameters for more accurate recommendations.\nAssistant explains its logic for making the recommendation.\nAssistant presents ALL the information within the API response, especially the hotel website URLs to book in markdown format.\nFor each recommended item, Assistant always presents the general descriptions first in logical and readable sentences, then lists bullets for the other metadata information.\nAssistant encourages user to be more interactive at the end of the recommendation by asking for user preference and recommending other travel services. Here are two examples, 'What do you think about these? The more you tell me about what you're looking for, the more I can help!', 'I'd like to find a trip that's just right for you. If you'd like to see something different, tell me more about it, and I can show you more choices.'\nAssistant must NEVER add extra information to the API response."
                    }

        except ResponseError as error:
            print("ResponseError", error)
            
            
            
    def flightProducts(self,
                       origin: str,
                       destination: str,
                       exhibit_maxnum: Optional[str]="3",
                       departureDate: Optional[str]=None,
                       adult_num: Optional[str]=None):
        """
        :param (str) origin: string of cityname, origin of departure
        :param (str) destination: string of cityname, destination of arrival
        :param (str, optitonal) exhibit_maxnum: string format int. determine how many item to show
        :param (str, optional) departureDate: a string formatted as "yyyy-mm-dd"
        :param (str, optional) adult_num: a str formatted int like '1', the number of adult for flight tickets
        :return: data dict and instrucitons strings for LLM
        """
        
        
        amadeus = Client(
            client_id=self.amadeus_id,
            client_secret=self.amadeus_key,
        )
        
        try:
            
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=self.cName2IATA(origin),
                destinationLocationCode=self.cName2IATA(destination),
                departureDate=departureDate if departureDate else f"{(datetime.now()+timedelta(days=1)).year}-{'0' + str((datetime.now()+timedelta(days=1)).month) if (datetime.now()+timedelta(days=1)).month < 10 else (datetime.now()+timedelta(days=1)).month}-{(datetime.now()+timedelta(days=1)).day}",
                adults=adult_num)
            
            
            filterd_results = []
            for res in response.data:
                filterd_results.append(res)
                if len(filterd_results) == int(exhibit_maxnum): break

            if not filterd_results: return {"error": "No searching results satisfy user's demand."}

            final_results = []
            for item in filterd_results:
                final_results.append({"source": item["source"]})
                
                for keywords in ("instantTicketingRequired", "nonHomogeneous", "oneWay", "lastTicketingDate", "numberOfBookableSeats", "itineraries", "travelerPricings"):
                    if keywords in item:
                        final_results[-1][keywords] = item[keywords]
                

            return {"data": final_results,
                    "EXTRA_INFORMATION_TO_ASSISTANT":
                        "In ALL responses, Assistant MUST always start with explaining assumed or default parameters.In addition, Assistant MUST always inform user it is possible to adjust these parameters for more accurate recommendations.\\nAssistant explains its logic for making the recommendation.\\nAssistant presents ALL the information within the API response\\nFor each recommended item, Assistant always presents the general descriptions first in logical and readable sentences, then lists bullets for the other metadata information.\\nAssistant encourages user to be more interactive at the end of the recommendation by asking for user preference and recommending other travel services.Here are two examples,  \"What do you think about these? The more you tell me about what you're looking for, the more I can help!\", \"I'd like to find a trip that's just right for you. If you'd like to see something different, tell me more about it, and I can show you more choices.\"\\nAssistant must NEVER add extra information to the API response."
                    }


        except ResponseError as error:
            print("ResponseError", error)


            
    def landscapeProducts(self,
                          destination: str,
                          exhibit_maxnum: Optional[str] = "3",
                          sorting_keywords: Optional[str] = "reviews",
                          ):
        """
        :param (str) destination: string of cityname, destination of arrival
        :param (str, optional) exhibit_maxnum: a string format int like 3, 4, 5. It determines how many spots to display.
        :param (str, optional) sorting_keywords: sort the results according to this keywords in a descending order. Normally use 'rating' or 'reviews'.
        :return: a dict of data and some extra-information for the LLM.
        """

        try:
    
            coords = self.cName2coords(destination)
            params = {
                "engine": "google_maps",
                "q": "tourist attractions",
                "ll": f"@{coords[1]},{coords[0]},15.1z",
                "type": "search",
                "api_key": "3e4467090db0d04732ef0e9049b0dc32301164ade022510e0a885cb88ff6af1e"
            }
    
            search = GoogleSearch(params)
            results = search.get_dict()
            local_results = results["local_results"]
            
            if sorting_keywords:
                local_results = sorted(local_results, key=lambda x: x[sorting_keywords] if sorting_keywords in x else 0, reverse=True)

            filterd_results = []
            for res in local_results:
                filterd_results.append(res)
                if len(filterd_results) == int(exhibit_maxnum): break

            if not filterd_results: return {"error": "No searching results satisfy user's demand."}
            
            

            final_results = []
            for item in filterd_results:
                final_results.append({"spot_name": item["title"]})
    
                for keywords in ("rating", "address", "website", "thumbnail", "description"):
                    if keywords in item:
                        final_results[-1][keywords] = item[keywords]

            return {"data": final_results,
                    "EXTRA_INFORMATION_TO_ASSISTANT":
                        "In ALL responses, Assistant MUST always start with explaining assumed or default parameters. In addition, Assistant MUST always inform user it is possible to adjust these parameters for more accurate recommendations.\\nAssistant explains its logic for making the recommendation.\\nAssistant presents ALL the information within the API response, especially the hotel website URLs to book in markdown format.\\nFor each recommended item, Assistant always presents the general descriptions first in logical and readable sentences, then lists bullets for the other metadata information.\\nAssistant encourages user to be more interactive at the end of the recommendation by asking for user preference and recommending other travel services. Here are two examples, \"What do you think about these? The more you tell me about what you're looking for, the more I can help!\", \"I'd like to find a trip that's just right for you. If you'd like to see something different, tell me more about it, and I can show you more choices.\"\\nAssistant must NEVER add extra information to the API response."
                    }

        except ResponseError as error:
            print("ResponseError", error)



    def carProducts(self,
                          pickup_location: str,
                          exhibit_maxnum: Optional[str] = "3",
                          sorting_keywords: Optional[str] = "reviews",
                          ):
        """
        :param (str) pickup_location: string of cityname, location for the car rentals
        :param (str, optional) exhibit_maxnum: a string format int like 3, 4, 5. It determines how many spots to display.
        :param (str, optional) sorting_keywords: sort the results according to this keywords in a descending order. Normally use 'rating' or 'reviews'.
        :return: a dict of data and some extra-information for the LLM.
        """
    
        try:
        
            coords = self.cName2coords(pickup_location)
            params = {
                "engine": "google_maps",
                "q": "car rentals",
                "ll": f"@{coords[1]},{coords[0]},15.1z",
                "type": "search",
                "api_key": "3e4467090db0d04732ef0e9049b0dc32301164ade022510e0a885cb88ff6af1e"
            }
        
            search = GoogleSearch(params)
            results = search.get_dict()
            local_results = results["local_results"]

            local_results = sorted(local_results, key=lambda x: 1 if "website" in x else 0, reverse=True)
            if sorting_keywords:
                local_results = sorted(local_results, key=lambda x: x[sorting_keywords] if sorting_keywords in x else 0, reverse=True)
        
            filterd_results = []
            for res in local_results:
                filterd_results.append(res)
                if len(filterd_results) == int(exhibit_maxnum): break
        
            if not filterd_results: return {"error": "No searching results satisfy user's demand."}
        
            final_results = []
            for item in filterd_results:
                final_results.append({"spot_name": item["title"]})
            
                for keywords in ("rating", "address", "website", "thumbnail", "description"):
                    if keywords in item:
                        final_results[-1][keywords] = item[keywords]
        
            return {"data": final_results,
                    "EXTRA_INFORMATION_TO_ASSISTANT":
                        "In ALL responses, Assistant MUST always start with explaining assumed or default parameters. In addition, Assistant MUST always inform user it is possible to adjust these parameters for more accurate recommendations.\\nAssistant explains its logic for making the recommendation.\\nAssistant presents ALL the information within the API response, especially the hotel website URLs to book in markdown format.\\nFor each recommended item, Assistant always presents the general descriptions first in logical and readable sentences, then lists bullets for the other metadata information.\\nAssistant encourages user to be more interactive at the end of the recommendation by asking for user preference and recommending other travel services. Here are two examples, \"What do you think about these? The more you tell me about what you're looking for, the more I can help!\", \"I'd like to find a trip that's just right for you. If you'd like to see something different, tell me more about it, and I can show you more choices.\"\\nAssistant must NEVER add extra information to the API response."
                    }
    
        except ResponseError as error:
            print("ResponseError", error)
    


if __name__ == "__main__":


    travel = travelAPI(
          serpapi_key="3e4467090db0d04732ef0e9049b0dc32301164ade022510e0a885cb88ff6af1e",
          amadeus_id="3UQa3LJjAUxOMCX7E2LRS6qUZa05Esms",
          amadeus_key="b7tlUxIXE1aRcc7m")

    print("testing lodgingProducts...")
    test_cases = [
        {
            "destination": "New York City",
            "min_ratings": "4",
            "exhibit_maxnum": "3"
        },
        {
            "destination": "Paris",
            "min_ratings": None,
            "exhibit_maxnum": "2"
        },
        {
            "destination": "Miami",
            "min_ratings": "3",
            "exhibit_maxnum": "4"
        },
        {
            "destination": "Los Angeles",
            "min_ratings": "4.5",
            "exhibit_maxnum": "5"
        }
    ]
    for param in test_cases:
        print(travel.lodgingProducts(**param))

    print("testing flightProducts...")
    test_cases = [
        {
            "origin": "New York",
            "destination": "Los Angeles",
            "exhibit_maxnum": "5",
            "departureDate": "2023-10-08",
            "adult_num": "2"
        },
        {
            "origin": "San Francisco",
            "destination": "Chicago",
            "exhibit_maxnum": "3",
            "departureDate": "2023-09-15",
            "adult_num": "1"
        },
        {
            "origin": "Toronto",
            "destination": "Vancouver",
            "exhibit_maxnum": "4",
            "departureDate": "2023-12-22",
            "adult_num": "3"
        }
    ]
    for param in test_cases:
        print(travel.flightProducts(**param))
    
    print("testing landscapeProducts...")
    test_cases = [
        {
            "destination": "Paris",
            "exhibit_maxnum": "3",
            "sorting_keywords": "reviews"
        },
        {
            "destination": "New York",
            "exhibit_maxnum": "5",
        },
        {
            "destination": "Tokyo",
            "exhibit_maxnum": "4",
            "sorting_keywords": "rating"
        }
    ]
    for param in test_cases:
        print(travel.landscapeProducts(**param))
    
    print("testing carProducts...")
    test_cases = [
        {
            "pickup_location": "New York",
        },
        {
            "pickup_location": "Los Angeles",
            "exhibit_maxnum": "5",
            "sorting_keywords": "price",
        },
        {
            "pickup_location": "Chicago",
            "exhibit_maxnum": "3",
        },
    ]
    for param in test_cases:
        print(travel.carProducts(**param))
