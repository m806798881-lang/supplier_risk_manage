供应链风险评估 API（FastAPI + SQLAlchemy 2.0 + PostgreSQL）

采用 FastAPI + SQLAlchemy 2.0 异步架构，实现供应商主数据与风险记录的一对多关系建模，支持异步 CRUD。

基于 JWT + OAuth2 Password Flow 实现认证，使用 bcrypt 哈希存储密码，包含随机盐与 cost factor 防暴力破解。

通过依赖工厂模式实现 RBAC 权限控制：管理员独占删除权限，分析师可读可写，审计员只读。

基于 created_by 字段实现数据级权限隔离：分析师只能查看自己创建的供应商，管理层可看全量。

使用 Pydantic + response_model 实现请求校验与响应字段白名单，防止敏感字段泄露。

Docker Compose 一键启动 PostgreSQL + API，支持开发（SQLite）/ 生产（PostgreSQL）双模式切换。
