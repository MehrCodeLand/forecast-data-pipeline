from data_json_manager import JSONDataManager
from loguru import logger
from datetime import datetime

logger.add('logs/analyse.txt', rotation="1 week")

class Analyse:
    def __init__(self , json_manger : JSONDataManager ):
        self.json_manager = json_manger


    async def get_avg(self , period : int  ):
        try:
            data = await self.json_manager.read_data()     
            if not data:
                logger.warning("No data available for analysis.")
                return None

            if period <= 0:
                logger.warning("Invalid period: must be greater than zero.")
                return None

            if period > len(data):
                logger.warning(f"Requested period ({period}) exceeds available data ({len(data)}). Using available data.")
                period = len(data)
            else:
                sum_temp = 0            
                for ent in data[:period]:
                    sum_temp += ent["temperature"]
                return sum_temp / period
        except Exception as e :
            logger.info(f"we have issues in Analyse and get_avg method : {e}")

    async def estimate_avg_of_rate_of_change(self , hours : int ):
        try:
            data = await self.json_manager.read_data()

            if not data:
                logger.warning("No data available for analysis.")
                return None
            
            if hours <= 0 :
                logger.warning("Invalid hours data as an Input")
                return None 
            
            data = data[:hours]

            rates = []
            for i in range(1, len(data)):
                delta_temp = data[i]["temperature"] - data[i-1]["temperature"]
                delta_time_hours = data[i]["interval"] / 3600  
                rate = delta_temp / delta_time_hours
                rates.append(rate)

            return sum(rates) / len(rates)
        
        except Exception as e:
            logger.info(f"we have issues in estimate_avg_of_rate_of_change : {e}")
            return None

    async def estimate_delta(self , hours : int ):
        try:
            data = await self.json_manager.read_data()

            if not data:
                logger.warning("No data available for analysis.")
                return None
            
            if hours <= 0 :
                logger.warning("Invalid hours data as an Input")
                return None 
            
            delta1 = data[0]["temperature"]
            delta2 = data[hours - 1 ]["temperature"]
            return round((delta2 - delta1 ) / hours  , 2)
        
        except Exception as e :
            logger.info(f"we have issues in estimate_delta : {e}")
            return None




