from langchain_core.tools import tool
import httpx

from agent.tools.supplier_api import APIError, search_suppliers_api, list_all_suppliers_api, list_risks_api


def _fromat_risk_line(supplier_name: str, risk: dict) -> str:
    return (
        f"供应商【{supplier_name}】"
        f"最新风险等级：{risk['level']},"
        f"评分：{risk['score']},"
        f"评估人：{risk['assessor']},"
        f"评估时间：{risk['assessed_at']}。"
    )


@tool
async def list_high_risk_suppliers() -> str:
    """列出当前所有风险等级为 high 的供应商，返回名称、评分和最近评估信息。

    无需参数。当用户问“哪些供应商风险高”“高风险供应商有哪些”时使用。
    本工具会拉取所有供应商，逐个查询其最新风险记录，只返回 level=high 的。"""
    try:
        suppliers = await list_all_suppliers_api()
    except APIError as e:
        return f'获取供应商列表失败：{e}'
    except httpx.HTTPError as e:
        return f'获取供应商列表时网络异常：{e}'

    if not suppliers:
        return '系统中暂无供应商数据。'

    high_risk: list[tuple[str, dict]] = []
    for s in suppliers:
        try:
            risks = await list_risks_api(s['id'])
        except (APIError, httpx.HTTPError):
            continue  # 单个供应商查失败不影响整体
        if risks and risks[0]['level'] == 'high':
            high_risk.append((s['name'], risks[0]))

    if not high_risk:
        return '当前没有高风险供应商。'

    lines = [f"当前有 {len(high_risk)} 家高风险供应商："]
    for i, (name, risk) in enumerate(high_risk, 1):
        lines.append(
            f'{i}. {name} -评分{risk['score']}, '
            f'评估人 {risk['assessor']}，评估时间 {risk['assessed_at']}'
        )
    return '\n'.join(lines)


@tool
async def get_supplier_risk(supplier_name: str) -> str:
    """
    根据供应商的**完整名称**查询其最新风险等级和评分。

    如果名称不完整或不确定，请先用工具中的 search_suppliers 确认唯一匹配。
    如果名称对应多个供应商，本工具会返回候选列表而不会猜测。
    参数：
        supplier_name:供应商的完整名称，例如‘顺捷物流有限公司’。
    返回：
        一段文本,包含该供应商的风险等级(low/medium/high)和评分。
    """
    try:
        # supplier = await fetch_supplier_risk(supplier_name)
        # supplier_id = supplier['id']

        suppliers = await search_suppliers_api(supplier_name)
        if not suppliers:
            return f'未找到名为『{supplier_name}』的供应商，请确认名称是否正确。'

        # 2. 精确匹配优先（避免"顺捷"命中"顺捷物流"和"顺捷运输"时误选）
        exact = [s for s in suppliers if s['name'] == supplier_name]
        if len(exact) == 1:
            target = exact[0]
        elif len(suppliers) == 1:
            target = suppliers[0]
        else:
            names = [f'- {s['name']}' for s in suppliers]
            return f'名称『{supplier_name}』匹配到多个供应商，无法确定具体是哪一家：\n'+'\n'.join(names)+'\n请让用户确认具体是哪一,或使用更精确的名称。'

        # 3. 唯一确定了，查风险
        risks = await list_risks_api(target['id'])
        if not risks:
            return f'供应商【{supplier_name}】暂无风险评估记录'
        return _fromat_risk_line(target['name'], risks[0])

    except APIError as e:
        return f"查询供应商风险失败：{e}"

    except httpx.HTTPError as e:
        return f"查询供应商风险时网络异常：{e}"


@tool
async def search_suppliers(keyword: str) -> str:
    """
    按关键词模糊搜索供应商，返回匹配的供应商名称列表。
    当用户提供的供应商名称不完整、模糊，或你不确定是否存在这家供应商时，
    使用此工具先获取候选列表。搜索结果可能是 0 个、1 个或多个。

    参数：
        keyword:搜索关键词，可以是供应商名称的一部分，例如‘顺捷’。
    返回：
        如果找到唯一匹配，则返回该供应商完整名称。
        如果找到多个匹配，返回编号列表。
        如果无匹配，返回"未找到"提示。
"""
    try:
        suppliers = await search_suppliers_api(keyword)

    except Exception as e:
        return f'查找供应商时出错{e}'

    if not suppliers:
        return f'未找到名称包含『{keyword}』的供应商。'
    if len(suppliers) == 1:
        return f'找到唯一匹配的供应商：{suppliers[0]['name']}'
    names = [f'{i+1}. {item['name']}'for i, item in enumerate(suppliers)]
    return f'共找到{len(suppliers)}个匹配『{keyword}』的供应商: \n' + '\n'.join(names)
