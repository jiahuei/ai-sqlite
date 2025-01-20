from itertools import zip_longest
from typing import Sequence

import libsql_client
from libsql_client import InArgs, InStatement, ResultSet

from aisql.config import ENV_CONFIG


class GenerativeTableCore:
    def __init__(self, table_name: str, *, url: str = ENV_CONFIG.db_path):
        self.table_name = table_name
        self.url = url
        self._client = libsql_client.create_client(url)
        self.client = None

    async def __aenter__(self):
        self.client = await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._client.__aexit__(exc_type, exc_value, traceback)
        self.client = None

    async def execute(self, stmt: InStatement, args: InArgs = None) -> ResultSet:
        return await self.client.execute(stmt, args)

    async def batch(self, stmts: list[InStatement]) -> list[ResultSet]:
        return await self.client.batch(stmts)

    async def create_table(self) -> list[ResultSet]:
        return await self.client.batch(
            [
                f"CREATE TABLE {self.table_name}(id INTEGER PRIMARY KEY, Title TEXT, Text TEXT, Page INTEGER DEFAULT NULL, 'File ID' TEXT DEFAULT NULL)",
                # https://www.sqlite.org/fts5.html#external_content_tables
                (
                    f"CREATE VIRTUAL TABLE {self.table_name}_fts USING fts5("
                    f"Title, Text, content='{self.table_name}', "
                    "content_rowid='id', tokenize ='snowball english spanish russian simple unicode61 remove_diacritics 1')"
                ),
                f"""CREATE TRIGGER {self.table_name}_ai AFTER INSERT ON {self.table_name} BEGIN
  INSERT INTO {self.table_name}_fts(rowid, Title, Text) VALUES (new.id, new.Title, new.Text);
END;""",
                f"""CREATE TRIGGER {self.table_name}_ad AFTER DELETE ON {self.table_name} BEGIN
  INSERT INTO {self.table_name}_fts({self.table_name}_fts, rowid, Title, Text) VALUES('delete', old.id, old.Title, old.Text);
END;""",
                f"""CREATE TRIGGER {self.table_name}_au AFTER UPDATE ON {self.table_name} BEGIN
  INSERT INTO {self.table_name}_fts({self.table_name}_fts, rowid, Title, Text) VALUES('delete', old.id, old.Title, old.Text);
  INSERT INTO {self.table_name}_fts(rowid, Title, Text) VALUES (new.id, new.Title, new.Text);
END;""",
            ]
        )

    async def drop_table(self) -> list[ResultSet]:
        return await self.client.batch(
            [
                f"DROP TABLE IF EXISTS {self.table_name}",
                f"DROP TABLE IF EXISTS {self.table_name}_fts",
            ]
        )

    async def add_rows(
        self,
        titles: Sequence[str],
        texts: Sequence[str] | None = None,
        pages: Sequence[int] | None = None,
        file_ids: Sequence[str] | None = None,
    ) -> ResultSet:
        texts = [] if texts is None else texts
        pages = [] if pages is None else pages
        file_ids = [] if file_ids is None else file_ids
        values = ", ".join(
            f"('{title}', '{text}', {page}, '{file_id}')"
            for title, text, page, file_id in zip_longest(
                titles, texts, pages, file_ids, fillvalue="NULL"
            )
        )
        return await self.client.execute(
            f"INSERT INTO {self.table_name}(Title, Text, Page, 'File ID') VALUES {values};"
        )

    async def fts_search(self, query: str) -> ResultSet:
        return await self.client.execute(
            f"SELECT *, rank FROM {self.table_name}_fts WHERE {self.table_name}_fts MATCH ? ORDER BY rank ASC;",
            (query,),
        )
