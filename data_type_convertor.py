import pandas as pd
import numpy as np
from typing import List, Dict
from loguru import logger

logger.add('logs/df.txt', rotation="1 week")

class WeatherDataConverter:
    def __init__(self , data:List[Dict]):
        self.raw_data = data
        self.df = None 

    async def to_dataframe(self):
        try:
            df = pd.DataFrame(self.raw_data)

            if "time" in df.columns:
                df["time"] = pd.to_datetime(df["time"])

            if "time" in df.columns:
                df = df.sort_values("time").reset_index(drop=True)

            self.df = df 
            return df 
        except Exception as e :
            logger.info(f"we have issues with to dataframe : {e}")
            return None 
    
    async def info(self):
        try:
            if self.df is None :
                return None
            print(f"Info is : {self.df.info()}")
        except Exception as e :
            logger.info(f"we have issues with info {e}")
            return None 
        
    
        