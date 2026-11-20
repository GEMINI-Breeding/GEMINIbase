"""Plot identifiers in the database and the API (see gemini.workers.plot_ids)."""
from typing import Annotated, Union

from pydantic import BeforeValidator
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from gemini.workers.plot_ids import normalize_plot_number, plot_number_key  # noqa: F401


PlotNumber = Annotated[Union[int, str], BeforeValidator(normalize_plot_number)]


class PlotNumberType(TypeDecorator):
    """TEXT column holding a plot identifier: binds as text, reads back
    through normalize_plot_number."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        n = normalize_plot_number(value)
        return None if n is None else str(n)

    def process_result_value(self, value, dialect):
        return normalize_plot_number(value)
