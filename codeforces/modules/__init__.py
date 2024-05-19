
from .utils import start,add_handle,subscribe,unsubscribe,set_filter,rating_min_received,rating_max_received,tags_received,handle_received
from .all_problems import update_problems
from .problem_sender import send_daily_problem
from .codeforces_api import fetch_user_submissions

def __list_all_modules():
    from os.path import dirname, basename, isfile
    import glob
    mod_paths = glob.glob(dirname(__file__) + "/*.py")
    all_modules = [basename(f)[:-3] for f in mod_paths if isfile(f)
                   and f.endswith(".py")
                   and not f.endswith('__init__.py')]

    return all_modules



ALL_MODULES = sorted(__list_all_modules())