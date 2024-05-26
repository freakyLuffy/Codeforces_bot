import sqlite3
from datetime import datetime,timedelta
import matplotlib.pyplot as plt
import asyncio

funny_remarks = [
    "Don't worry, even a tortoise finishes the race! 🐢",
    "Looks like you took a vacation in the problem-solving world! 🌴",
    "Better luck next month, superstar! ⭐️",
    "Slow and steady might just win the race. 🐌",
    "Hey, it's the effort that counts! 👍",
    "Rome wasn't built in a day! 🏛️",
    "Next month will be your time to shine! 🌟",
    "Good things take time, keep going! ⏳",
    "You're just getting warmed up! 🔥",
    "Everyone starts somewhere! 🚀"
]


good_remarks = [
    "Good job! You're getting the hang of it. 👏",
    "Keep up the good work! 💪",
    "You're doing great, keep going! 🌟",
    "Consistency is key, well done! 🗝️",
    "You're on the right track! 🚂",
    "Nice effort this month! 👍",
    "Your persistence is paying off! 💼",
    "Good progress, keep pushing! 🏋️",
    "Solid effort, keep improving! 🏆",
    "Great job, you're doing well! 🌟"
]


excellent_remarks = [
    "Fantastic work! You're a problem-solving machine! 🤖",
    "Incredible performance! 🎉",
    "You're on fire! 🔥",
    "Outstanding effort this month! 🌟",
    "You're a problem-solving superstar! ⭐️",
    "Amazing job! Keep up the great work! 🌟",
    "You're crushing it! 💪",
    "Excellent work, keep it up! 👍",
    "You're a natural! 🌟",
    "You're ready for the next level! 🚀"
]



def generate_remark(total_problems):
    if total_problems <= 10:
        return funny_remarks[total_problems % len(funny_remarks)]
    elif total_problems <= 20:
        return good_remarks[total_problems % len(good_remarks)]
    else:
        return excellent_remarks[total_problems % len(excellent_remarks)]

def analyze_responses(responses):
    from collections import defaultdict
    import calendar

    user_stats = defaultdict(lambda: {'total': 0, 'days': defaultdict(int)})

    # Process responses
    for user_id, response, timestamp in responses:
        day_of_week = datetime.fromisoformat(timestamp).weekday()
        user_stats[user_id]['total'] += 1
        user_stats[user_id]['days'][day_of_week] += 1

    stats = {}
    for user_id, data in user_stats.items():
        days = data['days']
        total_problems = data['total']
        most_active_day = max(days, key=days.get)
        least_active_day = min(days, key=days.get)

        stats[user_id] = {
            'total': total_problems,
            'most_active_day': calendar.day_name[most_active_day],
            'least_active_day': calendar.day_name[least_active_day],
            'problems_per_day': dict(days),
            'remark': generate_remark(total_problems)
        }

    return stats

async def generate_and_send_stats(context, user_id, stats):
    from collections import defaultdict
    import calendar
    from matplotlib.dates import date2num, num2date
    import io

    data = stats[user_id]
    days = data['problems_per_day']
    days_sorted = sorted(days.items())

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.bar([calendar.day_name[day] for day, _ in days_sorted], [count for _, count in days_sorted], color='blue')
    plt.xlabel('Day of the Week')
    plt.ylabel('Problems Solved')
    plt.title('Problems Solved Per Day of the Week')

    # Save the plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # Send the plot
    await context.bot.send_photo(
        chat_id=user_id,
        photo=buf,
        caption=(
            f"Here are your problem-solving stats for the past month:\n"
            f"Total problems solved: {data['total']}\n"
            f"Most active day: {data['most_active_day']}\n"
            f"Least active day: {data['least_active_day']}\n"
            f"Comment: {data['remark']}"
        )
    )

async def fetch_monthly_responses():
    conn = sqlite3.connect('codeforces_problems.db')
    cursor = conn.cursor()
    try:
        # Execute the SQL SELECT command to retrieve responses from the last month
        cursor.execute('''
            SELECT user_id, response, timestamp
            FROM user_responses
        '''), 

        # Fetch all responses
        responses = cursor.fetchall()

        # Organize responses by user_id
        # user_responses = {}
        # for user_id, response, timestamp in responses:
        #     if user_id not in user_responses:
        #         user_responses[user_id] = []
        #     user_responses[user_id].append((response, timestamp))
        
        return responses
    except sqlite3.Error as e:
        # Handle any errors that occur during database operation
        print(f"Error fetching monthly responses: {e}")
        return {}
    finally:
        # Close the database connection
        conn.close()


async def send_monthly_stats(context):
    responses = await fetch_monthly_responses()
    stats = analyze_responses(responses)

    tasks = [
        generate_and_send_stats(context, user_id, stats)
        for user_id in stats
    ]
    
    await asyncio.gather(*tasks)

    await delete_previous_records()




async def delete_previous_records():
    try:
        # Connect to the database
        conn = sqlite3.connect('codeforces_problems.db')
        cursor = conn.cursor()

        # Calculate the date one month ago
        one_month_ago = datetime.now()

        # Execute the SQL DELETE command to remove records older than one month
        cursor.execute('''
            DELETE FROM user_responses
            WHERE timestamp < ?
        ''', (one_month_ago.isoformat(),))
        
        # Commit the transaction to apply changes
        conn.commit()
        print("Previous month's records deleted successfully.")
    except sqlite3.Error as e:
        # Handle any errors that occur during database operation
        print(f"Error deleting previous month's records: {e}")
    finally:
        # Close the database connection
        conn.close()

