import logging
from contextlib import contextmanager
from typing import Any, Callable, Generator, TypeVar

import mysql.connector

from backend.config import database_config


logger = logging.getLogger(__name__)
T = TypeVar("T")


class DatabaseUnavailable(RuntimeError):
    """Raised when a database operation cannot be completed."""


class DatabaseConflict(RuntimeError):
    """Raised when database constraints reject a requested change."""


@contextmanager
def connection_manager() -> Generator[Any, None, None]:
    connection = None
    try:
        configuration = database_config()
    except RuntimeError as exc:
        logger.error("Database configuration error: %s", str(exc))
        raise DatabaseUnavailable(str(exc)) from exc
    try:
        connection = mysql.connector.connect(**configuration)
    except mysql.connector.Error as exc:
        logger.error("MySQL operation failed (%s).", type(exc).__name__)
        raise DatabaseUnavailable("The database is unavailable.") from exc
    try:
        yield connection
    finally:
        if connection is not None:
            connection.close()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    try:
        with connection_manager() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(query, params)
                return cursor.fetchall()
            finally:
                cursor.close()
    except mysql.connector.Error as exc:
        logger.error("MySQL query failed (%s).", type(exc).__name__)
        raise DatabaseUnavailable("The database query could not be completed.") from exc


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    try:
        with connection_manager() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(query, params)
                return cursor.fetchone()
            finally:
                cursor.close()
    except mysql.connector.Error as exc:
        logger.error("MySQL query failed (%s).", type(exc).__name__)
        raise DatabaseUnavailable("The database query could not be completed.") from exc


def run_transaction(operation: Callable[[Any], T]) -> T:
    try:
        with connection_manager() as connection:
            try:
                result = operation(connection)
                connection.commit()
                return result
            except Exception:
                connection.rollback()
                raise
    except mysql.connector.IntegrityError as exc:
        logger.info("MySQL constraint rejected an update (%s).", type(exc).__name__)
        raise DatabaseConflict(
            "The change conflicts with related records or database business rules."
        ) from exc
    except mysql.connector.Error as exc:
        logger.error("MySQL transaction failed (%s).", type(exc).__name__)
        raise DatabaseUnavailable("The database update could not be completed.") from exc


def check_connection() -> bool:
    return fetch_one("SELECT 1 AS connected") == {"connected": 1}
