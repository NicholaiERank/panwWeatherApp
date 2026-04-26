import requests
import sys

def get_weather(city, api_key):
    # Construct the URL for the OpenWeather API
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Pull out the interesting bits
        city_name = data['name']
        temp = data['main']['temp']
        description = data['weather'][0]['description']
        
        print(f"\n--- Current Weather ---")
        print(f"City: {city_name}")
        print(f"Temp: {temp}°C")
        print(f"Sky:  {description.capitalize()}")
        print(f"-----------------------\n")
        
    except Exception as e:
        print(f"Error: Could not get weather data. Check your key/city name. ({e})")

if __name__ == "__main__":
    # PASTE YOUR API KEY HERE FOR THE INITIAL TEST
    MY_KEY = "84fe7e73e1349d20c2c9b68bf328b9dd"
    
    # Check Melbourne by default, or whatever city you type after the command
    target = sys.argv[1] if len(sys.argv) > 1 else "Melbourne"
    
    get_weather(target, MY_KEY)
