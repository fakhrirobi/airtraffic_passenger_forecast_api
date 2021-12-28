import requests 
import pandas as pd 

url = 'http://127.0.0.1:5000/forecast_timeseries'



query = {
  "month_limit": "2021-06-01",
  "show_all_data" : True,
  "window_size": 12
}


def try_api() : 
  
    response = requests.post(url, json=query)
    data = pd.read_json(response.json())
    print(data.head())

if __name__ == '__main__' : 
    try_api()