# Database Queries

Contributor: [Xuanhe Zhou](https://github.com/zhouxh19)

### API Functions

- *select_database_data*: Fetch the query results from a database instance
- *rewrite_sql*: transform a sql query into an semantic-equivalent but execution-efficient sql


### Setup

1. Finish the configurations in [main readme](https://github.com/OpenBMB/BMTools/blob/main/README.md)

2. Rename config.ini.template into my_config.ini

3. Add database settings in my_config.ini, e.g.,

```bash
    [{db_system}]
    host = 127.0.0.1
    port = 5432
    user = postgres
    password = postgres
    dbname = postgres
```

Note. {db_system} must match with that in ./api.py

4. Run the test.py to test the tool