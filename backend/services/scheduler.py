"""
LIFEOS Background Scheduler Service ⏰
Handles periodic jobs: deadline checks, morning briefings, and weekly reviews.
"""
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db.mongodb import tasks_collection, users_collection, reviews_collection
from utils.google_api import create_calendar_event, delete_calendar_event, create_gmail_draft
from bson import ObjectId

scheduler = AsyncIOScheduler()

async def check_all_deadlines():
    """
    Check all pending tasks. If a deadline has passed, mark it as overdue.
    Also sync upcoming tasks to calendar.
    """
    print("⏰ Running deadline checks...")
    try:
        now = datetime.now(timezone.utc)
        # Find all pending tasks
        cursor = tasks_collection().find({"status": "pending"})
        async for task in cursor:
            deadline_str = task.get("deadline")
            if not deadline_str or deadline_str == "unknown":
                continue

            if deadline_str == "overdue":
                task_id = task["_id"]
                print(f"  🚨 Task '{task.get('title')}' is marked overdue. Updating status.")
                await tasks_collection().update_one(
                    {"_id": task_id},
                    {"$set": {"status": "overdue"}}
                )
                continue

            try:
                # Parse deadline (handles Z suffix or ISO formats)
                dl_dt = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                # Ensure dl_dt is timezone-aware
                if dl_dt.tzinfo is None:
                    dl_dt = dl_dt.replace(tzinfo=timezone.utc)

                # Check if it passed
                if dl_dt < now:
                    task_id = task["_id"]
                    print(f"  🚨 Task '{task.get('title')}' is past deadline. Marking overdue.")
                    await tasks_collection().update_one(
                        {"_id": task_id},
                        {"$set": {"status": "overdue"}}
                    )
            except Exception as parse_err:
                print(f"  ⚠️ Error parsing deadline for task '{task.get('title')}': {parse_err}")

    except Exception as e:
        print(f"  ❌ Error in check_all_deadlines background job: {e}")


async def send_morning_briefings():
    """
    Daily morning briefing at 8:00 AM.
    Drafts a morning briefing email via Gmail for each connected user.
    """
    print("🌅 Generating morning briefings...")
    try:
        now = datetime.now(timezone.utc)
        # Get start and end of today in local/UTC terms
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        today_end = today_start + timedelta(days=1)

        # Loop through all users
        cursor = users_collection().find()
        async for user in cursor:
            user_id = user.get("user_id")
            if not user_id:
                continue

            # Fetch user details
            name = user.get("name", "User")
            email = user.get("email")
            streak = user.get("streak_days", 0)
            
            # Fetch today's tasks
            tasks_cursor = tasks_collection().find({
                "user_id": user_id,
                "status": {"$in": ["pending", "overdue"]}
            })
            
            today_tasks = []
            async for task in tasks_cursor:
                # If overdue or has a deadline today
                dl = task.get("deadline")
                if task.get("status") == "overdue":
                    today_tasks.append(task)
                elif dl:
                    try:
                        dl_dt = datetime.fromisoformat(dl.replace("Z", "+00:00"))
                        if today_start <= dl_dt < today_end:
                            today_tasks.append(task)
                    except Exception:
                        pass

            if not today_tasks:
                continue

            # Build a beautiful, encouraging text briefing
            task_list_str = ""
            for idx, task in enumerate(today_tasks, 1):
                prio = task.get("priority_score", 5.0)
                status_emoji = "🚨" if task.get("status") == "overdue" else "⏰"
                task_list_str += f"{idx}. {status_emoji} {task.get('title')} [{task.get('category', 'personal')}] - Priority: {prio}/10\n"

            body = f"Good morning, {name.split()[0]}!\n\n"
            body += f"Here is your morning briefing from LIFEOS for today, {now.strftime('%A, %b %d')}.\n\n"
            body += f"🔥 Current streak: {streak} days\n\n"
            body += "Here are the tasks you need to focus on today:\n"
            body += task_list_str
            body += "\nLet's get after it today! Make it count.\n\nBest,\nLIFEOS AI"

            # Create a Gmail draft
            print(f"  ✉️ Creating morning briefing draft for {name} ({email or user_id})...")
            draft = await create_gmail_draft(
                user_id=user_id,
                to=email or "",
                subject=f"🌅 Your Morning Briefing — {now.strftime('%b %d')}",
                body=body
            )
            if draft:
                print(f"  ✅ Draft created for user {user_id}")
            else:
                print(f"  ⚠️ Could not create Gmail draft for user {user_id} (Gmail connection or permissions missing).")

    except Exception as e:
        print(f"  ❌ Error in send_morning_briefings: {e}")


async def generate_weekly_reviews():
    """
    Weekly review Sunday at 8:00 PM.
    Compiles reviews for all users automatically.
    """
    print("📊 Compiling scheduled weekly reviews...")
    try:
        from routes.insights import generate_review, ReviewRequest
        now = datetime.now(timezone.utc)
        week = f"{now.year}-W{now.isocalendar()[1]:02d}"

        cursor = users_collection().find()
        async for user in cursor:
            user_id = user.get("user_id")
            if not user_id:
                continue

            print(f"  📈 Compiling review for user {user_id} for week {week}...")
            try:
                request = ReviewRequest(user_id=user_id, week=week)
                res = await generate_review(request)
                print(f"  ✅ Review generated: {res.get('message')}")
            except Exception as user_err:
                print(f"  ⚠️ Failed to generate review for user {user_id}: {user_err}")

    except Exception as e:
        print(f"  ❌ Error in generate_weekly_reviews: {e}")


def start_scheduler():
    """Start the APScheduler background runner."""
    if not scheduler.running:
        # Run deadline check every 5 minutes
        scheduler.add_job(check_all_deadlines, "interval", minutes=5, id="deadline_check")
        
        # Run morning briefing daily at 8:00 AM
        scheduler.add_job(send_morning_briefings, "cron", hour=8, minute=0, id="morning_briefing")
        
        # Run weekly reviews Sunday at 8:00 PM (20:00)
        scheduler.add_job(generate_weekly_reviews, "cron", day_of_week="sun", hour=20, minute=0, id="weekly_review")
        
        scheduler.start()
        print("⏰ AsyncIOScheduler started successfully!")


def stop_scheduler():
    """Stop the APScheduler background runner."""
    if scheduler.running:
        scheduler.shutdown()
        print("⏰ AsyncIOScheduler stopped.")
