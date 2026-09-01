"""存储层实现:SQLite(SQLAlchemy)。

- database.py:引擎 / 会话工厂 / 建表
- sqlite.py:Storage 接口的 SQLAlchemy 实现

后续如需迁移到其他数据库,新增一个 Storage 实现即可。
"""
