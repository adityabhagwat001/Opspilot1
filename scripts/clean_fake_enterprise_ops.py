"""
Clean all fake enterprise-ops mock data from the database.
Purges FixProposals, WorkflowFailures, InAppNotifications, ApprovalRequests,
and GitHubEvents referencing dummy enterprise-ops repository.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from app.core.db import AsyncSessionLocal
from app.models.models import ApprovalRequest, FixProposal, WorkflowFailure, InAppNotification, GitHubEvent
from sqlalchemy import select, delete


async def purge_fake_enterprise_ops():
    async with AsyncSessionLocal() as db:
        # 1. Fix Proposals
        p_res = await db.execute(select(FixProposal).where(FixProposal.repo_full_name.like("%enterprise-ops%")))
        proposals = p_res.scalars().all()
        print(f"Purging {len(proposals)} fake FixProposals...")
        for p in proposals:
            await db.delete(p)

        # 2. Workflow Failures
        f_res = await db.execute(select(WorkflowFailure).where(WorkflowFailure.repo_full_name.like("%enterprise-ops%")))
        failures = f_res.scalars().all()
        print(f"Purging {len(failures)} fake WorkflowFailures...")
        for f in failures:
            await db.delete(f)

        # 3. Notifications
        n_res = await db.execute(select(InAppNotification))
        notifs = n_res.scalars().all()
        fake_notifs = [
            n for n in notifs 
            if "enterprise-ops" in (n.message or "") 
            or "enterprise-ops" in (n.title or "")
            or "#38558137" in (n.message or "")
            or "#26776825" in (n.message or "")
        ]
        print(f"Purging {len(fake_notifs)} fake InAppNotifications...")
        for n in fake_notifs:
            await db.delete(n)

        # 4. Approval Requests
        a_res = await db.execute(select(ApprovalRequest))
        apprs = a_res.scalars().all()
        fake_apprs = [
            a for a in apprs 
            if "enterprise-ops" in (a.target_resource or "") 
            or "enterprise-ops" in (a.canonical_action_arguments or "") 
            or "enterprise-ops" in (a.action_summary or "")
        ]
        print(f"Purging {len(fake_apprs)} fake ApprovalRequests...")
        for a in fake_apprs:
            await db.delete(a)

        # 5. GitHub Events
        e_res = await db.execute(select(GitHubEvent).where(GitHubEvent.repo_full_name.like("%enterprise-ops%")))
        events = e_res.scalars().all()
        print(f"Purging {len(events)} fake GitHubEvents...")
        for e in events:
            await db.delete(e)

        await db.commit()
        print("Successfully purged all fake enterprise-ops mock data.")


if __name__ == "__main__":
    asyncio.run(purge_fake_enterprise_ops())
