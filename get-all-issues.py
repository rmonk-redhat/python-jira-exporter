#!/usr/bin/env python3

from jira import JIRA
import jira
import json
import shutil
import os
from pathlib import Path
from pprint import pprint
import json2html
from jinja2 import Template


EXPORT_FOLDER = Path("export")
MAX_ISSUES = 5
PROJECT_MATCH = ['AF30'] # Projects to include, empty for all
SAMPLE_PAGE = Template("""
<html><head><title>{{key}} - {{name}}</title></head><body>
<h1>{{project}} - {{key}} - {{name}}</h1>

<h3>{{summary}}</h3>

<dl>
<dt>Creator</dt>
<dd>{{creator}}</dd>
<dt>Status</dt>
<dd>{{status}}</dd>
<dt>type</dt>
<dd>{{issuetype}}</dd>
<dt>Created Date</dt>
<dd>{{createddate}}</dd>
<dt>Resolution Date</dt>
<dd>{{resolutiondate}}</dd>
</dl>

<h2>Description</h2>
<blockquote>
{{ description }}
</blockquote>

<h2>Comments</h2>
<ol>
{% for comment in comments %}
<li> {{comment}} </li>
{% endfor %}
</ol>

<h2>Attachments</h2>
{% for attachment in attachments %}
{{ attachment }}
{% endfor%}

<h2>All data</h2>

{{ raw }}

</body></html>
""")



shutil.rmtree(EXPORT_FOLDER, ignore_errors=True)
os.mkdir(EXPORT_FOLDER)




with open('secret.json') as jsonsecret:
	jsondata = json.load(jsonsecret)
	options = {
		"server":jsondata['jira_url']
	}	
	JIRA_USERNAME = jsondata['username']
	JIRA_PASSWORD = jsondata['password']
	

jira_cursor = JIRA(options, basic_auth=(JIRA_USERNAME, JIRA_PASSWORD))


# https://jira.readthedocs.io/en/master/examples.html#projects

project_dict = {}

projects = jira_cursor.projects()
for project in projects:
	if PROJECT_MATCH and project.key not in PROJECT_MATCH:
		
		#print("Skipping", project.key)
		continue
	else:
		print("Fetching", project.key)
	try:
		project_dict[project] = {'name': project.name, 'issues':{}}
		
		

		# This is made *after* the issues are fetched, to trip the exception
		this_project = EXPORT_FOLDER / str(project)
		os.mkdir(this_project)
		issue_dict = {}
		for issue in jira_cursor.search_issues('project={}'.format(project,MAX_ISSUES), maxResults=False):
			issue_dict[issue.key] = issue.name
			print("\n***{}".format(issue.key))
			for field in issue.raw['fields']:
				if issue.raw['fields'][field]:
					pprint((field, issue.raw['fields'][field]))
			

			for attachment in issue.fields.attachment:
			    print("Name: '{filename}', size: {size}".format(
			        filename=attachment.filename, size=attachment.size))
			    # to read content use `get` method:
			    print("Content: '{}'".format(attachment.get()))
			# maxResults evaluates as False, it will try to get all issues in batches.
			#pprint(dir(issue))
			#pprint(issue.raw)
	except jira.exceptions.JIRAError as e:
		print("Problem fetching issues for {}".format(project))
		print(e)
