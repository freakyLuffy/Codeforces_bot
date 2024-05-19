import aiohttp

# Function to fetch all problems from Codeforces API
async def fetch_all_problems():
    url = "https://codeforces.com/api/problemset.problems"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = response.json()
            if data['status'] == 'OK':
                return data['result']['problems']
            else:
                raise Exception(f"API call failed: {data['comment']}")



async def fetch_user_submissions(handle):
    url = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=1000000"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data=await response.json()
            if data['status']=='OK':
                return data['result']
            else:
                raise Exception(f"API call failed: {data['comment']}")


# # Initialize database and fetch problems
# initialize_database()
# problems = fetch_all_problems()
# insert_problems(problems)

# # Initialize solved problems table
# initialize_solved_problems_table()

# user_handle = 'slicingzoro'
# submissions = fetch_user_submissions(user_handle)
# insert_solved_problems(user_handle, submissions)

# solved_problems = query_accepted_problems(user_handle)
# print(len(solved_problems))
