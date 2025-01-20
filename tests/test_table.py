from aisql.db import GenerativeTableCore, ResultSet

TABLE_NAME = "test"


async def test_execute_batch():
    async with GenerativeTableCore(TABLE_NAME) as client:
        await client.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")
        await client.execute(
            f"CREATE TABLE {TABLE_NAME}(id INTEGER PRIMARY KEY, Title TEXT DEFAULT NULL);"
        )
        try:
            await client.batch(
                [
                    f"ALTER TABLE {TABLE_NAME} ADD COLUMN sold INTEGER DEFAULT FALSE;",
                    f"INSERT INTO {TABLE_NAME}_xx(Title) VALUES ('no');",  # Should fail and rolled-back
                ]
            )
        except Exception:
            pass
        result = await client.execute(f"INSERT INTO {TABLE_NAME}(Title) VALUES (?);", ("yes",))
        assert isinstance(result, ResultSet)
        result = await client.execute(f"SELECT * from {TABLE_NAME}")
        assert len(result.columns) == 2
        assert len(result.rows) == 1
        # Insert new column
        await client.batch(
            [
                f"ALTER TABLE {TABLE_NAME} ADD COLUMN sold INTEGER DEFAULT FALSE;",
                f"INSERT INTO {TABLE_NAME}(Title) VALUES ('ok');",
            ]
        )
        result = await client.execute(f"SELECT * from {TABLE_NAME}")
        assert len(result.columns) == 3
        assert len(result.rows) == 2


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_execute_batch())
