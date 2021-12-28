#importing utilities we are going to use
from fastapi import FastAPI
#pydantic to create request body
from pydantic import BaseModel
# typing.Optional to create requets body that is not mandatory with default value
from typing import Optional 
# we are going to use datetime manipulation package to create timestamp
from datetime import date
from dateutil import relativedelta
#loading trained forecast model
from statsmodels.tsa.statespace.sarimax import SARIMAXResults


#import uvicorn for server 
import uvicorn
#for data manipulation
import pandas as pd
import math 
import json


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Head to endpoint /forecast_timeseries to fetch forecast data or to /docs to see documentation"}




#creating request body for endpoint /timeseris_forecasting
#we use pydantic BaseModel
class api_request(BaseModel) : 
    #month_limit has following format YYYY-MM-01 , the forecast is monthly basis  
    month_limit : str 
    # show_all_data is optional and default falue is True
    show_all_data : Optional[bool] = True 
    #window_size is related with model rolling average number, i picked 12
    # since forecast is monthly basis with 12 months in a year
    window_size : Optional[int] = 12
    

@app.post("/forecast_timeseries") 
async def return_forecast(req:api_request) : 
    
    ts_model = SARIMAXResults.load('moving_avg_diff_passenger_ovetime_model.pkl')
        # parsing the forecast range from request body and convert into date_object using 	date.fromisoformat
    date_object = date.fromisoformat(req.month_limit)
    #parsing month number from date object
    month = date_object.month
    #parsing year number from date object
    year = date_object.year
    #blank list to contain forecast_result
    to_forecast_date = []
    # to_forecast_date = date.fromisoformat(f'{year}-0{month}-01') if int(month) <10 else date.fromisoformat(f'{year}-{month}-01')
    if month < 10 : 
        to_forecast_date.append(date.fromisoformat(f'{year}-0{month}-01') )
    elif month >= 10 : 
        to_forecast_date.append(date.fromisoformat(f'{year}-{month}-01') )
    last_date = date.fromisoformat('2016-03-01')
    date_diff = relativedelta.relativedelta(to_forecast_date[0], last_date)
    forecast_step = date_diff.months + date_diff.years * 12
    #create function to load model 
    forecast_result  = ts_model.forecast(steps=int(forecast_step))
    

    
    #part 1
    #reading the training data for later use in rolling mean calculation 
    origin_data= pd.read_csv('passanger_total.csv',parse_dates=['Period'])
    #get the value of window size for rolling mean from request body 
    window_size = int(req.window_size)

#create function to reverse the value of forecast result before moving average diff
    def transform_moving_avg_diff(forecast_result,window_size=window_size,
                                num_month=12,origin_data=origin_data) : 
        #cloning original data to avoid overwrite
        clone_original_data = origin_data.copy()
        
        #creating a temporary dataframe for dataframe insert 
        temp_data = pd.DataFrame(data={'Period':[],'Passenger Total' : []})
        # the forecast result is still formated as dataframe ( output of SARIMAXResults)
        forecast_result = forecast_result.to_list()
        list_df = [temp_data]
        # loop through each forecast result to modify them individually
        for idx in range(len(forecast_result)) : 
            rolling_mean_df = clone_original_data['Passenger Total'].tail(window_size).rolling(window_size).mean()
            # get the value of rolling mean  
            prev_rolling_mean_window = rolling_mean_df[rolling_mean_df.isnull() ==  False].to_list()[0]
            # to get whole number we use math.ceil 
            transformed_value = math.ceil(prev_rolling_mean_window + forecast_result[idx])
            # del the prev_rolling_mean_window
            del prev_rolling_mean_window

            # since our training data end up in march 2016 we are going to predict the rest 
            # i define datetime component for creating timestamp for each forecast result
            last_month = 3 
            last_year = 2016
            month_step = idx + 1 
            total_month  = month_step + last_month
            # logic behind year addition
            def year_addition(total_month,num_month) : 
                if total_month <=12 : 
                    return 0
                elif total_month > 12 : 
                    if total_month % 12 == 0 : 
                        multi= math.floor(total_month/num_month)
                        
                        return multi -1 
                    elif total_month % 12 != 0 : 
                        multi= math.floor(total_month/num_month)
                        return multi
            
            # case when total month to be forecasted less than 12 but can exceed december
            if total_month <= num_month : 
                
                year_add =  year_addition(total_month,num_month)
                #adding year step 
                last_year += year_add 
                # add the modulus value of month step / 12 indicating the rest of the month 
                month_add  = month_step % num_month 
                #add month step 
                last_month += month_add
            # case when total month > 12 
            elif total_month >  num_month : 
                
                year_add = year_addition(total_month,num_month)
                last_year += year_add 
                month_add  = total_month % num_month if total_month % num_month != 0 else 12 
            
                add_more_month = last_month + month_add
                last_month -= add_more_month
            # create empty list for dataframe column value
            date_str = []
            # logic for value with lastmonth < 10 will add string '0' in front of the value
            date_str = f'{last_year}-0{abs(last_month)}-01' if abs(last_month) < 10 else f'{last_year}-{abs(last_month)}-01'
            
            # appending timestamp with its transformed value 
            append_df = pd.DataFrame(data={'Period':[date_str],'Passenger Total' :[transformed_value]})
            # appending each individual result for the next rolling mean 
            clone_original_data = pd.concat([clone_original_data,append_df],axis=0)

            # appending each forecast result without its original data to serve json response 
            list_df.append(append_df)
        #joining all forecast data in 0 axis 
        temp_data = pd.concat(list_df,axis=0)
        #return final forecast data
        return temp_data
    transformed_forecast_data =    transform_moving_avg_diff(forecast_result=forecast_result,window_size=window_size)
    
    
    
    
    dict_forecast = transformed_forecast_data.to_dict(orient='records')
    json_ = json.dumps(dict_forecast)
    return json_
    # json_compatible_item_data = jsonable_encoder(output_before_json)
    # return JSONResponse(content=json_compatible_item_data)
    #start creating figure 
    
# running the server
if __name__ == '__main__' : 
    uvicorn.run(app=app,host="127.0.0.1", port=5000, log_level="info")