# Update Todoist Section Assignments

## Purpose: Assign all tasks in a user's Todoist inbox to useful time bins based on task due dates.

## Author: Jim Sewall

## Description

This program uses the Todoist REST API to ingest all Todoist tasks in a user's inbox, parse the due-date
construct, and (re)assign each task to one of the following bins:
  * Overdue
  * Today
  * This Week
  * This Month
  * This Quarter
  * This Year
  * Future

These sections are created if they do not already exist.

## Instructions:
1. Download a copy of Update_Todoist_Section_Assignments.py to your desktop.
2. Log into your Todoist web app, navigate to Settings > Integrations > Developer tab, and copy your personal API token to your clipboard.
3. Edit the source file and paste the token into the following variable definition:

API_TOKEN = ""

4. Ensure that all of the following modules have been installed:
   * todoist_api_python
   * datetime
   * python-dateutil
   * tqdm
5. Execute.

## Supported Platforms:
This program can be executed on any Windows or Android platform with Python 3.11 or greater.  For example, the code can be uploaded or pasted into an Android IDE such as Py3.

## Known Issues:

Because of API limitations, section assignments are performed by cloning existing tasks with new sections then
deleting the original tasks.  Limitations also prevent replication of task recurrance information; hence the user
is asked whether recurring tasks should be copied into the next fixed-date instances.
