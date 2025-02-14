from itertools import zip_longest
from typing import Sequence

import libsql_client
from libsql_client import InArgs, InStatement, ResultSet

from aisql.config import ENV_CONFIG


class GenerativeTableCore:
    VECTOR_MAP = {
        "float64": "F64_BLOB",
        "float32": "F32_BLOB",
        "float16": "F16_BLOB",
        "bfloat16": "FB16_BLOB",
        "float8": "F8_BLOB",
        "float1": "F1BIT_BLOB",
        "binary": "F1BIT_BLOB",
    }

    def __init__(
        self,
        table_name: str,
        *,
        embedding_dim: int = 128,
        embedding_precision: str = "float16",
        url: str = ENV_CONFIG.db_path,
    ):
        self.table_name = table_name
        self.embedding_dim = embedding_dim
        self.embedding_precision = self.VECTOR_MAP.get(embedding_precision, "F32_BLOB")
        self.url = url
        self._client = libsql_client.create_client(url)
        self.client = None

    async def __aenter__(self):
        self.client = await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._client.__aexit__(exc_type, exc_value, traceback)
        self.client = None

    @property
    def embedding_type(self) -> str:
        return f"{self.embedding_precision}({self.embedding_dim})"

    async def execute(self, stmt: InStatement, args: InArgs = None) -> ResultSet:
        return await self.client.execute(stmt, args)

    async def batch(self, stmts: list[InStatement]) -> list[ResultSet]:
        return await self.client.batch(stmts)

    async def create_table(self) -> list[ResultSet]:
        return await self.client.batch(
            [
                f"""
                CREATE TABLE {self.table_name}(
                    id          INTEGER PRIMARY KEY,
                    Title       TEXT,
                    Text        TEXT,
                    Title_Embed {self.embedding_type},
                    Text_Embed  {self.embedding_type},
                    Page        INTEGER DEFAULT NULL,
                    File_ID     TEXT    DEFAULT NULL
                )
                """,
                ### --- Vector Search --- ###
                f"""
                CREATE INDEX {self.table_name}_Title_Embed_Idx ON {self.table_name} (libsql_vector_idx(Title_Embed));
                """,
                f"""
                CREATE INDEX {self.table_name}_Text_Embed_Idx ON {self.table_name} (libsql_vector_idx(Text_Embed));
                """,
                ### --- Full Text Search --- ###
                # https://www.sqlite.org/fts5.html#external_content_tables
                f"""
                CREATE VIRTUAL TABLE {self.table_name}_fts USING fts5(
                    Title, Text,
                    content='{self.table_name}', content_rowid='id',
                    tokenize ='snowball english spanish russian simple unicode61 remove_diacritics 1'
                )
                """,
                f"""
                CREATE TRIGGER {self.table_name}_ai AFTER INSERT ON {self.table_name} BEGIN
                    INSERT INTO {self.table_name}_fts(rowid, Title, Text) VALUES (new.id, new.Title, new.Text);
                END;
                """,
                f"""
                CREATE TRIGGER {self.table_name}_ad AFTER DELETE ON {self.table_name} BEGIN
                    INSERT INTO {self.table_name}_fts({self.table_name}_fts, rowid, Title, Text) VALUES('delete', old.id, old.Title, old.Text);
                END;
                """,
                f"""
                CREATE TRIGGER {self.table_name}_au AFTER UPDATE ON {self.table_name} BEGIN
                    INSERT INTO {self.table_name}_fts({self.table_name}_fts, rowid, Title, Text) VALUES('delete', old.id, old.Title, old.Text);
                    INSERT INTO {self.table_name}_fts(rowid, Title, Text) VALUES (new.id, new.Title, new.Text);
                END;
                """,
            ]
        )

    async def drop_table(self) -> list[ResultSet]:
        return await self.client.batch(
            [
                f"DROP TABLE IF EXISTS {self.table_name}",
                f"DROP TABLE IF EXISTS {self.table_name}_fts",
                f"DROP INDEX IF EXISTS {self.table_name}_Title_Embed_Idx;",
                f"DROP INDEX IF EXISTS {self.table_name}_Text_Embed_Idx;",
            ]
        )

    async def add_row(
        self,
        title: str | None,
        text: str | None = None,
        title_embedding: Sequence[float] | None = None,
        text_embedding: Sequence[float] | None = None,
        page: int | None = None,
        file_id: str | None = None,
    ) -> ResultSet:
        return await self.client.execute(
            f"INSERT INTO {self.table_name}(Title, Text, Title_Embed, Text_Embed, Page, File_ID) VALUES (?, ?, ?, ?, ?, ?);",
            (title, text, title_embedding, text_embedding, page, file_id),
        )

    @staticmethod
    def _process_value(x) -> str:
        if x is None:
            return "NULL"
        elif isinstance(x, str):
            return f"'{x}'"
        elif isinstance(x, bool):
            x = int(x)
        return str(x)

    async def add_rows(
        self,
        titles: Sequence[str | None],
        texts: Sequence[str | None] | None = None,
        title_embeddings: Sequence[Sequence[float] | None] | None = None,
        text_embeddings: Sequence[Sequence[float] | None] | None = None,
        pages: Sequence[int | None] | None = None,
        file_ids: Sequence[str | None] | None = None,
    ) -> ResultSet:
        titles = map(self._process_value, titles)
        texts = [] if texts is None else map(self._process_value, texts)
        title_embeddings = (
            [] if title_embeddings is None else map(self._process_value, title_embeddings)
        )
        text_embeddings = (
            [] if text_embeddings is None else map(self._process_value, text_embeddings)
        )
        pages = [] if pages is None else map(self._process_value, pages)
        file_ids = [] if file_ids is None else map(self._process_value, file_ids)
        values = ", ".join(
            f"({title}, {text}, {title_embed}, {text_embed}, {page}, {file_id})"
            for title, text, title_embed, text_embed, page, file_id in zip_longest(
                titles, texts, title_embeddings, text_embeddings, pages, file_ids, fillvalue="NULL"
            )
        )
        return await self.client.execute(
            f"INSERT INTO {self.table_name}(Title, Text, Title_Embed, Text_Embed, Page, File_ID) VALUES {values};"
        )

    async def fts_search(self, query: str) -> ResultSet:
        return await self.client.execute(
            f"""
            SELECT t.*, fts.rank
            FROM {self.table_name} AS t
            JOIN {self.table_name}_fts AS fts ON t.id = fts.rowid
            WHERE {self.table_name}_fts MATCH ?
            ORDER BY fts.rank ASC;
            """,
            (query,),
        )
