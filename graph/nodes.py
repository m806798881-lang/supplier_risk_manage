from graph.state import SupplyChainRiskState
from agent.tools.supplier_api import search_suppliers_api, APIError, list_risks_api, list_all_suppliers_api
from rag.main_lcel import hybrid_retriever
from langgraph.types import interrupt, Command
from datetime import datetime, timezone

# ========== 1. 供应商信息 ==========


async def fetch_supplier(state: SupplyChainRiskState) -> dict:
    """根据名称查供应商 ID（复用 Week 3 的 httpx 封装）"""
    name = state['supplier_name']
    print(f'[fetch_supplier] 查询: {name}')
    try:
        suppliers = await search_suppliers_api(name)
    except APIError as e:
        return {'error': f'供应商查询失败：{e}'}

    if not suppliers:
        return {'error': f'未找到供应商：{name}'}
    # 精确匹配优先（Day 5 的策略搬过来）
    exact = [s for s in suppliers if s['name'] == name]
    if len(exact) == 1:
        target = exact[0]
    elif len(suppliers) == 1:
        target = suppliers[0]
    else:
        names = [s['name'] for s in suppliers]
        return {'error': f'{name}不唯一，候选{names}'}

    print(f"[fetch_supplier] 命中: {target['name']} (id={target['id']})")
    return {'supplier_name': target['name'], 'supplier_id': target['id']}


# ========== 2. 风险查询 ==========


async def fetch_risk(state: SupplyChainRiskState) -> dict:
    """根据 ID 查最新风险记录（替换 Day 2 的模拟逻辑）"""
    if state.get('error'):
        return {}
    sid = state.get('supplier_id')
    if not sid:
        return {'error': '缺少 supplier_id，无法查询风险'}

    print(f"[fetch_risk] 查询供应商 {sid} 的风险记录")
    try:
        risks = await list_risks_api(sid)
    except APIError as e:
        return {"error": f"风险查询失败：{e}"}

    if not risks:
        return {"risk_score": 0,
                "risk_level": "unknown",
                "error": "该供应商暂无风险评估记录", }

    latest = risks[0]
    print(f"[fetch_risk] 评分={latest['score']} 等级={latest['level']}")
    return {"risk_score": latest["score"], "risk_level": latest["level"]}


# ========== 3. 深度审查（仅 high） ==========


async def deep_review(state: SupplyChainRiskState) -> dict:
    """高风险供应商的额外审查：拉取全部高风险供应商做横向参考"""
    print(f"[deep_review] {state['supplier_name']} 进入重点审查")
    try:
        all_suppliers = await list_all_suppliers_api()
    except APIError as e:
        return {"deep_reviewed": True, "review_notes": f"横向对比失败：{e}"}

    peer_high_risk = []
    for s in all_suppliers:
        if s["id"] == state.get("supplier_id"):
            continue
        try:
            risks = await list_risks_api(s["id"])
        except APIError:
            continue
        if risks and risks[0]["level"] == "high":
            peer_high_risk.append(s["name"])

    note = "供应商为高风险，建议重点审查合同约束条款并缩短复审周期。"
    if peer_high_risk:
        note += f" 另有 {len(peer_high_risk)} 家高风险供应商：{peer_high_risk[:5]}"
    print(f"[deep_review] {note}")
    return {"deep_reviewed": True, "review_notes": note}

# ========== 4. 政策检索 ==========


async def retrieve_policies(state: SupplyChainRiskState) -> dict:
    """用混合检索器查风控政策（直接调 hybrid_retriever，不调 @tool）"""
    level = state.get("risk_level", "unknown")
    map_risk_level = {'high': '高', 'medium': '中', 'low': '低'}
    query = f"供应商 {map_risk_level[level]} 风险的处理措施和合同约束条款"
    print(f"[retrieve_policies] 检索: {query}")

    docs = await hybrid_retriever.ainvoke(query)
    if not docs:
        return {"policy_context": "未检索到相关政策条款", "policy_sources": []}

    parts, sources = [], []
    for i, doc in enumerate(docs[:3], 1):
        source = doc.metadata.get("source", "未知来源")
        snippet = doc.page_content.replace("\n", " ")[:400]
        parts.append(f"{snippet}")
        sources.append(source)

    print(f"[retrieve_policies] 命中 {len(docs)} 条，来源: {sources}")
    return {
        "policy_context": "\n\n".join(parts),
        "policy_sources": sources, }

# ========== 5. 人工审批（interrupt） ==========


async def human_approval(state: SupplyChainRiskState) -> dict:
    """生成报告前的人工审批（Day 5 的 interrupt 模式）"""
    decision = interrupt({
        "supplier": state.get("supplier_name"),
        "risk_score": state.get("risk_score"),
        "risk_level": state.get("risk_level"),
        "deep_reviewed": state.get("deep_reviewed", False),
        "policy_sources": state.get("policy_sources", []),
        "question": "是否生成最终评估报告？(True/False)",
    })
    print("[human_approval] 暂停，等待人工审批")
    # decision 来自 Command(resume=...)
    # 支持 True/False 或 {"approved": bool, "notes": str}
    if isinstance(decision, dict):
        approved = bool(decision.get("approved"))
        notes = decision.get("notes", "")
    else:
        approved = bool(decision)
        notes = ""

    return {"human_approved": approved,
            "approval_notes": notes,
            "approved_at": datetime.now(timezone.utc).isoformat(), }

# ========== 6. 生成结构化报告 ==========


async def generate_report(state: SupplyChainRiskState) -> dict:
    """拼装最终报告"""

    print("[generate_report] 生成报告")

    if not state.get("human_approved"):
        return {"final_report": "人工审批未通过，报告未生成。"}

    deep = state.get("deep_reviewed", False)
    sources = state.get("policy_sources", [])
    source_list = "\n".join(f"- {s}" for s in sources) if sources else "- 无"

    report = f"""# 供应商风险评估报告

## 一、基础信息
- **供应商**：{state.get('supplier_name')}
- **风险评分**：{state.get('risk_score')}
- **风险等级**：{state.get('risk_level')}

## 二、审查结论
- **是否深度审查**：{"是" if deep else "否（低风险快速通道）"}
- **审查备注**：{state.get('review_notes', '无')}

## 三、政策依据
{state.get('policy_context', '无')}

### 引用来源
{source_list}

## 四、审批记录
- **审批结果**：{"✅ 批准" if state.get('human_approved') else "❌ 拒绝"}
- **审批时间**：{state.get('approved_at', '未知')}
- **审批备注**：{state.get('approval_notes') or '无'}
"""
    return {"final_report": report}
