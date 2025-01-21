from aisql.db import GenerativeTableCore

TABLE_NAME = "test"


async def test_en_one_term():
    async with GenerativeTableCore(TABLE_NAME) as client:
        await client.drop_table()
        await client.create_table()
        data = ["Hello", "Hello running", "Hello你好", "Hello你好 running", "Hello 你好 running"]
        await client.add_rows(data)
        # Typical
        results = await client.fts_search("hello")
        assert len(results.rows) == len(data)
        # Stemmed
        results = await client.fts_search("run")
        assert len(results.rows) == 3
        # Invalid
        results = await client.fts_search("runn")
        assert len(results.rows) == 0


async def test_en_one_term_multicolumn():
    async with GenerativeTableCore(TABLE_NAME) as client:
        await client.drop_table()
        await client.create_table()
        titles = ["Hello", ""]
        texts = ["", "Hello你好"]
        await client.add_rows(titles, texts)
        # Search
        results = await client.fts_search("hello")
        assert len(results.rows) == len(titles)
        results = await client.fts_search("你好")
        assert len(results.rows) == 1


async def test_en_one_term_unexpected():
    async with GenerativeTableCore(TABLE_NAME) as client:
        await client.drop_table()
        await client.create_table()
        data = ["Hello", "Hello runner"]
        await client.add_rows(data)
        # Stemmer failure
        results = await client.fts_search("hell")
        assert len(results.rows) == len(data)
        # Stemmer failure
        results = await client.fts_search("run")
        assert len(results.rows) == 0


async def test_en_one_term_rank():
    async with GenerativeTableCore(TABLE_NAME) as client:
        await client.drop_table()
        await client.create_table()
        data = ["Hello running", "hello", "Hello你好", "Hello你好 running", "Hello 你好 running"]
        await client.add_rows(data)
        # Search
        results = await client.fts_search("hello")
        assert len(results.rows) == len(data)
        assert results.rows[0][0] == 2
        assert results.rows[0][1] == data[1]


async def test_en_two_terms():
    async with GenerativeTableCore(TABLE_NAME) as client:
        await client.drop_table()
        await client.create_table()
        titles = ["Hello there", "there hello", "hello", "there"]
        await client.add_rows(titles)
        # Search
        results = await client.fts_search("hello there")
        assert len(results.rows) == 2
        results = await client.fts_search("there hello")
        assert len(results.rows) == 2
        results = await client.fts_search("hello OR there")
        assert len(results.rows) == len(titles)


async def test_en_two_terms_multicolumn():
    async with GenerativeTableCore(TABLE_NAME) as client:
        await client.drop_table()
        await client.create_table()
        titles = ["Hello there", "", "Hello"]
        texts = ["", "Hello there", "there"]
        await client.add_rows(titles, texts)
        # Search
        results = await client.fts_search("hello there")
        assert len(results.rows) == len(titles)


async def test_en_two_terms_rank():
    async with GenerativeTableCore(TABLE_NAME) as client:
        await client.drop_table()
        await client.create_table()
        data = ["hello", "running", "Hello 你好 running"]
        await client.add_rows(data)
        # Search
        results = await client.fts_search("hello OR run")
        assert len(results.rows) == len(data)
        assert results.rows[0][0] == 3
        assert results.rows[0][1] == data[-1]


async def test_cn_two_terms():
    async with GenerativeTableCore(TABLE_NAME) as client:
        await client.drop_table()
        await client.create_table()
        titles = ["你好", "你 好", "好你", "好 你", "你", "好"]
        await client.add_rows(titles)
        # Search
        results = await client.fts_search("你好")
        assert len(results.rows) == 2
        assert results.rows[0][0] == 1
        assert results.rows[1][0] == 2
        assert results.rows[0][1] == titles[0]
        assert results.rows[1][1] == titles[1]
        results = await client.fts_search("你 好")
        assert len(results.rows) == 4
        results = await client.fts_search("你 OR 好")
        assert len(results.rows) == len(titles)
        # # Pinyin
        # results = await client.fts_search("ni hao")
        # print(results.rows)
        # assert len(results.rows) == 2
        # assert results.rows[0][0] == titles[0]
        # assert results.rows[1][0] == titles[1]


async def test_cn_two_terms_multicolumn():
    async with GenerativeTableCore(TABLE_NAME) as client:
        await client.drop_table()
        await client.create_table()
        titles = ["你好", "你"]
        texts = ["", "好"]
        await client.add_rows(titles, texts)
        # Search
        results = await client.fts_search("你好")
        assert len(results.rows) == 1
        results = await client.fts_search("你 好")
        assert len(results.rows) == 2


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_cn_two_terms())
