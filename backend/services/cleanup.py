"""
Database Cleanup Service
Automated cleanup of old data to prevent unbounded growth
"""

import os
from datetime import datetime, timedelta
from supabase import create_client
import asyncpg
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class DatabaseCleanup:
    """Handles automated database cleanup based on retention policies"""
    
    def __init__(self, supabase_url: str, supabase_key: str, checkpoint_db_uri: str = None):
        self.supabase = create_client(supabase_url, supabase_key)
        self.checkpoint_db_uri = checkpoint_db_uri
    
    async def cleanup_rejected_rfps(self, days: int = 30) -> int:
        """
        Delete rejected/abandoned RFPs older than N days
        
        Returns:
            Number of records deleted
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        try:
            # Delete from Supabase (cascading delete handles related records)
            result = self.supabase.table("rfp_summaries")\
                .delete()\
                .in_("status", ["rejected", "abandoned"])\
                .lt("created_at", cutoff.isoformat())\
                .execute()
            
            count = len(result.data) if result.data else 0
            logger.info(f"Deleted {count} rejected RFPs older than {days} days")
            return count
        except Exception as e:
            logger.error(f"Error cleaning rejected RFPs: {e}")
            return 0
    
    async def cleanup_old_completed_rfps(self, days: int = 90) -> int:
        """
        Delete completed (but not won/submitted) RFPs older than N days
        
        Returns:
            Number of records deleted
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        try:
            result = self.supabase.table("rfp_summaries")\
                .delete()\
                .eq("status", "completed")\
                .lt("created_at", cutoff.isoformat())\
                .execute()
            
            count = len(result.data) if result.data else 0
            logger.info(f"Deleted {count} completed RFPs older than {days} days")
            return count
        except Exception as e:
            logger.error(f"Error cleaning completed RFPs: {e}")
            return 0
    
    async def cleanup_old_checkpoints(self, days: int = 7) -> str:
        """
        Delete checkpoint data older than N days
        
        Returns:
            Result status message
        """
        if not self.checkpoint_db_uri:
            logger.warning("No checkpoint DB URI provided, skipping checkpoint cleanup")
            return "skipped"
        
        cutoff = datetime.now() - timedelta(days=days)
        
        try:
            conn = await asyncpg.connect(self.checkpoint_db_uri)
            result = await conn.execute(
                "DELETE FROM checkpoints WHERE created_at < $1",
                cutoff
            )
            await conn.close()
            
            logger.info(f"Deleted checkpoints older than {days} days: {result}")
            return result
        except Exception as e:
            logger.error(f"Error cleaning checkpoints: {e}")
            return "error"
    
    def cleanup_temp_review_pdfs(self, days: int = 7) -> int:
        """
        Delete temporary review PDFs older than N days
        
        Returns:
            Number of files deleted
        """
        output_dir = os.path.join("backend", "data", "output")
        
        if not os.path.exists(output_dir):
            return 0
        
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        try:
            for filename in os.listdir(output_dir):
                if filename.endswith("_review.pdf"):
                    file_path = os.path.join(output_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"Deleted temp review PDF: {filename}")
            
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning temp PDFs: {e}")
            return deleted_count
    
    async def run_full_cleanup(self) -> Dict[str, int]:
        """
        Run all cleanup tasks
        
        Returns:
            Dictionary with cleanup results
        """
        logger.info("Starting database cleanup...")
        
        rejected = await self.cleanup_rejected_rfps(days=30)
        completed = await self.cleanup_old_completed_rfps(days=90)
        checkpoints = await self.cleanup_old_checkpoints(days=7)
        temp_pdfs = self.cleanup_temp_review_pdfs(days=7)
        
        total = rejected + completed + temp_pdfs
        logger.info(f"Cleanup complete: {total} records/files deleted")
        
        return {
            "rejected_rfps": rejected,
            "completed_rfps": completed,
            "checkpoints": checkpoints,
            "temp_pdfs": temp_pdfs,
            "total": total
        }


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv()
    
    cleanup = DatabaseCleanup(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        checkpoint_db_uri=os.getenv("CHECKPOINT_DB_URI")
    )
    
    # Run cleanup
    result = asyncio.run(cleanup.run_full_cleanup())
    print(f"Cleanup result: {result}")
