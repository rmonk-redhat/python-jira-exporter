#!/usr/bin/env python3

from jira import JIRA
import jira
import json
import shutil
import os
from pathlib import Path
from pprint import pprint, pformat
from json2html import *
from jinja2 import Template
from jinja2 import Environment, FileSystemLoader, select_autoescape
import datetime
from collections import defaultdict
import tqdm

EXPORT_FOLDER = Path("export")
MAX_ISSUES = 5
PROJECT_MATCH = [] # Projects to include, empty for all


env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape(
    default_for_string=True,
    default=True)
)
TEMPLATE = env.get_template('template-page.html')
INDEX_TEMPLATE = env.get_template('indexpage.html')
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
with tqdm.tqdm(projects, desc="projects") as tqdmproject:
	for project in tqdmproject:
		if PROJECT_MATCH and project.key not in PROJECT_MATCH:
			
			#print("Skipping", project.key)
			continue
		else:
			tqdmproject.set_description('Fetching Project {}'.format(project.key))
		try:
			project_dict[project] = {'name': project.name, 'issues_len':0}
			
			

			# This is made *after* the issues are fetched, to trip the exception
			this_project = EXPORT_FOLDER / str(project)
			os.mkdir(this_project)
			issue_dict = {}
			
			for issue in tqdm.tqdm(jira_cursor.search_issues('project={}'.format(project), maxResults=False), desc="issues", leave=False):
				#pprint(issue.raw)
				#print("\n***{}".format(issue.key))
				creatorname = issue.fields.creator.displayName

				try:
					creatoremail = issue.fields.creator.emailAddress
				except AttributeError:
					creatoremail = 'Unknown'

				issue_dict[issue.key] = {'summary':        issue.fields.summary,
										'key':            issue.key,
										'creator':        "{} <{}>".format(creatorname, creatoremail),
										'project':        "{} ({})".format(issue.fields.project.name, issue.fields.project.key),
										'status':         issue.fields.status.name,
										'issuetype':      issue.fields.issuetype.name,
										'createddate':    issue.fields.created,
										'updateddate':    issue.fields.created,
										'resolutiondate': "{} {}".format(issue.fields.resolution, issue.fields.resolutiondate),
										'description':    issue.fields.description, # remember to htmlify this
										'comments':       [],
										'projectkey':     str(project),
										'attachments':    {},
										'raw':            pformat(issue.raw)}
				# for field in issue.raw['fields']:
				# 	if issue.raw['fields'][field]:
				# 		pprint((field, issue.raw['fields'][field]))
			
			for issue in tqdm.tqdm(jira_cursor.search_issues('project={}'.format(project), expand='comment', fields='comment', maxResults=False), desc='comments', leave=False):
				#pprint(issue.raw)
				for comment in issue.fields.comment.comments:
					creatorname = comment.author.displayName

					try:
						creatoremail = comment.author.emailAddress
					except AttributeError:
						creatoremail = 'Unknown'
					issue_dict[issue.key]['comments'].append({'author':  "{} <{}>".format(creatorname, creatoremail),
				                                        	'body':    comment.body,
				                                        	'created': comment.updated,
				                                        	})



			for issue in tqdm.tqdm(jira_cursor.search_issues('project={}&attachments is not empty'.format(project), fields='attachments', maxResults=False), desc='attachments', leave=False):
				os.mkdir(this_project/str(issue.key))
				#pprint(issue.raw['fields'])
				for attachment in issue.fields.attachment:
					#print("Name: '{filename}', size: {size}".format(
					#	filename=attachment.filename, size=attachment.size))
					issue_dict[issue.key]['attachments'][attachment.id] = attachment.filename
					with open(this_project/str(issue.key)/"{}-{}".format(attachment.id, attachment.filename), "wb") as attachmentfile:
						attachmentfile.write(attachment.get())
					# to read content use `get` method:

					#print("Content: '{}'".format(attachment.get()))
				
				#maxResults evaluates as False, it will try to get all issues in batches.
				#pprint(dir(issue))
				#pprint(issue.raw)
			for issue in issue_dict:
				with open(this_project/"{}.html".format(issue), "w") as issuehtml:
					issuehtml.write(TEMPLATE.render(issue_dict[issue]))
			issuelist = []
			for issue in issue_dict:
				issuelist.append({'url':"{}.html".format(issue),
			                	'label': "{}: {}".format(issue, issue_dict[issue]['summary'])})
			with open(this_project/"index.html", "w") as index:
					index.write(INDEX_TEMPLATE.render({'key': project.key,
				                                	'name': project.name,
				                                	'itemlist': issuelist,
				                                	'backlink': "<a href='../index.html'>List of Projects</a>"

				                                	}))
			project_dict[project]['issues_len'] = len(issue_dict)
		
		except jira.exceptions.JIRAError as e:
			tqdmproject.write("Problem fetching issues for {}. {}".format(project, str(e.text)))
			
	project_list = []
	for project in project_dict:
		project_list.append({'url': "{}/index.html".format(project),
		                	'label': "{}: {} ({} issues)".format(project, project_dict[project]['name'], project_dict[project]['issues_len'])})

	with open(EXPORT_FOLDER/"index.html", "w") as index:
				index.write(INDEX_TEMPLATE.render({'key': options['server'],
				                                	'name': 'All Proejcts exported on {}'.format(datetime.datetime.now()),
				                                	'itemlist': project_list,
				                                	'backlink': None

				                                	}))