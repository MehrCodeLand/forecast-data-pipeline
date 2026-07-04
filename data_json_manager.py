import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from loguru import logger

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
    
    def _with_id_and_timestamp(self, current_data: List[Dict], new_data: Dict) -> Dict:
        record = dict(new_data)
        last_id = current_data[-1].get('id', -1) if current_data else -1
        record['id'] = last_id + 1
        record['timestamp'] = datetime.now().isoformat()
        return record
    
    async def save_data(self, data: Dict) -> bool:
        try:
            all_data = await self.read_data()
            record = self._with_id_and_timestamp(all_data, data)
            all_data.append(record)

            with open(self.filename, 'w') as f:
                json.dump(all_data, f, indent=2)

            logger.info(f"Data saved successfully with id: {record['id']}")
            return True
        except Exception as e:
            logger.error(f"Issues in save json: {e}")
            return False
