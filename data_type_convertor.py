from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

logger.add('logs/df.txt', rotation="1 week")


class WeatherDataConverter:
    def __init__(self, data: List[Dict]):
        self.raw_data = data
        self.df: Optional[pd.DataFrame] = None

    def to_dataframe(self) -> Optional[pd.DataFrame]:
        try:
            df = pd.DataFrame(self.raw_data)

            if "time" in df.columns:
                df["time"] = pd.to_datetime(df["time"])
                df = df.sort_values("time").reset_index(drop=True)

            self.df = df
            return df
        except Exception as e:
            logger.error(f"Error converting data to dataframe: {e}")
            return None

    def info(self) -> None:
        if self.df is not None:
            self.df.info()
