import os
import time
import re
from gitlab import Gitlab

# # DOTENV FOR TESTING ----------------------
# from dotenv import load_dotenv, find_dotenv

# load_dotenv(find_dotenv())
# # DOTENV FOR TESTING ----------------------

# GET VALUES FROM ENVIRONMENT
gitlab_token = os.environ.get('GITLAB_TOKEN')
project_id = os.environ.get('GITLAB_PROJECT_ID')
trigger_decription = os.environ.get('GITLAB_PROJECT_TRIGGER_DESCRIPTION')

clone_source_url = os.environ.get('FORK_URL')
sha_source_url = os.environ.get('FORK_SHA')
pull_request_number = os.environ.get('PULLRQ_NR')

# CHECK VALUES FROM ENVIRONMENTV
print(f'GITLAB_PROJECT_ID: {project_id}')
print(f'GITLAB PROJECT TRIGGER DESCRIPTION: {trigger_decription}')
print(f'FORK URL: {clone_source_url}')
print(f'FORK SHA: {sha_source_url}')
print(f'PULL RQ NUMBER: {pull_request_number}')

# ACCESS GITLAB
gl = Gitlab('https://gitlab.espressif.cn:6688', private_token=gitlab_token)
project = gl.projects.get(project_id)


# CREATE (TRIGGER) PIPELINE IN GITLAB
def get_or_create_trigger(project):
    # trigger_decription = 'my_trigger_id'
    for t in project.triggers.list():
        if t.description == trigger_decription:
            return t
    return project.triggers.create({'description': trigger_decription})


trigger = get_or_create_trigger(project)
pipeline = project.trigger_pipeline(
    'main',
    trigger.token,
    variables={
        "FORK_URL": clone_source_url,
        "FORK_SHA": sha_source_url,
        "PULLRQ_NR": pull_request_number,
    },
)
print(f'PIPELINE ID: {pipeline.id}')

# WAIT UNTIL GITLAB PIPELINE FINISHES
while pipeline.finished_at is None:
    print(f'PIPELINE RUNNING STATUS: {pipeline.status}')
    pipeline.refresh()
    time.sleep(15)

# REPORT FINISH STATUS OF GITLAB PIPELINE
pipeline_detailed_status = pipeline.detailed_status['label']
print(f'PIPELINE {pipeline.id} -> FINAL STATUS: {pipeline_detailed_status}')

if pipeline_detailed_status == 'passed':
    print(f'PIPELINE {pipeline.id} finished with SUCCESS')
    # exit(0)
else:
    print(f'PIPELINE {pipeline.id} FAILED')
    exit(1)

# UPLOAD JOB LOGS OF PIPELINE TO LOG FILES
jobs = pipeline.jobs.list()
jobs_ids_list = [job.id for job in jobs]
print(jobs_ids_list)

for job_id in jobs_ids_list:
    job = project.jobs.get(job_id)
    job_log = job.trace()

    ansi_escape_8bit = re.compile(br'(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])')
    job_log_clean = ansi_escape_8bit.sub(b'', job_log).decode('utf-8')

    # SAVE TO FILE
    filename = f'artifacts/GLP{pipeline.id}_GLJ{job.id}-{job.name}.log'
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w") as f:
        f.write(job_log_clean)
        print(f'TEST: {job.name} of PIPELINE {pipeline.id} -> RESULTS write to {filename}')
