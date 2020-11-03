from app.logger import logger

from datetime import datetime
from typing import Union
from uuid import uuid4, UUID

from asyncpg import Connection
from asyncpg.exceptions import UniqueViolationError

from app.models import Organization
from app.database.dao.member_org import MemberOrgDao


class OrganizationsDao(MemberOrgDao):
    async def create_organization(self, name, description, active) -> Union[Organization, None]:
        sql = "INSERT INTO organizations (id, name, description, active, created) VALUES ($1, $2, $3, $4, $5);"

        id = uuid4()
        created = datetime.utcnow()

        try:
            async with self.pool.acquire() as con:  # type: Connection
                await con.execute(sql, id, name, description, active, created)
        except UniqueViolationError as exc:
            logger.debug(exc.__str__())
            logger.warning("Tried to create organization: " + str(id) + " but organization already existed")
            return None

        organization = Organization()
        organization.id = id
        organization.name = name
        organization.description = description
        organization.active = active
        organization.created = created

        return organization

    async def get_default_organization(self) -> Union[Organization, None]:
        sql = "SELECT default_organization FROM settings"

        try:
            async with self.pool.acquire() as con:  # type: Connection
                row = await con.fetchrow(sql)
        except Exception:
            logger.error("An error occured when trying to retrieve the default organization!", stack_info=True)
            return None

        if row["default_organization"] is None:
            logger.debug("No default organization found...")
            return None

        return await self.get_organization_by_id(row["default_organization"])

    async def get_organization_by_name(self, name: str) -> Union[Organization, None]:
        sql = "SELECT id, description, created FROM organizations WHERE name = $1"

        try:
            async with self.pool.acquire() as con:  # type: Connection
                row = await con.fetchrow(sql, name)
        except Exception:
            logger.error("An error occured when trying to retrieve an organization by name!", stack_info=True)
            return None

        if row is None:
            logger.debug("No  organization found with name: " + name)
            return None

        organization = Organization()
        organization.id = row["id"]
        organization.name = name
        organization.name = row["description"]
        organization.name = row["created"]

        return organization

    async def get_organizations(self, search: str, order_column: str, order_dir_asc: bool) -> list:
        """
        Get a list of all organizations
        :return: A list filled dicts
        """
        order_dir = "DESC"

        if order_dir_asc is True:
            order_dir = "ASC"

        if order_column != "name" or order_column != "created":
            order_column = "name"

        if search == "":
            sql = """ SELECT o.id, o.name, o.description, o.created, o.active
                      FROM organizations o
                      ORDER BY """ + order_column + " " + order_dir + ";"  # noqa: S608 # nosec

            async with self.pool.acquire() as con:  # type: Connection
                rows = await con.fetch(sql)
        else:
            search = "%"+search+"%"
            sql = """ SELECT o.id, o.name, o.description, o.created, o.active
                      FROM organizations o
                      WHERE o.name LIKE $1
                      OR o.description LIKE $1
                      OR to_char(o.created, 'YYYY-MM-DD HH24:MI:SS.US') LIKE $1
                      ORDER BY """ + order_column + " " + order_dir + ";"  # noqa: S608 # nosec

            async with self.pool.acquire() as con:  # type: Connection
                rows = await con.fetch(sql, search)

        organizations = []
        for row in rows:
            organization = Organization()
            organization.id = row["id"]
            organization.name = row["name"]
            organization.description = row["description"]
            organization.active = row["active"]
            organization.created = row["created"]

            organizations.append(organization)

        return organizations

    async def update_organization(self, id: UUID, name: str, description: str, active: bool) -> Union[Organization, None]:
        sql = "UPDATE organizations SET name = $1, description = $2, active = $3 WHERE id = $4"

        try:
            async with self.pool.acquire() as con:  # type: Connection
                await con.execute(sql, name, description, active, id)
        except UniqueViolationError as exc:
            logger.debug(exc.__str__())
            logger.warning("Tried to update organization: " + str(id))
            return None

        return await self.get_organization_by_id(id)

    async def delete_organization(self, id: UUID) -> bool:
        success = await self.remove_memberships_from_org(id)
        if not success:
            return False

        # NULL default_organization if were removing default
        try:
            async with self.pool.acquire() as con:
                await con.execute("UPDATE settings SET default_organization = NULL WHERE default_organization = $1", id)
        except Exception:
            return False

        try:
            async with self.pool.acquire() as con:
                await con.execute("DELETE FROM organizations WHERE id = $1", id)
        except Exception:
            return False
        return True
