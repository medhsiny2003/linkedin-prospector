"""Checkpoint manager to save and load process state."""

import json
import os
import uuid
import tempfile
import shutil
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from .logger import setup_logger

logger = setup_logger(__name__)

class CheckpointManager:
    """Manages the saving and loading of the execution checkpoint."""
    
    def __init__(self, checkpoint_path: str = 'data/checkpoint.json'):
        self.checkpoint_path = checkpoint_path
        self.state: Dict[str, Any] = {
            "run_id": str(uuid.uuid4()),
            "last_company": None,
            "last_keyword": None,
            "processed_companies": [],
            "total_contacts": 0,
            "last_contact_id": 0,
            "timestamp": datetime.now().isoformat(),
            "failed_queries": []
        }
        
    def save(self, state: Dict[str, Any] = None) -> None:
        """Save state to checkpoint file atomically."""
        if state:
            self.state.update(state)
            
        self.state["timestamp"] = datetime.now().isoformat()
        
        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        
        # Atomic write using temp file
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(self.checkpoint_path), text=True)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
            shutil.move(temp_path, self.checkpoint_path)
            logger.debug(f"Checkpoint saved to {self.checkpoint_path}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    def load(self) -> Optional[Dict[str, Any]]:
        """Load state from checkpoint file if it exists."""
        if not os.path.exists(self.checkpoint_path):
            return None
            
        try:
            with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                loaded_state = json.load(f)
                self.state.update(loaded_state)
                logger.info(f"Loaded checkpoint from {self.checkpoint_path}")
                return self.state
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted checkpoint file: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
            
    def update_progress(self, company: str, keyword: str, contact_id: int, total: int) -> None:
        """Update the checkpoint with current progress."""
        if company not in self.state["processed_companies"]:
            self.state["processed_companies"].append(company)
            
        self.state["last_company"] = company
        self.state["last_keyword"] = keyword
        self.state["last_contact_id"] = contact_id
        self.state["total_contacts"] = total
        self.save()
        
    def mark_failed(self, query: str) -> None:
        """Mark a specific query as failed."""
        if query not in self.state["failed_queries"]:
            self.state["failed_queries"].append(query)
            self.save()
            
    def get_resume_point(self) -> Optional[Tuple[str, str]]:
        """Get the last company and keyword to resume from."""
        loaded = self.load()
        if not loaded or not loaded.get("last_company"):
            return None
        return loaded.get("last_company"), loaded.get("last_keyword")
        
    def clear(self) -> None:
        """Clear the checkpoint file."""
        if os.path.exists(self.checkpoint_path):
            try:
                os.remove(self.checkpoint_path)
                logger.info(f"Cleared checkpoint at {self.checkpoint_path}")
            except Exception as e:
                logger.error(f"Failed to clear checkpoint: {e}")
        
        # Reset state
        self.state = {
            "run_id": str(uuid.uuid4()),
            "last_company": None,
            "last_keyword": None,
            "processed_companies": [],
            "total_contacts": 0,
            "last_contact_id": 0,
            "timestamp": datetime.now().isoformat(),
            "failed_queries": []
        }
