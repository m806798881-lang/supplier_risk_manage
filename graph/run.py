from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from graph.builder import _build_graph
from langgraph.types import Command
import argparse
import asyncio

CHECKPOINT_DB = "graph/checkpoints.db"


async def start(supplier_name: str, thread_id: str):
    """第一次运行：跑到 interrupt 就停"""
    async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB) as saver:
        await saver.setup()
        graph = _build_graph(saver)
        print(graph.get_graph().draw_mermaid())
        config = {"configurable": {"thread_id": thread_id}}

        print(f"\n{'='*60}\n【启动】{supplier_name} | thread={thread_id}")

        result = await graph.ainvoke({"supplier_name": supplier_name}, config)
        # 检查是否停在了 interrupt
        snapshot = await graph.aget_state(config)
        if snapshot.next:
            print(f"\n⏸ 暂停于: {snapshot.next}")
            print(f"   待审批内容: {snapshot.values} ")
            print(
                f"   请运行：python -m graph.run resume --thread {thread_id} --approve")
        elif result.get("error"):
            print(f"\n❌ 流程终止：{result['error']}")
        else:
            print(f"\n✅ 已完成：\n{result.get('final_report')}")


async def resume(thread_id: str, approve: bool, notes: str):
    """第二次运行：从检查点恢复"""
    async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB) as saver:
        await saver.setup()
        graph = _build_graph(saver)

        config = {"configurable": {"thread_id": thread_id}}
        print(f"\n{'='*60}\n【恢复】thread={thread_id} | 审批={approve}")

        decision = {"approved": approve, "notes": notes} if notes else approve
        result = await graph.ainvoke(Command(resume=decision), config)

        print(f"\n✅ 最终报告：\n{result.get('final_report')}")


async def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_start = sub.add_parser("start", help="启动新工作流")
    p_start.add_argument('--thread', required=True)
    p_start.add_argument("--supplier", required=True)

    p_resume = sub.add_parser("resume", help="从检查点恢复")
    p_resume.add_argument("--thread", required=True)
    p_resume.add_argument("--approve", action="store_true")
    p_resume.add_argument("--notes", default="")

    args = parser.parse_args()

    if args.cmd == "start":
        await start(args.supplier, args.thread)
    else:
        await resume(args.thread, args.approve, args.notes)

if __name__ == "__main__":
    asyncio.run(main())
