"""
Batch processing for the website crawler.

This module provides utilities for batch processing operations.
"""
import asyncio
from typing import List, Dict, Any, Callable, Optional, TypeVar, Awaitable
from collections.abc import Iterable

from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("BatchProcessor", __name__)

T = TypeVar('T')
R = TypeVar('R')


class BatchProcessor:
    """
    Service for batch processing operations.
    
    Supports batch processing of documents, URLs, and other operations.
    """
    
    def __init__(
        self,
        batch_size: int = 10,
        max_concurrent: int = 5,
        fail_fast: bool = False
    ):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of items to process per batch
            max_concurrent: Maximum concurrent operations
            fail_fast: Whether to stop on first error
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.fail_fast = fail_fast
        
        logger.info(f"[BatchProcessor] Initialized: batch_size={batch_size}, max_concurrent={max_concurrent}")
    
    async def process_batch_async(
        self,
        items: Iterable[T],
        processor: Callable[[T], Awaitable[R]],
        error_handler: Optional[Callable[[T, Exception], None]] = None
    ) -> List[R]:
        """
        Process items in batches asynchronously.
        
        Args:
            items: Iterable of items to process
            processor: Async function to process each item
            error_handler: Optional error handler function
            
        Returns:
            List of results
        """
        items_list = list(items)
        total_items = len(items_list)
        
        logger.info(f"[BatchProcessor] Processing {total_items} items in batches of {self.batch_size}")
        
        results = []
        errors = []
        
        # Process in batches
        for batch_start in range(0, total_items, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_items)
            batch = items_list[batch_start:batch_end]
            
            logger.info(f"[BatchProcessor] Processing batch {batch_start // self.batch_size + 1} ({batch_start + 1}-{batch_end}/{total_items})")
            
            # Process batch with concurrency limit
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def process_item(item: T) -> Optional[R]:
                """Process a single item with semaphore."""
                async with semaphore:
                    try:
                        return await processor(item)
                    except Exception as e:
                        if error_handler:
                            error_handler(item, e)
                        else:
                            logger.error(f"[BatchProcessor] Error processing item: {e}", exc_info=True)
                        
                        if self.fail_fast:
                            raise
                        
                        errors.append((item, e))
                        return None
            
            # Process all items in batch concurrently
            batch_results = await asyncio.gather(*[process_item(item) for item in batch], return_exceptions=True)
            
            # Filter out None results and exceptions
            for result in batch_results:
                if result is not None and not isinstance(result, Exception):
                    results.append(result)
                elif isinstance(result, Exception) and self.fail_fast:
                    raise result
        
        logger.info(f"[BatchProcessor] Completed: {len(results)} successful, {len(errors)} errors")
        
        return results
    
    def process_batch(
        self,
        items: Iterable[T],
        processor: Callable[[T], R],
        error_handler: Optional[Callable[[T, Exception], None]] = None
    ) -> List[R]:
        """
        Process items in batches synchronously.
        
        Args:
            items: Iterable of items to process
            processor: Function to process each item
            error_handler: Optional error handler function
            
        Returns:
            List of results
        """
        items_list = list(items)
        total_items = len(items_list)
        
        logger.info(f"[BatchProcessor] Processing {total_items} items in batches of {self.batch_size}")
        
        results = []
        errors = []
        
        # Process in batches
        for batch_start in range(0, total_items, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_items)
            batch = items_list[batch_start:batch_end]
            
            logger.info(f"[BatchProcessor] Processing batch {batch_start // self.batch_size + 1} ({batch_start + 1}-{batch_end}/{total_items})")
            
            # Process batch
            for item in batch:
                try:
                    result = processor(item)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    if error_handler:
                        error_handler(item, e)
                    else:
                        logger.error(f"[BatchProcessor] Error processing item: {e}", exc_info=True)
                    
                    if self.fail_fast:
                        raise
                    
                    errors.append((item, e))
        
        logger.info(f"[BatchProcessor] Completed: {len(results)} successful, {len(errors)} errors")
        
        return results
    
    async def save_batch(
        self,
        documents: List[Dict[str, Any]],
        save_func: Callable[[Dict[str, Any]], Awaitable[Any]],
        error_handler: Optional[Callable[[Dict[str, Any], Exception], None]] = None
    ) -> List[Any]:
        """
        Save documents in batches.
        
        Args:
            documents: List of document dictionaries
            save_func: Async function to save a document
            error_handler: Optional error handler function
            
        Returns:
            List of save results
        """
        return await self.process_batch_async(documents, save_func, error_handler)
    
    def chunk_and_process(
        self,
        items: Iterable[T],
        chunker: Callable[[T], List[Any]],
        processor: Callable[[Any], R],
        error_handler: Optional[Callable[[Any, Exception], None]] = None
    ) -> List[R]:
        """
        Chunk items and process chunks in batches.
        
        Args:
            items: Iterable of items to chunk and process
            chunker: Function to chunk each item into sub-items
            processor: Function to process each chunk
            error_handler: Optional error handler function
            
        Returns:
            List of results
        """
        # First, chunk all items
        all_chunks = []
        for item in items:
            chunks = chunker(item)
            all_chunks.extend(chunks)
        
        # Then process chunks in batches
        return self.process_batch(all_chunks, processor, error_handler)

