"""Policy resolver - maps client intent to internal configuration."""
import os
import aiohttp
from typing import Dict, Any
from urllib.parse import urlparse

from config.schema import MainConfig
from controller.models import ClientCrawlRequest, ConfigOverride
from utils.logging_config import ComponentLoggerAdapter, get_component_logger


class CrawlPolicyResolver:
    """Resolves client intent into fully-configured internal settings."""
    
    def __init__(self, base_config: MainConfig):
        self.base_config = base_config
        self.logger: ComponentLoggerAdapter = get_component_logger("PolicyResolver", __name__)
    
    async def resolve(self, client_request: ClientCrawlRequest) -> MainConfig:
        """Resolve client request into full internal configuration."""
        # Convert to dict for modification (MainConfig is frozen)
        config_dict = self.base_config.model_dump()
        
        self._apply_crawl_scope(client_request, config_dict)
        await self._apply_strategy(client_request, config_dict)
        self._apply_rendering(client_request, config_dict)
        self._apply_extraction(client_request, config_dict)
        self._apply_domain_restrictions(client_request, config_dict)
        self._apply_chunking(client_request, config_dict)
        self._apply_safety_policies(config_dict)
        
        # Apply config override if provided (after all other policies)
        if client_request.config_override:
            self._apply_config_override(client_request.config_override, config_dict)
            # Re-apply safety policies after override to ensure safety limits are maintained
            self._apply_safety_policies(config_dict)
        
        # Validate and return MainConfig
        return MainConfig.model_validate(config_dict)
    
    def _apply_crawl_scope(self, request: ClientCrawlRequest, config_dict: Dict[str, Any]) -> None:
        """Apply max_pages and max_depth with safety limits."""
        if request.max_pages is not None:
            max_limit = int(os.getenv("CRAWLER_MAX_PAGES_LIMIT", "10000"))
            config_dict["crawler"]["max_pages"] = min(request.max_pages, max_limit)
            config_dict["strategy"]["max_pages"] = min(request.max_pages, max_limit)
        
        if request.max_depth is not None:
            max_limit = int(os.getenv("CRAWLER_MAX_DEPTH_LIMIT", "10"))
            config_dict["crawler"]["max_depth"] = min(request.max_depth, max_limit)
            config_dict["strategy"]["max_depth"] = min(request.max_depth, max_limit)
    
    async def _apply_strategy(self, request: ClientCrawlRequest, config_dict: Dict[str, Any]) -> None:
        """Auto-select or apply strategy."""
        # Log original strategy from base config
        original_strategy = config_dict.get("strategy", {}).get("type", "bfs")
        
        if request.strategy == "auto":
            parsed_url = urlparse(str(request.url))
            sitemap_url = f"{parsed_url.scheme}://{parsed_url.netloc}/sitemap.xml"
            has_sitemap = await self._check_sitemap_exists(sitemap_url)
            
            if has_sitemap:
                selected_strategy = "sitemap"
            elif request.max_pages and request.max_pages > 100:
                selected_strategy = "bfs"
            else:
                selected_strategy = "dfs"
            
            config_dict["strategy"]["type"] = selected_strategy
            self.logger.info(
                f"[PolicyResolver] Auto-selected strategy: {selected_strategy} "
                f"(original: {original_strategy}, client: auto)"
            )
        else:
            # Client explicitly requested a strategy - override base config
            config_dict["strategy"]["type"] = request.strategy
            self.logger.info(
                f"[PolicyResolver] Client requested strategy: {request.strategy} "
                f"(original: {original_strategy})"
            )
        
        # Verify the strategy was set correctly
        final_strategy = config_dict.get("strategy", {}).get("type")
        if final_strategy != request.strategy and request.strategy != "auto":
            self.logger.warning(
                f"[PolicyResolver] Strategy mismatch! Requested: {request.strategy}, "
                f"Final: {final_strategy}"
            )
        
        # Apply priority patterns if provided
        if request.priority_patterns:
            existing_patterns = set(config_dict["strategy"].get("priority_patterns", []))
            existing_patterns.update(request.priority_patterns)
            config_dict["strategy"]["priority_patterns"] = list(existing_patterns)
            self.logger.info(
                f"[PolicyResolver] Applied {len(request.priority_patterns)} priority patterns"
            )
    
    def _apply_rendering(self, request: ClientCrawlRequest, config_dict: Dict[str, Any]) -> None:
        """Apply JS rendering settings."""
        config_dict["engine"]["js_enabled"] = request.render_js
        
        # Apply wait_for selector if provided
        if request.wait_for is not None:
            config_dict["engine"]["wait_for"] = request.wait_for
            self.logger.info(
                f"[PolicyResolver] Applied wait_for selector: {request.wait_for}"
            )
    
    def _apply_extraction(self, request: ClientCrawlRequest, config_dict: Dict[str, Any]) -> None:
        """Map extract dict to extraction config."""
        extract = request.extract
        config_dict["extraction"]["extract_text"] = extract.get("text", True)
        config_dict["extraction"]["extract_links"] = extract.get("links", True)
        config_dict["extraction"]["extract_images"] = extract.get("images", False)
        config_dict["extraction"]["extract_metadata"] = extract.get("metadata", True)
        
        if request.selectors:
            config_dict["extraction"]["selectors"] = request.selectors
            config_dict["extraction"]["type"] = "css"
    
    def _apply_domain_restrictions(self, request: ClientCrawlRequest, config_dict: Dict[str, Any]) -> None:
        """Apply domain restrictions."""
        if request.allowed_domains:
            config_dict["crawler"]["allowed_domains"] = request.allowed_domains
        if request.exclude_patterns:
            existing = set(config_dict["crawler"].get("exclude_patterns", []))
            existing.update(request.exclude_patterns)
            config_dict["crawler"]["exclude_patterns"] = list(existing)
    
    def _apply_chunking(self, request: ClientCrawlRequest, config_dict: Dict[str, Any]) -> None:
        """Enable chunking if requested."""
        # Note: MainConfig doesn't have chunking field, so we'll handle this differently
        # We'll set it in the dict that gets passed to orchestrator
        # This method is a placeholder - chunking is handled in the endpoint
        pass
    
    def _apply_safety_policies(self, config_dict: Dict[str, Any]) -> None:
        """Enforce backend safety policies."""
        crawler_config = config_dict.get("crawler", {})
        engine_config = config_dict.get("engine", {})
        
        # 1. Enforce max_pages limit
        max_pages_limit = int(os.getenv("CRAWLER_MAX_PAGES_LIMIT", "10000"))
        crawler_config["max_pages"] = min(crawler_config.get("max_pages", 100), max_pages_limit)
        if config_dict.get("strategy", {}).get("max_pages"):
            config_dict["strategy"]["max_pages"] = min(
                config_dict["strategy"]["max_pages"], 
                max_pages_limit
            )
        
        # 2. Enforce minimum delay for large crawls
        if crawler_config["max_pages"] > 500:
            min_delay = float(os.getenv("CRAWLER_MIN_DELAY_LARGE", "2.0"))
            crawler_config["delay"] = max(crawler_config.get("delay", 1.0), min_delay)
        
        # 3. Enforce minimum retries
        min_retries = int(os.getenv("CRAWLER_MIN_RETRIES", "3"))
        crawler_config["retries"] = max(crawler_config.get("retries", 3), min_retries)
        
        # 4. Enforce timeout limits
        max_timeout = int(os.getenv("CRAWLER_MAX_TIMEOUT", "300"))
        crawler_config["timeout"] = min(crawler_config.get("timeout", 30), max_timeout)
        
        # 5. Enforce rate limiting (if not set, apply default)
        if crawler_config.get("rate_limit") is None:
            default_rate_limit = os.getenv("CRAWLER_DEFAULT_RATE_LIMIT")
            if default_rate_limit:
                crawler_config["rate_limit"] = float(default_rate_limit)
        elif crawler_config.get("rate_limit") is not None and crawler_config["rate_limit"] > 0:
            max_rate_limit = float(os.getenv("CRAWLER_MAX_RATE_LIMIT", "10.0"))
            crawler_config["rate_limit"] = min(crawler_config["rate_limit"], max_rate_limit)
        
        # 6. Always respect robots.txt (safety override)
        # Allow override via env var for special cases, but default to True
        force_robots_txt = os.getenv("CRAWLER_FORCE_ROBOTS_TXT", "true").lower() == "true"
        if force_robots_txt:
            crawler_config["respect_robots_txt"] = True
            self.logger.info("[PolicyResolver] Enforced robots.txt respect (safety policy)")
        
        # 7. Enforce max HTML size limits
        max_html_size_limit = int(os.getenv("CRAWLER_MAX_HTML_SIZE_LIMIT", "16777216"))  # 16MB default
        current_max_html_size = crawler_config.get("max_html_size", 16777216)
        crawler_config["max_html_size"] = min(current_max_html_size, max_html_size_limit)
        
        # 8. Enforce wait_timeout limits
        max_wait_timeout = int(os.getenv("CRAWLER_MAX_WAIT_TIMEOUT", "300"))
        engine_config["wait_timeout"] = min(engine_config.get("wait_timeout", 30), max_wait_timeout)
        
        # Update config dict
        config_dict["crawler"] = crawler_config
        config_dict["engine"] = engine_config
    
    def _apply_config_override(self, override: ConfigOverride, config_dict: Dict[str, Any]) -> None:
        """Apply type-safe config override."""
        if override.crawler:
            config_dict["crawler"].update(override.crawler)
        if override.engine:
            config_dict["engine"].update(override.engine)
        if override.extraction:
            config_dict["extraction"].update(override.extraction)
        if override.strategy:
            config_dict["strategy"].update(override.strategy)
        if override.chunking:
            config_dict["chunking"] = {**config_dict.get("chunking", {}), **override.chunking}
        
        self.logger.info("[PolicyResolver] Applied config override")
    
    async def _check_sitemap_exists(self, sitemap_url: str) -> bool:
        """Check if sitemap exists at URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    sitemap_url,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    return resp.status == 200
        except:
            return False

