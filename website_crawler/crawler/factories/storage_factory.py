"""
Factory for creating storage backends.

This module provides a factory to create storage backend instances based on configuration.
Supports MongoDB and can be extended with other backends.
"""

from typing import Dict, Type, Any
from storage.base import BaseStorage
from storage.mongo import MongoStorage


class StorageFactory:
    """
    Factory for creating storage backends.
    
    This factory creates the appropriate storage backend instance based on the
    storage type specified in the configuration.
    """
    
    # Registry of available storage backends
    _storages: Dict[str, Type[BaseStorage]] = {
        "mongo": MongoStorage,
    }
    
    @classmethod
    def create(cls, storage_type: str, **kwargs: Any) -> BaseStorage:
        """
        Create a storage backend based on type.
        
        Args:
            storage_type: Type of storage ("mongo", "postgres", "s3", etc.)
            **kwargs: Additional configuration parameters for the storage
                     (e.g., host, port, database for MongoDB)
        
        Returns:
            Instance of the requested storage backend implementing BaseStorage
        
        Raises:
            ValueError: If storage_type is not supported
            TypeError: If the storage class cannot be instantiated with provided kwargs
        
        Example:
            >>> # Create a MongoDB storage
            >>> storage = StorageFactory.create("mongo", host="localhost", port=27017, database="crawler_db")
        """
        if storage_type not in cls._storages:
            available = ", ".join(cls._storages.keys())
            raise ValueError(
                f"Unknown storage type: '{storage_type}'. "
                f"Available types: {available}"
            )
        
        storage_class = cls._storages[storage_type]
        
        try:
            return storage_class(**kwargs)
        except Exception as e:
            raise TypeError(
                f"Failed to create {storage_type} storage with provided parameters: {e}"
            ) from e
    
    @classmethod
    def register(cls, storage_type: str, storage_class: Type[BaseStorage]) -> None:
        """
        Register a new storage backend type.
        
        This allows extending the factory with custom storage backends at runtime.
        
        Args:
            storage_type: Name identifier for the storage type
            storage_class: Class that implements BaseStorage
        
        Example:
            >>> from storage.postgres import PostgresStorage
            >>> StorageFactory.register("postgres", PostgresStorage)
            >>> storage = StorageFactory.create("postgres", connection_string="...")
        """
        if not issubclass(storage_class, BaseStorage):
            raise TypeError(
                f"Storage class must inherit from BaseStorage, "
                f"got {storage_class.__name__}"
            )
        cls._storages[storage_type] = storage_class
    
    @classmethod
    def get_available_types(cls) -> list[str]:
        """
        Get list of available storage types.
        
        Returns:
            List of storage type names that can be created
        """
        return list(cls._storages.keys())

