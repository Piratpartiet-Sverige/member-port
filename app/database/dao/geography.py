from datetime import datetime
from typing import Union
from uuid import uuid4, UUID

from asyncpg import Connection
from asyncpg.exceptions import UniqueViolationError

from app.logger import logger
from app.models import Country, Municipality, Area
from app.database.dao.base import BaseDao


class GeographyDao(BaseDao):
    async def create_area(self, name: str, country_id: UUID, parent_id: Union[int, None]) -> Area:
        sql = """
            WITH i AS (
                SELECT nextval(pg_get_serial_sequence('areas', 'id')) AS id
            )
            INSERT INTO areas (id, name, created, "country", path) SELECT id, $1, $2, $3, CAST($4 || CAST(id AS TEXT) as ltree) FROM i
            RETURNING id;
        """
        created = datetime.utcnow()
        area_id = 0
        path = await self._get_path(parent_id)

        try:
            async with self.pool.acquire() as con:  # type: Connection
                area_id = await con.fetchval(sql, name, created, country_id, path)
        except Exception:
            logger.error("An error occured when trying to create new area!", stack_info=True)
            return None

        area = Area()
        area.id = area_id
        area.name = name
        area.created = created
        area.country_id = country_id
        area.path = path + str(area_id)

        return area

    async def get_areas_by_country(self, country_id: UUID) -> list:
        sql = 'SELECT id, name, created, path FROM areas WHERE "country" = $1;'

        try:
            async with self.pool.acquire() as con:  # type: Connection
                rows = await con.fetch(sql, country_id)
        except Exception:
            logger.error("An error occured when trying to create new area!", stack_info=True)
            return list()

        areas = []

        for row in rows:
            area = Area()
            area.id = row["id"]
            area.name = row["name"]
            area.created = row["created"]
            area.country_id = country_id
            area.path = row["path"]
            areas.append(area)

        return areas

    async def get_parent_areas_from_municipality(self, municipality_id) -> list:
        sql = 'SELECT "area" FROM municipalities WHERE id = $1;'
        try:
            async with self.pool.acquire() as con:  # type: Connection
                row = await con.fetchrow(sql, municipality_id)
        except Exception:
            logger.warning("No municipality with ID: " + str(municipality_id) + " was found!")
            return None

        sql = 'SELECT id FROM areas WHERE path @> (SELECT path FROM areas WHERE id = $1);'
        try:
            async with self.pool.acquire() as con:  # type: Connection
                rows = await con.fetch(sql, row["area"])
        except Exception:
            logger.warning("No area with ID: " + str(row["area"]) + " was found!")
            return None

        areas = list()

        for row in rows:
            areas.append(row["id"])

        return areas

    async def _get_path(self, parent_id: Union[int, None]) -> str:
        if parent_id is None:
            return ""

        path = ""
        sql = 'SELECT path FROM areas WHERE id = $1;'

        try:
            async with self.pool.acquire() as con:  # type: Connection
                path = await con.fetchval(sql, parent_id)
        except Exception:
            logger.error("An error occured when trying to retrieve the path for new area!", stack_info=True)
            return ""

        path += "."
        logger.debug("Path for new area: " + path)

        return path

    async def create_municipality(self, name: str, country_id: UUID, area_id: UUID) -> Union[Municipality, None]:
        sql = 'INSERT INTO municipalities (id, name, created, "country", "area") VALUES ($1, $2, $3, $4, $5);'
        created = datetime.utcnow()
        municipality_id = uuid4()

        try:
            async with self.pool.acquire() as con:  # type: Connection
                await con.execute(sql, municipality_id, name, created, country_id, area_id)
        except UniqueViolationError as exc:
            logger.debug(exc.__str__())
            logger.warning(
                "Tried to create municipality with the ID: " + str(municipality_id) + " and name: " + name + " but it already existed"
            )
            return None
        except Exception:
            logger.error("An error occured when trying to create new municipality!", stack_info=True)
            return None

        municipality = Municipality()
        municipality.name = name
        municipality.created = country_id
        municipality.country_id = country_id
        municipality.area_id = area_id

        return municipality

    async def get_municipality_by_id(self, municipality_id: UUID) -> Union[Municipality, None]:
        sql = 'SELECT name, created, "country", "area" FROM municipalities WHERE id = $1;'

        async with self.pool.acquire() as con:  # type: Connection
            row = await con.fetchrow(sql, municipality_id)

        municipality = Municipality()

        if row is not None:
            municipality.id = municipality_id
            municipality.name = row["name"]
            municipality.created = row["created"]
            municipality.country_id = row["country"]
            municipality.area_id = row["area"]
        else:
            return None

        return municipality

    async def get_municipality_by_name(self, name: str) -> Union[Municipality, None]:
        sql = 'SELECT id, created, "country", "area" FROM municipalities WHERE name = $1;'

        async with self.pool.acquire() as con:  # type: Connection
            row = await con.fetchrow(sql, name)

        municipality = Municipality()

        if row is not None:
            municipality.id = row["id"]
            municipality.name = name
            municipality.created = row["created"]
            municipality.country_id = row["country"]
            municipality.area_id = row["area"]
        else:
            return None

        return municipality

    async def get_municipalities_by_country(self, country_id: str) -> list:
        sql = 'SELECT id, name, created, "area" FROM municipalities WHERE "country" = $1;'

        async with self.pool.acquire() as con:  # type: Connection
            rows = await con.fetch(sql, country_id)

        municipalities = []

        for row in rows:
            municipality = Municipality()
            municipality.id = row["id"]
            municipality.name = row["name"]
            municipality.created = row["created"]
            municipality.country_id = country_id
            municipality.area_id = row["area"]
            municipalities.append(municipality)

        return municipalities

    async def get_municipalities(self) -> list:
        sql = 'SELECT id, name, created, "country", "area" FROM municipalities;'

        async with self.pool.acquire() as con:  # type: Connection
            rows = await con.fetch(sql)

        municipalities = []

        for row in rows:
            municipality = Municipality()
            municipality.id = row["id"]
            municipality.name = row["name"]
            municipality.created = row["created"]
            municipality.country_id = row["country"]
            municipality.area_id = row["area"]
            municipalities.append(municipality)

        return municipalities

    async def create_country(self, name: str) -> Union[Country, None]:
        sql = 'INSERT INTO countries (id, name, created) VALUES ($1, $2, $3);'
        created = datetime.utcnow()
        country_id = uuid4()

        try:
            async with self.pool.acquire() as con:  # type: Connection
                await con.execute(sql, country_id, name, created)
        except UniqueViolationError as exc:
            logger.debug(exc.__str__())
            logger.warning(
                "Tried to create country with the ID: " + str(country_id) + " and name: " + name + " but it already existed"
            )
            return None
        except Exception:
            logger.error("An error occured when trying to create new country!", stack_info=True)
            return None

        country = Country()
        country.id = country_id
        country.name = name
        country.created = created

        return country

    async def get_country_by_id(self, country_id: UUID) -> Union[Country, None]:
        sql = 'SELECT name, created FROM countries WHERE id = $1;'

        async with self.pool.acquire() as con:  # type: Connection
            row = await con.fetchrow(sql, country_id)

        country = Country()

        if row is not None:
            country.id = country_id
            country.name = row["name"]
            country.created = row["created"]
        else:
            return None

        return country

    async def get_country_by_name(self, country_name: str) -> Union[Country, None]:
        sql = 'SELECT id, created FROM countries WHERE name = $1;'

        async with self.pool.acquire() as con:  # type: Connection
            row = await con.fetchrow(sql, country_name)

        country = Country()

        if row is not None:
            country.id = row["id"]
            country.name = country
            country.created = row["created"]
        else:
            return None

        return country

    async def get_default_country(self) -> Union[Country, None]:
        sql = 'SELECT id, created FROM countries WHERE name = $1;'

        async with self.pool.acquire() as con:  # type: Connection
            row = await con.fetchrow(sql, "Sverige")

        country = Country()

        if row is not None:
            country.id = row["id"]
            country.name = country
            country.created = row["created"]
        else:
            return None

        return country

    async def get_countries(self) -> list:
        sql = 'SELECT id, name, created FROM countries;'

        async with self.pool.acquire() as con:  # type: Connection
            rows = await con.fetch(sql)

        countries = []

        for row in rows:
            country = Country()
            country.id = row["id"]
            country.name = row["name"]
            country.created = row["created"]
            countries.append(country)

        return countries
