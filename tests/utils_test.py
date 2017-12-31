from jishaku import utils


def test_reltime():
    for test in [[25, "25 seconds"],
                 [-90, "1 minute, 30 seconds ago"],
                 [60*60*3, "3 hours"],
                 [60*60*24*7, "1 week"]]:
        assert utils.humanize_relative_time(test[0]) == test[1]

test_block = """```py
await asyncio.sleep(3)
```"""


def test_codeblock():
    assert utils.cleanup_codeblock(test_block) == "await asyncio.sleep(3)"
