# TO DO List after 1.6.0

- [ ] Unit tests for important online feeds.
- [X] Unit tests for parallel execution.
- [X] Unit tests for intervals (using `freezegun`).
- [X] Package test runner as extra.
- [ ] Make requests module obligatory, remove cURL code and all those awkward unit tests for that.
- [ ] Proper class structure for main module
- [x] ~~Use `asyncio` instead of threads?~~ `requests` doesn't really support `asyncio`. 
      Maybe in a future version, we'll use `aiohttp`. But for now, I don't want to re-write.
- [ ] Replace `str.format(...)` with format strings
- [ ] Experiment with an HTTP server for tests (e.g. `pytest-httpserver`) or properly  
      mocking `requests` (e.g. `requests-mock`) instead of local files.
- [ ] ...
