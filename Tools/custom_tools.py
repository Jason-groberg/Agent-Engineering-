from pydantic import BaseModel, ConfigDict
import requests
import random


def get_weather(latitude: float, longitude: float):
    response = requests.get (
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,wind_speed_10m,weather_code",
            "temperature_unit": "fahrenheit"
        }
    )
    data = response.json()
    return data["current"]

def mod_exp(x: int, y: int, N: int) -> int:
    if y == 0 :
        return 1
    z = mod_exp(x,y//2, N)

    if y & 1 == 0:
        return (z*z) % N
    else:
        return (x * (z*z)) % N

def fermat(N: int) -> bool:
    """
    Returns True if N is prime
    """
    if( N < 2):
        return False
    if N == 2:
        return True
    if N & 1 == 0:
        return False
    for i in range(20):
        a = random.randint(2, N-1)
        if mod_exp(a, N-1, N) == 1:
            continue
        else:
            return False
    return True

def generate_large_prime(n_bits: int) -> int:
    """Generate a random prime number with the specified bit length"""
    while True:
        bits = random.getrandbits(n_bits)
        if bits & 1 == 1:
            if fermat(bits):
                return bits

def get_url_contents(url: str) -> str:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text

def get_conference_speakers() -> str:
        return get_url_contents("https://www.churchofjesuschrist.org/"
        "study/general-conference/speakers?lang=eng")


# Pydantic Schemas
class GetGeneratePrimeParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    n_bits: int

class GetFermatParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    N : int

class GetConferenceSpeakersParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

class GetUrlContentsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str

class GetWeatherParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    latitude: float
    longitude: float

class GetTodoListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pass

class ModExpParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    x: int
    y: int
    N: int

# Generate Schemas with Pydantic
todo_list_schema = GetTodoListParams.model_json_schema()
weather_schema = GetWeatherParams.model_json_schema()
mod_exp_schema = ModExpParams.model_json_schema()

tools = [
    {
        "type": "function",
        "name": "get_url_contents",
        "description": (
            "Fetch a URL and return its raw response text. "
            "HTML pages include markup. Does not execute JavaScript."
        ),
        "parameters": GetUrlContentsParams.model_json_schema(),
        "strict": True,
    },
    {
    "type": "function",
    "name": "get_conference_speakers",
    "description": (
        "Start here when finding a General Conference quote from a "
        "speaker and a paraphrase. Fetch this index, locate the speaker's "
        "link, then use get_url_contents to read the speaker's page and "
        "candidate talks. Only reproduce wording verified in retrieved "
        "talk text. Include the speaker, talk title, date, and source URL. "
        "If no passage is verified, report that no match was found."
    ),
    "parameters": GetConferenceSpeakersParams.model_json_schema(),
    "strict": True,
    },
    {
        "type": "function",
        "name": "get_todo_list",
        "description": "Get the list of todos",
        "parameters": todo_list_schema,
        "strict": True
    },
    {
        "type": "function",
        "name": "get_weather",
        "description": "Get current weather (temperature in °F, wind in mph) for a latitude/longitude",
        "parameters": weather_schema,
        "strict": True,
    },
    {
        "type": "function",
        "name": "mod_exp",
        "description": "Calculate x^y % N for integers x, exponent y mod N.",
        "parameters": mod_exp_schema,
        "strict": True,
    },
{
    "type": "function",
    "name": "fermat",
    "description": (
        "Test integer N using 20 randomized rounds of Fermat's "
        "primality test. False means composite or less than 2. "
        "True means probable prime, not guaranteed prime."
    ),
    "parameters": GetFermatParams.model_json_schema(),
    "strict": True,
},
{
    "type": "function",
    "name": "generate_large_prime",
    "description": (
        "Generate a random probable prime using Fermat's primality "
        "test. n_bits must be at least 2 and specifies the maximum "
        "bit length. The result is not guaranteed prime."
    ),
    "parameters": GetGeneratePrimeParams.model_json_schema(),
    "strict": True,
},
]