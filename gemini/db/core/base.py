"""
Base models for database interactions in GEMINI.

This module defines the core SQLAlchemy models and utility methods for
interacting with the GEMINI database, including base classes for
standard tables, views, materialized views, and columnar tables.
"""
from __future__ import annotations

from typing import Any, List, Optional, Dict
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy import TIMESTAMP, JSON, DATE
from sqlalchemy import MetaData, text
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy_mixins.serialize import SerializeMixin
from sqlalchemy.dialects.postgresql import insert as pg_insert, JSONB

import logging
from gemini.manager import GEMINIManager, GEMINIComponentType
from gemini.db.core.engine import DatabaseEngine
from gemini.db.config import DatabaseConfig


db_config_settings = GEMINIManager().get_component_settings(GEMINIComponentType.DB)
db_config = DatabaseConfig(
    database_url=f"postgresql://{db_config_settings['GEMINI_DB_USER']}:{db_config_settings['GEMINI_DB_PASSWORD']}@{db_config_settings['GEMINI_DB_HOSTNAME']}:{db_config_settings['GEMINI_DB_PORT']}/{db_config_settings['GEMINI_DB_NAME']}"
)
metadata_obj = MetaData(schema="gemini")
db_engine = DatabaseEngine(db_config)


logger = logging.getLogger(__name__)

class BaseModel(DeclarativeBase, SerializeMixin):
    """
    Base class for all SQLAlchemy models in GEMINI.

    Provides common CRUD (Create, Read, Update, Delete) operations,
    field validation, and utility methods for database interaction.
    """

    __abstract__ = True
    metadata = metadata_obj


    @classmethod
    def set_engine(cls, engine: DatabaseEngine) -> None:
        """
        Sets the global database engine for the models.

        Args:
            engine (DatabaseEngine): The database engine instance to use.
        """
        global db_engine
        db_engine = engine


    @classmethod
    def unique_fields(cls) -> List[str]:
        """
        Retrieves a list of unique field names for the model's table.

        Returns:
            list: A list of strings, where each string is the name of a unique field.
        """
        unique_fields = []
        for constraint in cls.__table__.constraints:
            if isinstance(constraint, UniqueConstraint):
                for column in constraint.columns:
                    unique_fields.append(column.name)


        return unique_fields
    

    @classmethod
    def validate_fields(cls, **kwargs: Any) -> Dict[str, Any]:
        """
        Validates and filters keyword arguments against the model's columns.

        Removes None values, empty dictionaries, and arguments that do not
        correspond to actual columns in the table.

        Returns:
            dict: A dictionary of validated and filtered keyword arguments.
        """
        # Remove None values from the kwargs
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        # Remove empty dicts from the kwargs
        kwargs = {k: v for k, v in kwargs.items() if v != {}}
        # Remove Items that are not columns in the table
        columns = cls.__table__.columns.keys()
        kwargs = {k: v for k, v in kwargs.items() if k in columns}
        return kwargs
    

    @classmethod
    def count(cls) -> int:
        """
        Returns the total number of instances of the model in the database.

        Returns:
            int: The total record count.
        """
        from sqlalchemy import func
        query = select(func.count()).select_from(cls)
        with db_engine.get_session() as session:
            result = session.execute(query).scalar()
        return result or 0

    @classmethod
    def create(cls, **kwargs: Any) -> BaseModel:
        """
        Creates a new instance of the model and adds it to the database.

        Args:
            **kwargs: Keyword arguments corresponding to the model's fields.

        Returns:
            BaseModel: The newly created model instance.
        """
        kwargs = cls.validate_fields(**kwargs)
        instance = cls(**kwargs)
        with db_engine.get_session() as session:
            session.add(instance)
        return instance
    

    @classmethod
    def exists(cls, **kwargs: Any) -> bool:
        """
        Checks if an instance with the given parameters exists in the database.

        Args:
            **kwargs: Keyword arguments to search for.

        Returns:
            bool: True if an instance exists, False otherwise.
        """
        kwargs = cls.validate_fields(**kwargs)
        if kwargs == {}:
            return False
        instance = cls.get_by_parameters(**kwargs)
        if instance:
            return True
        return False


    @classmethod
    def all(cls, limit: int = None, offset: int = None) -> List[BaseModel]:
        """
        Retrieves all instances of the model from the database.

        Args:
            limit (int, optional): Maximum number of records to return.
            offset (int, optional): Number of records to skip before returning.

        Returns:
            list: A list of all model instances.
        """
        query = select(cls)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        with db_engine.get_session() as session:
            result = session.execute(query).scalars().all()
        return result
    

    @classmethod
    def get(cls, id: Any) -> BaseModel | None:
        """
        Retrieves a single instance of the model by its ID.

        Args:
            id: The ID of the instance to retrieve.

        Returns:
            BaseModel or None: The model instance if found, otherwise None.
        """
        query = select(cls).where(cls.id == id)
        with db_engine.get_session() as session:
            result = session.execute(query).scalar_one_or_none()
        return result
    

    @classmethod
    def get_by_parameters(cls, **kwargs: Any) -> BaseModel | None:
        """
        Retrieves a single instance of the model based on provided parameters.

        Args:
            **kwargs: Keyword arguments to filter the query.

        Returns:
            BaseModel or None: The model instance if found, otherwise None.
        """
        query = select(cls)
        kwargs = cls.validate_fields(**kwargs)
        if kwargs == {}:
            return None
        for key, value in kwargs.items():
            attribute = getattr(cls, key)
            if isinstance(attribute.type, JSON):
                query = query.where(attribute.contains(value))
            elif isinstance(attribute.type, TIMESTAMP):
                query = query.where(attribute == value)
            else:
                query = query.where(attribute == value)
        with db_engine.get_session() as session:
            result = session.execute(query).scalars().first()
        return result
    

    @classmethod
    def update(cls, instance, **kwargs: Any) -> BaseModel:
        """
        Updates an existing instance of the model with new values.

        Args:
            instance (BaseModel): The instance to update.
            **kwargs: Keyword arguments with the new values for the fields.

        Returns:
            BaseModel: The updated model instance.
        """
        with db_engine.get_session() as session:
            kwargs = cls.validate_fields(**kwargs)
            for key, value in kwargs.items():
                setattr(instance, key, value)
            session.add(instance)
        return instance
    
    @classmethod
    def get_or_update(cls, instance, **kwargs: Any) -> BaseModel:
        """
        Retrieves an existing instance based on unique fields, or updates the provided instance.

        If an instance with matching unique fields exists, it is returned.
        Otherwise, the provided instance is updated with the given kwargs.

        Args:
            instance (BaseModel): The instance to potentially update.
            **kwargs: Keyword arguments for unique fields and other updates.

        Returns:
            BaseModel: An existing instance or the updated provided instance.
        """
        unique_fields = cls.unique_fields()
        kwargs = cls.validate_fields(**kwargs)
        unique_kwargs = {key: value for key, value in kwargs.items() if key in unique_fields}
        if unique_kwargs == {}:
            return instance
        existing_instance = cls.get_by_parameters(**unique_kwargs)
        if existing_instance:
            return existing_instance
        # If no existing instance found, update the current instance
        if not instance:
            instance = cls(**kwargs)
        else:
            # Update the existing instance with new values
            instance = cls.update(instance, **kwargs)
        return instance


    @classmethod
    def get_or_create(cls, **kwargs: Any) -> Optional[BaseModel]:
        """
        Retrieves an existing instance or creates a new one if it doesn't exist.

        Args:
            **kwargs: Keyword arguments to search for or create the instance.

        Returns:
            BaseModel or None: An existing or newly created model instance, or None if unique fields are missing.
        """
        unique_fields = cls.unique_fields()
        kwargs = cls.validate_fields(**kwargs)
        unique_kwargs = {key: value for key, value in kwargs.items() if key in unique_fields}
        if unique_kwargs == {}:
            return None
        instance = cls.get_by_parameters(**unique_kwargs)
        if instance:
            return instance
        else:
            instance = cls.create(**kwargs)
            return instance
        
    @classmethod
    def delete(cls, instance: Any) -> bool:
        """
        Deletes an instance from the database.

        Args:
            instance (BaseModel): The instance to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        try:
            with db_engine.get_session() as session:
                merged = session.merge(instance)
                session.delete(merged)
            return True
        except Exception as e:
            logger.error(f"Error deleting instance: {e}")
            return False
    
    @classmethod
    def get_model_from_table_name(cls, table_name) -> Optional[BaseModel]:
        """
        Retrieves a model class from its table name.

        Args:
            table_name (str): The name of the table.

        Returns:
            Table: The SQLAlchemy Table object.
        """
        return cls.metadata.tables[f"{cls.metadata.schema}.{table_name}"]
        

    @classmethod
    def insert_bulk(cls, constraint: Any, data) -> List[UUID]:
        """
        Performs a bulk insert operation with conflict handling.

        Args:
            constraint: The unique constraint to use for conflict resolution.
            data (list): A list of dictionaries, where each dictionary represents a row to insert.

        Returns:
            list: A list of IDs of the inserted records.
        """
        with db_engine.get_session() as session:
            table = cls.__table__
            stmt = pg_insert(table).on_conflict_do_nothing(constraint=constraint).returning(table.c.id)
            inserted_records = session.execute(stmt, data, execution_options={"populate_existing": True})
            inserted_ids = [record.id for record in inserted_records]
            return inserted_ids
        
        
    @classmethod
    def update_bulk(cls, constraint: Any, upsert_on: Any, data) -> List[UUID]:
        """
        Performs a bulk update (upsert) operation with conflict handling.

        Args:
            constraint: The unique constraint to use for conflict resolution.
            upsert_on: The column to update on conflict.
            data (list): A list of dictionaries, where each dictionary represents a row to upsert.

        Returns:
            list: A list of IDs of the upserted records.
        """
        with db_engine.get_session() as session:
            table = cls.__table__
            insert_stmt = pg_insert(table)
            stmt = insert_stmt.on_conflict_do_update(
                constraint=constraint,
                set_={upsert_on: insert_stmt.excluded[upsert_on]}
            ).returning(table.c.id)
            inserted_records = session.execute(stmt, data, execution_options={"populate_existing": True})
            inserted_ids = [record.id for record in inserted_records]
            return inserted_ids
        

    @classmethod
    def delete_bulk(cls, data: Any) -> bool:
        """
        Performs a bulk delete operation.

        Args:
            data (list): A list of IDs of the records to delete.

        Returns:
            bool: True if deletion was successful.
        """
        with db_engine.get_session() as session:
            table = cls.__table__
            stmt = delete(table).where(table.c.id.in_(data))
            session.execute(stmt)
            return True
        
    @classmethod
    def update_parameter(cls, instance: Any, parameter_name: str, parameter_value: Any) -> BaseModel:
        """
        Updates a specific parameter (column) of an existing instance.

        Args:
            instance (BaseModel): The instance to update.
            parameter_name (str): The name of the parameter (column) to update.
            parameter_value: The new value for the parameter.

        Returns:
            BaseModel: The updated model instance.

        Raises:
            ValueError: If `parameter_name` is not a valid column.
        """
        # Check if parameter_name is a valid column in the table
        if parameter_name not in cls.__table__.columns:
            raise ValueError(f"{parameter_name} is not a valid column in {cls.__tablename__}")
        with db_engine.get_session() as session:
            # Update the parameter value
            setattr(instance, parameter_name, parameter_value)
            session.add(instance)
        return instance
        
        
    @classmethod
    def update_or_create(cls, constraint: Any, **kwargs: Any) -> Optional[BaseModel]:
        """
        Updates an existing instance or creates a new one if it doesn't exist, based on a unique constraint.

        Args:
            constraint: The unique constraint to use for identifying existing records.
            **kwargs: Keyword arguments to search for or create/update the instance.

        Returns:
            BaseModel or None: An existing, updated, or newly created model instance, or None if unique fields are missing.
        """
        unique_fields = cls.unique_fields()
        kwargs = cls.validate_fields(**kwargs)
        unique_kwargs = {key: value for key, value in kwargs.items() if key in unique_fields}
        if unique_kwargs == {}:
            return None
        instance = cls.get_by_parameters(**unique_kwargs)
        if instance:
            instance = cls.update(instance, **kwargs)
            return instance
        else:
            instance = cls.create(**kwargs)
            return instance
        

    @classmethod
    def search(cls, **kwargs: Any) -> List[BaseModel]:
        """
        Searches for instances based on provided parameters.

        Supports searching by exact match for most types, and `contains` for JSONB fields.

        Args:
            **kwargs: Keyword arguments to filter the search.

        Returns:
            list: A list of matching model instances.
        """
        with db_engine.get_session() as session:
            query = select(cls)
            kwargs = cls.validate_fields(**kwargs)
            for key, value in kwargs.items():
                attribute = getattr(cls, key)
                if isinstance(attribute.type, JSONB):
                    query = query.where(attribute.contains(value))
                elif isinstance(attribute.type, TIMESTAMP):
                    query = query.where(attribute >= value)
                elif isinstance(attribute.type, DATE):
                    query = query.where(attribute == value)  
                else:
                    query = query.where(attribute == value)
            result = session.execute(query).scalars().all()
        return result
        

    @classmethod
    def paginate(cls, order_by: Any, page_number: int, page_limit: int, **kwargs: Any) -> tuple[int, int, List[BaseModel]]:
        """
        Paginates through instances of the model based on provided parameters.

        Args:
            order_by: The column to order the results by.
            page_number (int): The current page number (1-indexed).
            page_limit (int): The maximum number of records per page.
            **kwargs: Keyword arguments to filter the query.

        Returns:
            tuple: A tuple containing (total_records, total_pages, current_page_results).
        """
        with db_engine.get_session() as session:
            query = session.query(cls)
            kwargs = cls.validate_fields(**kwargs)
            for key, value in kwargs.items():
                attribute = getattr(cls, key)
                if isinstance(attribute.type, JSON):
                    query = query.filter(attribute.contains(value))
                elif isinstance(attribute.type, TIMESTAMP):
                    query = query.filter(attribute >= value)
                elif isinstance(attribute.type, DATE):
                    query = query.filter(attribute == value)
                else:
                    query = query.filter(attribute == value)
            number_of_records = query.count()
            number_of_pages = number_of_records // page_limit
            if page_number > 0:
                query = query.offset((page_number - 1) * page_limit)
            query = query.limit(page_limit)
            query_result = query.all()
        return number_of_records, number_of_pages, query_result
    

    @classmethod
    def stream(cls, **kwargs: Any) -> Any:
        """
        Streams instances of the model in partitions.

        Args:
            **kwargs: Keyword arguments to filter the stream.

        Yields:
            BaseModel: Instances of the model.
        """
        query = select(cls)
        kwargs = cls.validate_fields(**kwargs)
        for key, value in kwargs.items():
            attribute = getattr(cls, key)
            if isinstance(attribute.type, JSON):
                query = query.where(attribute.contains(value))
            elif isinstance(attribute.type, TIMESTAMP):
                query = query.where(attribute >= value)
            elif isinstance(attribute.type, DATE):
                query = query.where(attribute == value)
            else:
                query = query.where(attribute == value)
        query = query.execution_options(yield_per=1000)
        with db_engine.get_session() as session:
            for partition in session.execute(query).scalars().partitions():
                for instance in partition:
                    yield instance


    @classmethod
    def rawstream(cls, **kwargs: Any) -> Any:
        """
        Streams instances of the model directly from the database connection in partitions.

        Args:
            **kwargs: Keyword arguments to filter the stream.

        Yields:
            BaseModel: Instances of the model.
        """
        query = select(cls)
        kwargs = cls.validate_fields(**kwargs)
        for key, value in kwargs.items():
            attribute = getattr(cls, key)
            if isinstance(attribute.type, JSON):
                query = query.where(attribute.contains(value))
            elif isinstance(attribute.type, TIMESTAMP):
                query = query.where(attribute >= value)
            elif isinstance(attribute.type, DATE):
                query = query.where(attribute == value)
            else:
                query = query.where(attribute == value)
        query = query.execution_options(yield_per=50)
        with db_engine.get_engine().connect() as conn:
            result = conn.execute(query).scalars().partitions()
            for partition in result:
                for instance in partition:
                    yield instance



    # ===================================================================
    # Async CRUD methods
    # ===================================================================

    @classmethod
    async def async_create(cls, **kwargs: Any) -> BaseModel:
        """Async version of create()."""
        kwargs = cls.validate_fields(**kwargs)
        instance = cls(**kwargs)
        async with db_engine.get_async_session() as session:
            session.add(instance)
        return instance

    @classmethod
    async def async_get(cls, id: Any) -> BaseModel | None:
        """Async version of get()."""
        query = select(cls).where(cls.id == id)
        async with db_engine.get_async_session() as session:
            result = await session.execute(query)
            return result.scalar_one_or_none()

    @classmethod
    async def async_get_by_parameters(cls, **kwargs: Any) -> BaseModel | None:
        """Async version of get_by_parameters()."""
        query = select(cls)
        kwargs = cls.validate_fields(**kwargs)
        if kwargs == {}:
            return None
        for key, value in kwargs.items():
            attribute = getattr(cls, key)
            if isinstance(attribute.type, JSON):
                query = query.where(attribute.contains(value))
            elif isinstance(attribute.type, TIMESTAMP):
                query = query.where(attribute == value)
            else:
                query = query.where(attribute == value)
        async with db_engine.get_async_session() as session:
            result = await session.execute(query)
            return result.scalars().first()

    @classmethod
    async def async_all(cls, limit: int = None, offset: int = None) -> List[BaseModel]:
        """Async version of all()."""
        query = select(cls)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        async with db_engine.get_async_session() as session:
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def async_search(cls, **kwargs: Any) -> List[BaseModel]:
        """Async version of search()."""
        query = select(cls)
        kwargs = cls.validate_fields(**kwargs)
        for key, value in kwargs.items():
            attribute = getattr(cls, key)
            if isinstance(attribute.type, JSONB):
                query = query.where(attribute.contains(value))
            elif isinstance(attribute.type, TIMESTAMP):
                query = query.where(attribute >= value)
            elif isinstance(attribute.type, DATE):
                query = query.where(attribute == value)
            else:
                query = query.where(attribute == value)
        async with db_engine.get_async_session() as session:
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def async_update(cls, instance, **kwargs: Any) -> BaseModel:
        """Async version of update()."""
        kwargs = cls.validate_fields(**kwargs)
        for key, value in kwargs.items():
            setattr(instance, key, value)
        async with db_engine.get_async_session() as session:
            session.add(instance)
        return instance

    @classmethod
    async def async_delete(cls, instance: Any) -> bool:
        """Async version of delete()."""
        try:
            async with db_engine.get_async_session() as session:
                await session.delete(instance)
            return True
        except Exception as e:
            logger.error(f"Error deleting instance: {e}")
            return False

    @classmethod
    async def async_exists(cls, **kwargs: Any) -> bool:
        """Async version of exists()."""
        kwargs = cls.validate_fields(**kwargs)
        if kwargs == {}:
            return False
        instance = await cls.async_get_by_parameters(**kwargs)
        return instance is not None

    @classmethod
    async def async_get_or_create(cls, **kwargs: Any) -> Optional[BaseModel]:
        """Async version of get_or_create()."""
        unique_fields = cls.unique_fields()
        kwargs = cls.validate_fields(**kwargs)
        unique_kwargs = {key: value for key, value in kwargs.items() if key in unique_fields}
        if unique_kwargs == {}:
            return None
        instance = await cls.async_get_by_parameters(**unique_kwargs)
        if instance:
            return instance
        return await cls.async_create(**kwargs)

    @classmethod
    async def async_count(cls) -> int:
        """Async version of count()."""
        from sqlalchemy import func
        query = select(func.count()).select_from(cls)
        async with db_engine.get_async_session() as session:
            result = await session.execute(query)
            return result.scalar() or 0

    @classmethod
    async def async_insert_bulk(cls, constraint: Any, data) -> List[UUID]:
        """Async version of insert_bulk()."""
        async with db_engine.get_async_session() as session:
            table = cls.__table__
            stmt = pg_insert(table).on_conflict_do_nothing(constraint=constraint).returning(table.c.id)
            inserted_records = await session.execute(stmt, data, execution_options={"populate_existing": True})
            return [record.id for record in inserted_records]


class ViewBaseModel(BaseModel):
    """
    Base class for database views.
    """

    __abstract__ = True


class MaterializedViewBaseModel(BaseModel):
    """
    Base class for materialized database views.

    Provides a method for explicitly refreshing the materialized view.
    Read operations use the current state without auto-refreshing,
    since IMMV (Incrementally Maintained Materialized Views) are kept
    up-to-date automatically by pg_ivm. Call refresh() explicitly only
    when using standard (non-IMMV) materialized views that need manual refresh.
    """

    __abstract__ = True

    @classmethod
    def refresh(cls) -> None:
        """
        Explicitly refreshes the materialized view.

        Only needed for standard materialized views. IMMV views maintained
        by pg_ivm are updated automatically on base table changes.
        """
        with db_engine.get_session() as session:
            query = text(f"REFRESH MATERIALIZED VIEW {cls.__table__.name}")
            session.execute(query)
    
class ColumnarBaseModel(BaseModel):
    """
    Base class for columnar database models.
    """

    __abstract__ = True
    

    @classmethod
    def all(cls, limit: int = 100, offset: int = None) -> List[Any]:
        """
        Retrieves all instances of the columnar model with an optional limit.

        Args:
            limit (int): The maximum number of records to retrieve. Defaults to 100.
            offset (int, optional): Number of records to skip before returning.

        Returns:
            list: A list of all columnar model instances.
        """
        query = select(cls)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        with db_engine.get_session() as session:
            result = session.execute(query).scalars().all()
        return result
