"""
Cron subcommand for hermes CLI.

Handles standalone cron management commands like list, create, edit,
pause/resume/run/remove, status, and tick.
"""

import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from hermes_cli.colors import Colors, color
from hermes_cli.i18n import t


def _normalize_skills(single_skill=None, skills: Optional[Iterable[str]] = None) -> Optional[List[str]]:
    if skills is None:
        if single_skill is None:
            return None
        raw_items = [single_skill]
    else:
        raw_items = list(skills)

    normalized: List[str] = []
    for item in raw_items:
        text = str(item or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _cron_api(**kwargs):
    from tools.cronjob_tools import cronjob as cronjob_tool

    return json.loads(cronjob_tool(**kwargs))


def cron_list(show_all: bool = False):
    """List all scheduled jobs."""
    from cron.jobs import list_jobs

    jobs = list_jobs(include_disabled=show_all)

    if not jobs:
        print(color(t("cron.no_jobs"), Colors.DIM))
        print(color(t("cron.create_one"), Colors.DIM))
        return

    print()
    print(color("┌─────────────────────────────────────────────────────────────────────────┐", Colors.CYAN))
    print(color(f"│                         {t('cron.scheduled_jobs'):<47}│", Colors.CYAN))
    print(color("└─────────────────────────────────────────────────────────────────────────┘", Colors.CYAN))
    print()

    for job in jobs:
        job_id = job.get("id", "?")
        name = job.get("name", "(unnamed)")
        schedule = job.get("schedule_display", job.get("schedule", {}).get("value", "?"))
        state = job.get("state", "scheduled" if job.get("enabled", True) else "paused")
        next_run = job.get("next_run_at", "?")

        repeat_info = job.get("repeat", {})
        repeat_times = repeat_info.get("times")
        repeat_completed = repeat_info.get("completed", 0)
        repeat_str = f"{repeat_completed}/{repeat_times}" if repeat_times else "∞"

        deliver = job.get("deliver", ["local"])
        if isinstance(deliver, str):
            deliver = [deliver]
        deliver_str = ", ".join(deliver)

        skills = job.get("skills") or ([job["skill"]] if job.get("skill") else [])
        if state == "paused":
            status = color(f"[{t('cron.state_paused')}]", Colors.YELLOW)
        elif state == "completed":
            status = color(f"[{t('cron.state_completed')}]", Colors.BLUE)
        elif job.get("enabled", True):
            status = color(f"[{t('cron.state_active')}]", Colors.GREEN)
        else:
            status = color(f"[{t('cron.state_disabled')}]", Colors.RED)

        print(f"  {color(job_id, Colors.YELLOW)} {status}")
        print(f"    {t('cron.name')}:      {name}")
        print(f"    {t('cron.schedule')}:  {schedule}")
        print(f"    {t('cron.repeat')}:    {repeat_str}")
        print(f"    {t('cron.next_run')}:  {next_run}")
        print(f"    {t('cron.deliver')}:   {deliver_str}")
        if skills:
            print(f"    {t('cron.skills')}:    {', '.join(skills)}")
        script = job.get("script")
        if script:
            print(f"    {t('cron.script')}:    {script}")
        if job.get("no_agent"):
            print(f"    Mode:      {color('no-agent', Colors.DIM)} (script stdout delivered directly)")
        workdir = job.get("workdir")
        if workdir:
            print(f"    Workdir:   {workdir}")

        # Execution history
        last_status = job.get("last_status")
        if last_status:
            last_run = job.get("last_run_at", "?")
            if last_status == "ok":
                status_display = color("ok", Colors.GREEN)
            else:
                status_display = color(f"{last_status}: {job.get('last_error', '?')}", Colors.RED)
            print(f"    {t('cron.last_run')}:  {last_run}  {status_display}")

        delivery_err = job.get("last_delivery_error")
        if delivery_err:
            print(f"    {color('⚠ ' + t('cron.delivery_failed'), Colors.YELLOW)} {delivery_err}")

        print()

    from hermes_cli.gateway import find_gateway_pids
    if not find_gateway_pids():
        print(color(f"  ⚠  {t('cron.gateway_not_running')}", Colors.YELLOW))
        print(color(f"     {t('cron.start_with')} hermes gateway install", Colors.DIM))
        print(color("                    sudo hermes gateway install --system  # Linux servers", Colors.DIM))
        print()


def cron_tick():
    """Run due jobs once and exit."""
    from cron.scheduler import tick
    tick(verbose=True)


def cron_status():
    """Show cron execution status."""
    from cron.jobs import list_jobs
    from hermes_cli.gateway import find_gateway_pids

    print()

    pids = find_gateway_pids()
    if pids:
        print(color(f"✓ {t('cron.gateway_running_auto')}", Colors.GREEN))
        print(f"  PID: {', '.join(map(str, pids))}")
    else:
        print(color(f"✗ {t('cron.gateway_not_running_auto')}", Colors.RED))
        print()
        print(f"  {t('cron.to_enable_automatic')}")
        print("    hermes gateway install    # Install as a user service")
        print("    sudo hermes gateway install --system  # Linux servers: boot-time system service")
        print("    hermes gateway            # Or run in foreground")

    print()

    jobs = list_jobs(include_disabled=False)
    if jobs:
        next_runs = [j.get("next_run_at") for j in jobs if j.get("next_run_at")]
        print(f"  {t('cron.active_jobs', count=len(jobs))}")
        if next_runs:
            print(f"  {t('cron.next_run')}: {min(next_runs)}")
    else:
        print(f"  {t('cron.no_active_jobs')}")

    print()


def cron_create(args):
    result = _cron_api(
        action="create",
        schedule=args.schedule,
        prompt=args.prompt,
        name=getattr(args, "name", None),
        deliver=getattr(args, "deliver", None),
        repeat=getattr(args, "repeat", None),
        skill=getattr(args, "skill", None),
        skills=_normalize_skills(getattr(args, "skill", None), getattr(args, "skills", None)),
        script=getattr(args, "script", None),
        workdir=getattr(args, "workdir", None),
        no_agent=getattr(args, "no_agent", False) or None,
    )
    if not result.get("success"):
        print(color(t("cron.failed_create", error=result.get("error", t("errors.unknown"))), Colors.RED))
        return 1
    print(color(t("cron.created_job", job_id=result["job_id"]), Colors.GREEN))
    print(f"  {t('cron.name')}: {result['name']}")
    print(f"  {t('cron.schedule')}: {result['schedule']}")
    if result.get("skills"):
        print(f"  {t('cron.skills')}: {', '.join(result['skills'])}")
    job_data = result.get("job", {})
    if job_data.get("script"):
        print(f"  {t('cron.script')}: {job_data['script']}")
    if job_data.get("no_agent"):
        print("  Mode: no-agent (script stdout delivered directly)")
    print(f"  {t('cron.next_run')}: {result['next_run_at']}")
    if job_data.get("workdir"):
        print(f"  Workdir: {job_data['workdir']}")
    return 0


def cron_edit(args):
    from cron.jobs import get_job

    job = get_job(args.job_id)
    if not job:
        print(color(t("cron.job_not_found", job_id=args.job_id), Colors.RED))
        return 1

    existing_skills = list(job.get("skills") or ([] if not job.get("skill") else [job.get("skill")]))
    replacement_skills = _normalize_skills(getattr(args, "skill", None), getattr(args, "skills", None))
    add_skills = _normalize_skills(None, getattr(args, "add_skills", None)) or []
    remove_skills = set(_normalize_skills(None, getattr(args, "remove_skills", None)) or [])

    final_skills = None
    if getattr(args, "clear_skills", False):
        final_skills = []
    elif replacement_skills is not None:
        final_skills = replacement_skills
    elif add_skills or remove_skills:
        final_skills = [skill for skill in existing_skills if skill not in remove_skills]
        for skill in add_skills:
            if skill not in final_skills:
                final_skills.append(skill)

    result = _cron_api(
        action="update",
        job_id=args.job_id,
        schedule=getattr(args, "schedule", None),
        prompt=getattr(args, "prompt", None),
        name=getattr(args, "name", None),
        deliver=getattr(args, "deliver", None),
        repeat=getattr(args, "repeat", None),
        skills=final_skills,
        script=getattr(args, "script", None),
        workdir=getattr(args, "workdir", None),
        no_agent=getattr(args, "no_agent", None),
    )
    if not result.get("success"):
        print(color(t("cron.failed_update", error=result.get("error", t("errors.unknown"))), Colors.RED))
        return 1

    updated = result["job"]
    print(color(t("cron.updated_job", job_id=updated["job_id"]), Colors.GREEN))
    print(f"  {t('cron.name')}: {updated['name']}")
    print(f"  {t('cron.schedule')}: {updated['schedule']}")
    if updated.get("skills"):
        print(f"  {t('cron.skills')}: {', '.join(updated['skills'])}")
    else:
        print(f"  {t('cron.skills')}: {t('cron.skills_none')}")
    if updated.get("script"):
        print(f"  {t('cron.script')}: {updated['script']}")
    if updated.get("no_agent"):
        print("  Mode: no-agent (script stdout delivered directly)")
    if updated.get("workdir"):
        print(f"  Workdir: {updated['workdir']}")
    return 0


def _job_action(action: str, job_id: str, success_verb: str) -> int:
    result = _cron_api(action=action, job_id=job_id)
    if not result.get("success"):
        print(color(t("cron.failed_action", action=action, error=result.get("error", t("errors.unknown"))), Colors.RED))
        return 1
    job = result.get("job") or result.get("removed_job") or {}
    print(color(t("cron.action_ok", verb=success_verb, name=job.get("name", job_id), job_id=job_id), Colors.GREEN))
    if action in {"resume", "run"} and result.get("job", {}).get("next_run_at"):
        print(f"  {t('cron.next_run')}: {result['job']['next_run_at']}")
    if action == "run":
        print(f"  {t('cron.run_next_tick')}")
    return 0


def cron_command(args):
    """Handle cron subcommands."""
    subcmd = getattr(args, 'cron_command', None)

    if subcmd is None or subcmd == "list":
        show_all = getattr(args, 'all', False)
        cron_list(show_all)
        return 0

    if subcmd == "status":
        cron_status()
        return 0

    if subcmd == "tick":
        cron_tick()
        return 0

    if subcmd in {"create", "add"}:
        return cron_create(args)

    if subcmd == "edit":
        return cron_edit(args)

    if subcmd == "pause":
        return _job_action("pause", args.job_id, "Paused")

    if subcmd == "resume":
        return _job_action("resume", args.job_id, "Resumed")

    if subcmd == "run":
        return _job_action("run", args.job_id, "Triggered")

    if subcmd in {"remove", "rm", "delete"}:
        return _job_action("remove", args.job_id, "Removed")

    print(t("cron.unknown_command", subcmd=subcmd))
    print(t("cron.usage"))
    sys.exit(1)
