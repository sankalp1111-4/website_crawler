"""
Change detection utilities for the website crawler.

This module provides utilities for detecting changes in crawled content
at both page and chunk levels.
"""
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from crawler.models.source_page import SourcePage
from crawler.models.page_chunk import PageChunk
from utils.hashing import hash_content
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("ChangeDetection", __name__)


class ChangeDetectionService:
    """
    Service for detecting changes in crawled content.
    
    Supports:
    - Page-level change detection (content_hash comparison)
    - Chunk-level change detection (per-chunk hash comparison)
    - Incremental update planning
    """
    
    @staticmethod
    def detect_page_changes(
        existing_source_page: Optional[SourcePage],
        new_content: str,
        new_content_hash: str
    ) -> Tuple[bool, bool]:
        """
        Detect if a page has changed.
        
        Args:
            existing_source_page: Existing SourcePage or None
            new_content: New content text
            new_content_hash: Hash of new content
            
        Returns:
            Tuple of (has_changed, is_new_page)
        """
        if existing_source_page is None:
            return True, True  # New page
        
        if existing_source_page.content_hash != new_content_hash:
            return True, False  # Changed
        
        return False, False  # Unchanged
    
    @staticmethod
    def detect_chunk_changes(
        existing_chunks: List[Dict[str, Any]],
        new_chunks: List[PageChunk]
    ) -> Tuple[List[PageChunk], List[str], List[str]]:
        """
        Detect which chunks have changed, which are new, and which are unchanged.
        
        Args:
            existing_chunks: List of existing chunk dictionaries from storage
            new_chunks: List of new PageChunk objects
            
        Returns:
            Tuple of (chunks_to_save, unchanged_chunk_ids, obsolete_chunk_ids)
            - chunks_to_save: Chunks that are new or changed
            - unchanged_chunk_ids: Chunk IDs that are unchanged (to preserve)
            - obsolete_chunk_ids: Chunk IDs that should be marked obsolete
        """
        # Create a map of existing chunks by chunk_id
        existing_chunks_map = {
            chunk.get('chunk_id') or chunk.get('_id'): chunk
            for chunk in existing_chunks
        }
        
        chunks_to_save = []
        unchanged_chunk_ids = []
        new_chunk_ids = {chunk.chunk_id for chunk in new_chunks}
        
        for new_chunk in new_chunks:
            existing_chunk = existing_chunks_map.get(new_chunk.chunk_id)
            
            if existing_chunk is None:
                # New chunk
                chunks_to_save.append(new_chunk)
            else:
                # Compare hashes
                existing_hash = existing_chunk.get('content_hash')
                if existing_hash != new_chunk.content_hash:
                    # Changed chunk
                    chunks_to_save.append(new_chunk)
                else:
                    # Unchanged chunk - preserve it
                    unchanged_chunk_ids.append(new_chunk.chunk_id)
        
        # Find obsolete chunks (exist in storage but not in new chunks)
        obsolete_chunk_ids = [
            chunk_id for chunk_id in existing_chunks_map.keys()
            if chunk_id not in new_chunk_ids
        ]
        
        return chunks_to_save, unchanged_chunk_ids, obsolete_chunk_ids
    
    @staticmethod
    def plan_incremental_update(
        source_page_id: str,
        existing_source_page: Optional[SourcePage],
        new_content: str,
        new_chunks: List[PageChunk],
        existing_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Plan an incremental update for a SourcePage.
        
        Args:
            source_page_id: SourcePage ID
            existing_source_page: Existing SourcePage or None
            new_content: New content text
            new_chunks: List of new PageChunk objects
            existing_chunks: List of existing chunk dictionaries
            
        Returns:
            Dictionary with update plan:
            - page_changed: bool
            - is_new_page: bool
            - chunks_to_save: List[PageChunk]
            - unchanged_chunk_ids: List[str]
            - obsolete_chunk_ids: List[str]
            - new_version: int
        """
        new_content_hash = hash_content(new_content)
        page_changed, is_new_page = ChangeDetectionService.detect_page_changes(
            existing_source_page,
            new_content,
            new_content_hash
        )
        
        chunks_to_save, unchanged_chunk_ids, obsolete_chunk_ids = ChangeDetectionService.detect_chunk_changes(
            existing_chunks,
            new_chunks
        )
        
        # Determine new version
        if is_new_page:
            new_version = 1
        elif page_changed:
            new_version = existing_source_page.version + 1
        else:
            new_version = existing_source_page.version if existing_source_page else 1
        
        return {
            'page_changed': page_changed,
            'is_new_page': is_new_page,
            'chunks_to_save': chunks_to_save,
            'unchanged_chunk_ids': unchanged_chunk_ids,
            'obsolete_chunk_ids': obsolete_chunk_ids,
            'new_version': new_version,
            'new_content_hash': new_content_hash
        }

