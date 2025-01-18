'''
Name: Update Todoist Section Assignments

Purpose: Ingest all tasks in a user's Todoist inbox and assign them to time-based bins based on task due date.

Author: Jim Sewall

Desciption: 

This program uses the Todoist REST API to ingest all Todoist tasks in a user's inbox, parse the due-date
construct, and based on that date (re)assign each task to one of the following bins:
  * Overdue
  * Today
  * This Week
  * This Month
  * This Quarter
  * This Year
  * Future
If any or all of these sections do not exist in the user's Inbox, they are created.

Instructions:
    1. Log into your Todoist web app, navigate to Settings > Integrations > Developer tab, and copy your personal API token to your clipboard.
    2. Paste the token between the double quotes in the variable definition below:
'''
API_TOKEN = ""
'''
    3. Execute.

Known Issues:

Because of API limitations, section assignments are performed by cloning existing tasks with new sections then
deleting the original tasks.  API limitations also prevent replication of task recurrance information, hence the user
is asked whether recurring tasks should be copied into the next instances of fixed-date tasks in the current run.
'''
from todoist_api_python.api import TodoistAPI
from datetime import datetime, timedelta
from dateutil import parser
import json
import sys
from tqdm import tqdm

'''
Function Definitions
'''
def get_inbox_id():
# Get the project id of the "Inbox" project, which exists by default.  This is the Todoist project we will operate on.
    projects = api.get_projects()
    for project in projects:
        sections = api.get_sections(project_id=project.id)
        if project.name == "Inbox":
            return project.id
            break

def prompt_for_recurring_task_treatment():
# Ask the user whether to generate the next single instances of tasks that have been specified as recurring tasks.
    answer = input("Do you want to address recurring tasks? ")[0].capitalize()
    #print(f'answer = {answer}')
    address_recurring = True
    if answer != 'Y':
        address_recurring = False
    return address_recurring

def set_time_bin_boundaries():
# Establish the date-time boundaries of the time-based bins into which tasks are to be sorted based on
# today's date
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    next_month = today.replace(day=28) + timedelta(days=4)
    end_of_year = today.replace(month=12, day=31)
    return today,next_week,next_month,end_of_year


def construct_data_objects(SECTIONS):
# Construct a dictionary of Todoist tasks along with time-based section names and IDs.

    # Get the project id of the "Inbox" project, which exists by default.  This is the Todoist project we will operate on.
    projects = api.get_projects()
    for project in projects:
        sections = api.get_sections(project_id=project.id)
        if project.name == "Inbox":
            inbox_id = project.id
            break

    # Get the section ids of all sections in the inbox
    inbox_section_ids = {}
    inbox_section_names = {}
    for section in sections:
        sec_name = section.name
        sec_id = section.id
        inbox_section_ids[sec_name] = sec_id
        inbox_section_names[sec_id] = sec_name
    
    # Create any time-based inbox sections that do not already exist
    for name in SECTIONS:
        if value_not_in_dictionary (name, inbox_section_names):
            print(f'Creating "{name}" section in Inbox ...')
            section = api.add_section(name=name,project_id=inbox_id)
            inbox_section_ids[name] = section.id
            inbox_section_names[section.id] = section.name

    # Get the task ids of all tasks in the inbox sections
    task_dictionary = {}
    tasks = api.get_tasks(section_id=None)
    task_dictionary = load_tasks_into_dictionary(tasks,
                                                 inbox_id,
                                                 inbox_section_names,
                                                 task_dictionary)

    # Initialize a dictionary that assigns a calendar quarter number to each month number.
    quarters = {1:1,   2:1,  3:1,
                4:2,   5:2,  6:2,
                7:3,   8:3,  9:3,
                10:4, 11:4, 12:4}

    # Create a 'right-now' dictionary of current date, year, day, etc.
    current = {}
    current['date'] = datetime.now().date()
    current['year'] = current['date'].year
    current['day'] = current['date'].day
    current['month'] = current['date'].month
    current['quarter'] = quarters[current['month']] 
    current['week'] = datetime.now().date().isocalendar()[1]

    #for key,value in current.items():
    #    print(f'current.{key} = {value}')

    return task_dictionary,inbox_section_ids,inbox_id,inbox_section_names,quarters,current

def load_tasks_into_dictionary(tasks,
                               inbox_id,
                               inbox_section_names,
                               task_dictionary):
# Initialize and load the Todoist tasks dictionary and return it to the caller.
    n_tasks = len(tasks)
    n_processed = 0

    # Loop over every Todoist task in object passed by the caller, using the tqdm construct to
    # present a progress bar.
    for task in tqdm(tasks,' Loading tasks'):
        # Create an empty item dictionary and populate it with field values from the current
        # task
        item_dictionary = {}
        item_dictionary['task_id'] = task.id
        item_dictionary['inbox_id'] = inbox_id
        item_dictionary['content'] = task.content
        item_dictionary['parent_id'] = task.parent_id
        item_dictionary['assignee_id'] = task.assignee_id
        item_dictionary['priority'] = task.priority
        item_dictionary['labels'] = task.labels
        item_dictionary['order'] = task.order
        item_dictionary['description'] = task.description
        item_dictionary['created_at'] = task.created_at

        try:
            # If a task due date exists, store it in the item dictionary as both a string and
            # a raw date value.  If not, store "None" values.
            item_dictionary['task_due'] = datetime.strptime(task.due.date, "%Y-%m-%d").date()
            item_dictionary['due'] = task.due.date
        except:
            item_dictionary['task_due'] = None
            item_dictionary['due'] = None

        try:
            # Save a recurring task indicator in the item dictionary.
            item_dictionary['one_time_task'] = not task.due.is_recurring
        except:
            item_dictionary['one_time_task'] = True
        
        try:
            # For a recurring task, load the item_dictionary with the complex JSON recurring due date object.
            due_object = task.due
            if due_object.is_recurring:
                item_dictionary['due'] = json.dumps(due_object,default=default_json)
        except:
            pass

        # Load the item dictionary into the overall task dictionary, tagged by the task id.
        task_dictionary[task.id] = item_dictionary
        n_processed+=1
    return task_dictionary

def value_not_in_dictionary(target_value, dictionary):
# Utility function that informs the caller if a target value is not contained in a dictionary
    return not(target_value in dictionary.values())

def determine_new_section(task,current,quarters):
# Determine which time-based inbox section is most appropriate for a given task based on its due date.

    # Default the task's section to 'Future'
    new_section = 'Future'

    # Identify task's due year, month, day, etc., allowing for values that have not been specified.
    try:
        due_year = task['task_due'].year
    except:
        due_year = current['year']
    try:
        due_month = task['task_due'].month
    except:
        due_month = current['month']
    try:
        due_day = task['task_due'].day
    except:
        due_day = current['day']
    try:
        due_quarter = quarters[due_month]
    except:
        due_quarter = current['quarter']
    try:
        due_week = task['task_due'].isocalendar()[1]
    except:
        due_week = current['week']

    # Incrementally establish most appropriate time-based bin for task
    try:
        if due_year == current['year']:
            new_section = 'This Year'
            if current['quarter'] == due_quarter:
                new_section = 'This Quarter'
            if due_month == current['month']:
                new_section = 'This Month'
                if int(due_day) < current['day']+8:
                    new_section = 'This Week'
                    if due_day == current['day']:
                        new_section = 'Today'
                    elif int(due_day) < current['day']:
                        new_section = 'Overdue'
                else: #Might be on the edge of this week and next
                    if int(due_day) <= current['day']+2:
                        new_section = 'This Week'
        elif int(due_year) < current['year']:
            new_section = 'Overdue'
    except Exception as e:
        print(str(e))

    return new_section

def move_task(task,inbox_section_ids,inbox_section_names,
              section_name,address_recurring):
# To move a task means to replicate it with the section ID of the section to which it
# is being moved.  Replication is performed slightly differently for one-time and
# recurring tasks.

    original_task_id = task['task_id']
    new_task_section_id = inbox_section_ids[section_name]

    if task['one_time_task']:    
        api.add_task(content=task['content'],
            description=task['description'],
            project_id=task['inbox_id'],
            section_id=new_task_section_id,
            parent_id=task['parent_id'],
            order=task['order'],
            labels=task['labels'],
            priority=task['priority'],
            assignee_id=task['assignee_id'],
            due_date=task['due'])
        api.delete_task(task_id=original_task_id)
    elif address_recurring:
        try:
            api.add_task(content=task['content'],
                description=task['description'],
                project_id=task['inbox_id'],
                section_id=new_task_section_id,
                parent_id=task['parent_id'],
                order=task['order'],
                labels=task['labels'],
                priority=task['priority'],
                assignee_id=task['assignee_id'],
                due_date=str(task['task_due']))
            api.close_task(task_id=original_task_id)
        except Exception as e:
            print(f'*** {str(e)}')
            sys.exit()
    return

def default_json(t):
# Used by function that creates a task due date object
    return f'{t}'

'''
== Main ==========================================================================================================================
'''
# Instantiate the API 
print('Contacting ToDoist...')
api = TodoistAPI(API_TOKEN)

# Define the time-binned project section names.  If these do not already exist in the Inbox, they are created.
SECTIONS = ['Overdue','Today','This Week','This Month','This Quarter','This Year','Future','Recurring Tasks']

# Ask user whether to address recurring tasks.  Because of API limitations, this requires a computationally expensive workaround
# that generally does not need to be invoked.
address_recurring = prompt_for_recurring_task_treatment()

# Establish the boundaries for the Today, Next Week, Next Month and Next Year boundaries based on the current date.
today,next_week,next_month,end_of_year = set_time_bin_boundaries()
taskdict,inbox_section_ids,inbox_id,inbox_section_names,quarters,current = construct_data_objects(SECTIONS)

n_items = len(taskdict)
n_processed = 0

# Loop over every key/value pair in the task dictionary, using the tqdm construct to
# present a progress bar.  The value in each instance represents a task.

for key1, value1 in tqdm(taskdict.items(),desc="Updating tasks"):
    new_section = determine_new_section(value1,current,quarters)
    try:
        move_task(value1,
                 inbox_section_ids,
                 inbox_section_names,
                 new_section,
                 address_recurring)
        n_processed+=1
    except Exception as e:
        section = 'Future'
        move_task(value1,
                 inbox_section_ids,
                 inbox_section_names,
                 section,
                 address_recurring)
