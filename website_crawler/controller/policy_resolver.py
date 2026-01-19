"""Policy resolver - maps client intent to internal configuration."""
import os
import aiohttp
from typing import Dict, Any
from urllib.parse import urlparse

from config.schema import MainConfig
from controller.models import ClientCrawlRequest
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
        self._apply_auth(client_request, config_dict)
        self._apply_chunking(client_request, config_dict)
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
    
    def _apply_rendering(self, request: ClientCrawlRequest, config_dict: Dict[str, Any]) -> None:
        """Apply JS rendering settings."""
        config_dict["engine"]["js_enabled"] = request.render_js
    
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
    
    def _apply_auth(self, request: ClientCrawlRequest, config_dict: Dict[str, Any]) -> None:
        """Apply authentication if provided."""
        if request.auth:
            if "headers" in request.auth and request.auth["headers"]:
                config_dict.setdefault("auth", {}).setdefault("headers", {}).update(request.auth["headers"])
            if "cookies" in request.auth and request.auth["cookies"]:
                config_dict.setdefault("auth", {}).setdefault("cookies", {}).update(request.auth["cookies"])
            if "basic_auth" in request.auth and request.auth["basic_auth"]:
                config_dict.setdefault("auth", {})["basic_auth"] = request.auth["basic_auth"]
    
    def _apply_chunking(self, request: ClientCrawlRequest, config_dict: Dict[str, Any]) -> None:
        """Enable chunking if requested."""
        # Note: MainConfig doesn't have chunking field, so we'll handle this differently
        # We'll set it in the dict that gets passed to orchestrator
        # This method is a placeholder - chunking is handled in the endpoint
        pass
    
    def _apply_safety_policies(self, config_dict: Dict[str, Any]) -> None:
        """Enforce backend safety policies."""
        max_pages_limit = int(os.getenv("CRAWLER_MAX_PAGES_LIMIT", "10000"))
        config_dict["crawler"]["max_pages"] = min(config_dict["crawler"]["max_pages"], max_pages_limit)
        
        if config_dict["crawler"]["max_pages"] > 500:
            config_dict["crawler"]["delay"] = max(config_dict["crawler"]["delay"], 2.0)
        
        config_dict["crawler"]["retries"] = max(config_dict["crawler"]["retries"], 3)
    
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

