from data_json_manager import JSONDataManager
from loguru import logger
from datetime import datetime
import math

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
        
    async def get_avg_windspeed(self , period :int ):
        try:
            data = await self.json_manager.read_data()

            if not data:
                logger.warning("No data available for wind analysis.")
                return None

            if period <= 0:
                logger.warning("Invalid period: must be greater than zero.")
                return None
            
            period = min(period, len(data))

            total_speed = 0.0
            for ent in data[:period]:
                total_speed =+ ent["windspeed"]

            return round( total_speed / period  , 2)
        except Exception as e :
            logger.info(f"we have issues in get_avg_windspeed :  {e}")

    async def get_peak_windspeed(self, period: int):
        try:
            data = await self.json_manager.read_data()
            if not data:
                logger.warning("No data available for wind analysis.")
                return None

            if period <= 0:
                logger.warning("Invalid period: must be greater than zero.")
                return None

            period = min(period, len(data))
            
            max_speed = max(ent["windspeed"] for ent in data[:period])
            return round(max_speed, 2)
        
        except Exception as e:
            logger.error(f"Error in get_peak_windspeed: {e}")
            return None
        
    async def get_dominant_wind_direction(self, period: int):
        try:
            data = await self.json_manager.read_data()
            if not data:
                logger.warning("No data available for wind analysis.")
                return None

            if period <= 0:
                logger.warning("Invalid period: must be greater than zero.")
                return None

            period = min(period, len(data))
            
            # Convert to radians and calculate circular mean
            sin_sum = sum(math.sin(math.radians(ent["winddirection"])) for ent in data[:period])
            cos_sum = sum(math.cos(math.radians(ent["winddirection"])) for ent in data[:period])
            
            mean_direction = math.degrees(math.atan2(sin_sum, cos_sum))
            # Normalize to 0-360
            if mean_direction < 0:
                mean_direction += 360
            
            return round(mean_direction, 1)
        
        except Exception as e:
            logger.error(f"Error in get_dominant_wind_direction: {e}")
            return None


    async def get_wind_direction_variability(self, period: int):
        try:
            data = await self.json_manager.read_data()
            if not data or len(data) < 2:
                logger.warning("Insufficient data for variability analysis.")
                return None

            if period <= 0:
                logger.warning("Invalid period: must be greater than zero.")
                return None

            period = min(period, len(data))
            
            changes = []
            for i in range(1, period):
                diff = data[i]["winddirection"] - data[i-1]["winddirection"]
                # Normalize to -180 to 180 range
                if diff > 180:
                    diff -= 360
                elif diff < -180:
                    diff += 360
                changes.append(abs(diff))
            
            if not changes:
                return 0
            
            mean_change = sum(changes) / len(changes)
            variance = sum((x - mean_change) ** 2 for x in changes) / len(changes)
            std_dev = math.sqrt(variance)
            
            return round(std_dev, 2)
        
        except Exception as e:
            logger.error(f"Error in get_wind_direction_variability: {e}")
            return None
        
    async def get_calm_periods(self, period: int, threshold: float = 5.0):
        try:
            data = await self.json_manager.read_data()
            if not data:
                logger.warning("No data available for wind analysis.")
                return None

            if period <= 0:
                logger.warning("Invalid period: must be greater than zero.")
                return None

            period = min(period, len(data))
            
            calm_count = sum(1 for ent in data[:period] if ent["windspeed"] < threshold)
            
            return {
                "calm_periods": calm_count,
                "total_periods": period,
                "calm_percentage": round((calm_count / period) * 100, 1)
            }
        
        except Exception as e:
            logger.error(f"Error in get_calm_periods: {e}")
            return None







