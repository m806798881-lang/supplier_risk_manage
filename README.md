供应链风险评估 API（FastAPI + SQLAlchemy 2.0 + PostgreSQL）

采用 FastAPI + SQLAlchemy 2.0 异步架构，实现供应商主数据与风险记录的一对多关系建模，支持异步 CRUD。

基于 JWT + OAuth2 Password Flow 实现认证，使用 bcrypt 哈希存储密码，包含随机盐与 cost factor 防暴力破解。

通过依赖工厂模式实现 RBAC 权限控制：管理员独占删除权限，分析师可读可写，审计员只读。

基于 created_by 字段实现数据级权限隔离：分析师只能查看自己创建的供应商，管理层可看全量。

使用 Pydantic + response_model 实现请求校验与响应字段白名单，防止敏感字段泄露。

Docker Compose 一键启动 PostgreSQL + API，支持开发（SQLite）/ 生产（PostgreSQL）双模式切换。

## 为什么风控工作流需要 LangGraph 而不是单个 Agent？

第三、四周我们用 `create_react_agent` 构建了"能查数据库、能查文档"的 Agent，
它适合开放式问答。但风控评估场景有其特殊性：

### 1. 流程是**确定的**，不该由模型决定顺序

风控审批必须遵循"查信息 → 查风险 → 检索政策 → 人工审批 → 生成报告"
的固定顺序。`create_react_agent` 让模型自由选择工具和顺序，每次执行可能不同，
不符合审计要求。LangGraph 用 `add_edge` 把顺序写死，每次执行路径一致。

### 2. 条件路由需要**代码级**保证，不能依赖 Prompt

"高风险必须深度审查"是合规要求，不能靠 Prompt 说"请你记得深度审查"。
LangGraph 的 `add_conditional_edges` 用代码保证：评分 ≥ 70 时**只能**走
`deep_review` 分支，模型无法绕过。

### 3. 需要**可中断、可恢复**

人工审批意味着流程可能暂停数小时甚至数天。LangGraph 的 `interrupt` +
持久化 checkpointer（SqliteSaver）保证：暂停后关闭进程，几小时后用同一
`thread_id` 恢复，从断点继续，前置步骤不重跑。

### 4. 状态**显式可见**

LangGraph 的 `State` 是一个显式的 TypedDict，每一步的中间结果都记录在案。
审计时可以直接看 `snapshot.values`，而不需要从 Agent 的对话日志里翻找。

### 结论

**Agent 适合开放式探索，LangGraph 适合确定性流程。**
风控评估是"流程优先、模型辅助"的场景——模型只在报告润色、政策摘要
等局部环节出现，主干道由 Graph 控制。这就是为什么我们把 Week 3/4 的
Agent 能力"拆解"进 LangGraph 节点：**保留模型能力，收回流程控制权**。
