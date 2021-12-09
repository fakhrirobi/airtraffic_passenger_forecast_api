from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional 
from datetime import date
from dateutil import relativedelta

from statsmodels.tsa.statespace.sarimax import SARIMAXResults
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


import uvicorn
import pandas as pd


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}



#// TODO : Scatch the Diagram of API Process 

class api_request(BaseModel) : 
    #month_limit has following format YYYY-MM-01 , the forecast is monthly basis  
    month_limit : str 
    show_all_data : Optional[bool] = True 
    window_size : Optional[int] = 12
    

@app.post("/forecast_timeseries") 
async def return_forecast(req:api_request) : 
    #//TODO create module to load the model 
    ts_model = SARIMAXResults.load('moving_avg_diff_passenger_ovetime_model.pkl')
    #//TODO create a function to return the step from latest date 2016-03-01 
    date_object = date.fromisoformat(req.month_limit)
    month = date_object.month
    year = date_object.year
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
    
#creating function for modifying the forecast result
    
    def output_forecast(forecast_result,window_size=12) : 
        origin_data= pd.read_csv('passanger_total.csv',parse_dates=['Period'])
        ''' 
        Parameters : 
        forecast_result = list_of values contain forecast result ( callback result)
        origin_data : pd.Dataframe withour transformation 
            
        '''
        window_size = int(window_size)
        def transform_moving_avg_diff(forecast_result,window_size=window_size,num_month=12,origin_data=origin_data) : 
            clone_original_data = origin_data.copy()
            clone_original_data.to_csv('x.csv')
            import math 
            #len checking of forecast_result if result only contain 1 : 
            temp_data = pd.DataFrame(data={'Period':[],'Passenger Total' : []})
        
            forecast_result = forecast_result.to_list()
            list_df = [temp_data]
            for idx in range(len(forecast_result)) : 
                z = clone_original_data['Passenger Total'].tail(window_size).rolling(window_size).mean()
                prev_rolling_mean_window = z[z.isnull() ==  False].to_list()[0]
                transformed_value = math.ceil(prev_rolling_mean_window + forecast_result[idx])
                del prev_rolling_mean_window
                
                #generating date by using logic 
                # get last_index = origin_data.index[-1]
                last_month = 3 
                last_year = 2016
                month_step = idx + 1 
                total_month  = month_step + last_month
                print(total_month)
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
                        
                # def add_month(total_month,num_month) : 
                #     if total_month % num_month  == 0 : 
                #         return 12 
                if total_month <= num_month : 
                    #because if we yield december it will add to 1 so december will be 2017 
                    year_add =  year_addition(total_month,num_month)
                    last_year += year_add 
                    month_add  = month_step % num_month 
                    last_month += month_add
                elif total_month >  num_month : 
                    year_add = year_addition(total_month,num_month)
                    last_year += year_add 
                    month_add  = total_month % num_month if total_month % num_month != 0 else 12 
                    #find more proper name 
                    add_more_month = last_month + month_add
                    last_month -= add_more_month
                date_str = []
                date_str = f'{last_year}-0{abs(last_month)}-01' if abs(last_month) < 10 else f'{last_year}-{abs(last_month)}-01'
                
                # append directly to the dataset 
                append_df = pd.DataFrame(data={'Period':[date_str],'Passenger Total' : [transformed_value]})
                # append_df.to_csv('inspact.csv')
                # clone_original_data.append(append_df)
                clone_original_data = pd.concat([clone_original_data,append_df],axis=0)
                
                # temp_data.append(append_df)
                list_df.append(append_df)
            temp_data = pd.concat(list_df,axis=0)
            
            return temp_data
        transformed_forecast_data = transform_moving_avg_diff(forecast_result)
        return transformed_forecast_data
    output_before_json = output_forecast(forecast_result)
    
    print(output_before_json)
    import json
    d = output_before_json.to_dict(orient='records')
    j = json.dumps(d)
    return j
    # json_compatible_item_data = jsonable_encoder(output_before_json)
    # return JSONResponse(content=json_compatible_item_data)
    #start creating figure 
    

if __name__ == '__main__' : 
    uvicorn.run(app=app,host="127.0.0.1", port=5000, log_level="info")