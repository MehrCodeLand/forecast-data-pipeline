from loguru import logger
import json
from typing import List , Dict
from datetime import datetime
from pathlib import Path


logger.add('logs/json_data.txt', rotation="1 week")

class JSONDataManager:
    
    def __init__(self, filename: str):
        self.filename = filename
        self._ensure_directory()
    
    def _ensure_directory(self):
        Path(self.filename).parent.mkdir(parents=True, exist_ok=True)
    
    async def read_data(self) -> List[Dict]:
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                
                logger.warning("No list data in json file")
                return []
        except FileNotFoundError:
            logger.info(f"File {self.filename} not found, creating new file")
            return []
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {self.filename}: {e}")
            return []
        except Exception as e:
            logger.error(f"Issues in read_data: {e}")
            return []
    
    async def add_id_and_timestamp(self, current_data: List[Dict], new_data: Dict) -> Dict:
        try:
            if len(current_data) > 0:
                last_data = current_data[-1]
                last_id = last_data.get('id', -1)
                new_data["id"] = last_id + 1
            else:
                new_data['id'] = 0
            
            new_data['timestamp'] = datetime.now().isoformat()
            
            return new_data
        except Exception as e:
            logger.error(f"Issues in add_id_and_timestamp: {e}")
            new_data['id'] = 0
            new_data['timestamp'] = datetime.now().isoformat()
            return new_data
    
    async def save_data(self, data: Dict) -> bool:
        try:
            old_data = await self.read_data()
            data = await self.add_id_and_timestamp(old_data, data)
            old_data.append(data)

            with open(self.filename, 'w') as f:
                json.dump(old_data, f, indent=2)
            
            logger.info(f"Data saved successfully with id: {data.get('id')}")
            return True
        except Exception as e:
            logger.error(f"Issues in save json: {e}")
            return False
