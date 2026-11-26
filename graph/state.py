from typing import TypedDict, Optional


class SupplyChainRiskState(TypedDict, total=False):
    supplier_name: str
    # fetch_supplier 产出
    supplier_id: Optional[int]
    # fetch_risk 产出
    risk_score: Optional[float]
    risk_level: Optional[str]     # "low" / "medium" / "high"
    # deep_review 产出
    deep_reviewed: bool | None
    review_notes: str | None
    # retrieve_policies 产出
    policy_context: str
    policy_sources: list[str]
    # human_approval 产出
    human_approved: bool | None
    approval_notes: str
    approved_at: str | None
    # generate_report 产出
    final_report: str | None

    # 错误传播
    error: Optional[str]
    # 追加而不是覆盖，可以把它改成 Annotated[list[str], operator.add]
    # policy_context: Optional[str]
    # human_approved: Optional[bool]
