"""
Document chunking for the website crawler.

This module provides token-aware chunking with semantic boundary preservation.
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from crawler.models.page_chunk import PageChunk
from utils.logging_config import ComponentLoggerAdapter, get_component_logger
from utils.hashing import hash_content

logger: ComponentLoggerAdapter = get_component_logger("ChunkingService", __name__)


class ChunkingService:
    """
    Service for chunking documents into smaller pieces with token awareness.
    
    Supports multiple chunking strategies:
    - Token-aware sentence-based chunking (recommended)
    - Token-aware paragraph-based chunking
    - Character-based chunking (fallback)
    
    All strategies preserve semantic boundaries and generate deterministic chunks.
    """
    
    def __init__(
        self,
        chunk_size_tokens: int = 512,
        chunk_overlap_tokens: int = 50,
        chunk_size_chars: Optional[int] = None,
        chunk_overlap_chars: Optional[int] = None,
        strategy: str = "sentence",
        preserve_sentences: bool = True,
        preserve_paragraphs: bool = True,
        tokenizer: str = "cl100k_base"  # OpenAI's tokenizer
    ):
        """
        Initialize chunking service.
        
        Args:
            chunk_size_tokens: Maximum tokens per chunk (default: 512)
            chunk_overlap_tokens: Overlap between chunks in tokens (default: 50)
            chunk_size_chars: Fallback max characters if tokenizer unavailable
            chunk_overlap_chars: Fallback overlap in characters if tokenizer unavailable
            strategy: Chunking strategy ("sentence", "paragraph", "character")
            preserve_sentences: Always preserve sentence boundaries (default: True)
            preserve_paragraphs: Prefer paragraph boundaries (default: True)
            tokenizer: Tokenizer to use (default: "cl100k_base" for GPT models)
        """
        self.chunk_size_tokens = chunk_size_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens
        self.chunk_size_chars = chunk_size_chars or (chunk_size_tokens * 4)  # Rough estimate: 4 chars per token
        self.chunk_overlap_chars = chunk_overlap_chars or (chunk_overlap_tokens * 4)
        self.strategy = strategy
        self.preserve_sentences = preserve_sentences
        self.preserve_paragraphs = preserve_paragraphs
        
        # Initialize tokenizer if available
        self.tokenizer = None
        self.use_tokens = False
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.get_encoding(tokenizer)
                self.use_tokens = True
                logger.info(f"[ChunkingService] Tokenizer '{tokenizer}' initialized")
            except Exception as e:
                logger.warning(f"[ChunkingService] Failed to initialize tokenizer: {e}, falling back to character-based")
                self.use_tokens = False
        else:
            logger.warning("[ChunkingService] tiktoken not available, using character-based chunking")
        
        logger.info(f"[ChunkingService] Initialized: strategy={strategy}, token_aware={self.use_tokens}, "
                   f"chunk_size_tokens={chunk_size_tokens}, chunk_size_chars={self.chunk_size_chars}")
    
    def chunk_content(
        self,
        source_page_id: str,
        content: str,
        version: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[PageChunk]:
        """
        Chunk content into PageChunk objects with deterministic IDs.
        
        Args:
            source_page_id: ID of the source page
            content: Content to chunk
            version: Version number from SourcePage
            metadata: Optional metadata to include in chunks
            
        Returns:
            List of PageChunk objects with deterministic IDs and hashes
        """
        if not content:
            logger.warning(f"[ChunkingService] Empty content for source_page {source_page_id}")
            return []
        
        url_logger = logger.with_url(source_page_id)
        
        with url_logger.component_flow("chunk_content", source_page_id=source_page_id, content_length=len(content)):
            try:
                # Generate chunks based on strategy
                if self.strategy == "sentence":
                    chunk_texts = self._chunk_by_sentence_token_aware(content)
                elif self.strategy == "paragraph":
                    chunk_texts = self._chunk_by_paragraph_token_aware(content)
                elif self.strategy == "character":
                    chunk_texts = self._chunk_by_character(content)
                else:
                    logger.warning(f"[ChunkingService] Unknown strategy {self.strategy}, using sentence-based")
                    chunk_texts = self._chunk_by_sentence_token_aware(content)
                
                # Create PageChunk objects with deterministic IDs
                page_chunks = []
                for i, chunk_content in enumerate(chunk_texts):
                    # Deterministic chunk ID
                    chunk_id = f"{source_page_id}_chunk_{i}"
                    
                    # Compute content hash for change detection
                    chunk_hash = hash_content(chunk_content)
                    
                    # Count tokens if tokenizer available
                    token_count = None
                    if self.use_tokens and self.tokenizer:
                        try:
                            token_count = len(self.tokenizer.encode(chunk_content))
                        except Exception as e:
                            logger.warning(f"[ChunkingService] Failed to count tokens: {e}")
                    
                    # Calculate overlap (overlap with previous chunk)
                    overlap_size = 0
                    if i > 0 and chunk_texts:
                        # Find overlap by comparing start of current chunk with end of previous
                        prev_chunk = chunk_texts[i - 1]
                        # Simple overlap detection: check if start of current matches end of previous
                        # This is approximate; actual overlap is managed during chunking
                        overlap_size = self.chunk_overlap_chars if not self.use_tokens else (
                            self.chunk_overlap_tokens * 4  # Rough estimate
                        )
                    
                    chunk = PageChunk(
                        chunk_id=chunk_id,
                        source_page_id=source_page_id,
                        chunk_index=i,
                        content=chunk_content,
                        content_hash=chunk_hash,
                        chunk_size=len(chunk_content),
                        overlap_size=overlap_size,
                        token_count=token_count,
                        embedding=None,  # To be populated by embedding service
                        metadata={
                            **(metadata or {}),
                            'total_chunks': len(chunk_texts),
                            'chunked_at': datetime.utcnow().isoformat(),
                            'strategy': self.strategy,
                            'token_aware': self.use_tokens
                        },
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        version=version,
                        status="active"
                    )
                    page_chunks.append(chunk)
                
                url_logger.info(f"[ChunkingService] Created {len(page_chunks)} chunks from source_page {source_page_id}")
                return page_chunks
                
            except Exception as e:
                url_logger.error(f"[ChunkingService] Chunking failed: {e}", exc_info=True)
                # Return single chunk as fallback
                chunk_id = f"{source_page_id}_chunk_0"
                chunk_hash = hash_content(content)
                token_count = None
                if self.use_tokens and self.tokenizer:
                    try:
                        token_count = len(self.tokenizer.encode(content))
                    except Exception:
                        pass
                
                return [PageChunk(
                    chunk_id=chunk_id,
                    source_page_id=source_page_id,
                    chunk_index=0,
                    content=content,
                    content_hash=chunk_hash,
                    chunk_size=len(content),
                    overlap_size=0,
                    token_count=token_count,
                    metadata=metadata or {},
                    version=version,
                    status="active"
                )]
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tokenizer."""
        if not self.use_tokens or not self.tokenizer:
            # Fallback: estimate tokens as characters / 4
            return len(text) // 4
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text) // 4
    
    def _chunk_by_character(self, content: str) -> List[str]:
        """
        Chunk content by character count (fallback method).
        
        Args:
            content: Content to chunk
            
        Returns:
            List of chunk strings
        """
        chunks = []
        start = 0
        
        while start < len(content):
            end = min(start + self.chunk_size_chars, len(content))
            chunk = content[start:end]
            chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap_chars
            if start >= len(content):
                break
        
        return chunks
    
    def _chunk_by_sentence_token_aware(self, content: str) -> List[str]:
        """
        Chunk content by sentences with token awareness, preserving sentence boundaries.
        
        Args:
            content: Content to chunk
            
        Returns:
            List of chunk strings
        """
        # Split by sentences (preserve sentence boundaries)
        sentences = re.split(r'(?<=[.!?])\s+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return [content] if content else []
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)
            
            # If adding this sentence would exceed token limit, finalize current chunk
            if current_tokens + sentence_tokens > self.chunk_size_tokens and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Start new chunk with overlap
                if self.chunk_overlap_tokens > 0 and current_chunk:
                    # Include last few sentences for overlap
                    overlap_sentences = []
                    overlap_tokens = 0
                    for s in reversed(current_chunk):
                        s_tokens = self._count_tokens(s)
                        if overlap_tokens + s_tokens <= self.chunk_overlap_tokens:
                            overlap_sentences.insert(0, s)
                            overlap_tokens += s_tokens
                        else:
                            break
                    current_chunk = overlap_sentences
                    current_tokens = overlap_tokens
                else:
                    current_chunk = []
                    current_tokens = 0
            
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _chunk_by_paragraph_token_aware(self, content: str) -> List[str]:
        """
        Chunk content by paragraphs with token awareness, preserving paragraph boundaries.
        
        Args:
            content: Content to chunk
            
        Returns:
            List of chunk strings
        """
        # Split by paragraphs (double newlines)
        paragraphs = re.split(r'\n\s*\n', content)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if not paragraphs:
            return [content] if content else []
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for paragraph in paragraphs:
            paragraph_tokens = self._count_tokens(paragraph)
            
            # If adding this paragraph would exceed token limit, finalize current chunk
            if current_tokens + paragraph_tokens > self.chunk_size_tokens and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                
                # Start new chunk with overlap
                if self.chunk_overlap_tokens > 0 and current_chunk:
                    # Include last paragraph for overlap
                    current_chunk = [current_chunk[-1]] if current_chunk else []
                    current_tokens = self._count_tokens(current_chunk[0]) if current_chunk else 0
                else:
                    current_chunk = []
                    current_tokens = 0
            
            current_chunk.append(paragraph)
            current_tokens += paragraph_tokens
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
