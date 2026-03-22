import urllib.request
import json
url = 'https://api.github.com/repos/cliff-de-tech/Linkedin-Post-Bot/actions/runs?status=failure&per_page=1'
req = urllib.request.Request(url)
try:
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        run_id = data['workflow_runs'][0]['id']
        jobs_url = data['workflow_runs'][0]['jobs_url']
        print(f'Failed Run ID: {run_id}')
        with urllib.request.urlopen(jobs_url) as jres:
            jdata = json.loads(jres.read().decode('utf-8'))
            for job in jdata['jobs']:
                if job['conclusion'] == 'failure':
                    print(f'Failed Job: {job["name"]}')
                    print(f'Job steps: ')
                    for step in job['steps']:
                        if step['conclusion'] == 'failure':
                            print(f'Failed Step: {step["name"]}')
                            break
except Exception as e:
    print('Error fetching logs:', e)
