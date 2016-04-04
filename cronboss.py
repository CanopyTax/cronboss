#!/usr/bin/python3
import schedule
import time
import os
import sys
# import subprocess
import requests
from datetime import datetime

from docker import Client


class SelectorException(Exception):
    pass


cmd_args = sys.argv[1:]  # Trim
docker = Client(base_url='unix://var/run/docker.sock')
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')


def select_container():
    selector = os.getenv('SELECTOR_LABEL')
    eligible_containers = docker.containers(filters={'label': selector, 'status': 'running'})
    if len(eligible_containers) < 1:
        raise SelectorException('ERROR: No containers found with SELECTOR_LABEL "{}"'
              .format(selector))
    else:
        return eligible_containers[0].get('Id')


def run_command():
    try:
        container_id = select_container()
    except SelectorException as e:
        report_to_slack(str(e))
        return

    print('Running command on container {}. Current time: {}'
          .format(container_id[:8], str(datetime.now())))
    cmd_args = sys.argv[1:]  # Trim the first argument (this program)
    exec_id = docker.exec_create(container_id, cmd_args, tty=True).get('Id')
    output = docker.exec_start(exec_id)
    # result = subprocess.check_output(cmd_args, universal_newlines=True)
    result_object = docker.exec_inspect(exec_id)
    returncode = result_object.get('ExitCode')

    if returncode == 0:
        response_string = '-- SUCCESS! --'
    else:
        response_string = '-- FAILURE! -- Command returned exit code {}'.format(returncode)

    report_to_slack(response_string, 'Command finished at {}. Output:\n{}'
          .format(str(datetime.utcnow()), output.decode('utf-8')))


def report_to_slack(*strings):
    print(*strings)
    if SLACK_WEBHOOK_URL:
        print('sending logs to slack...')
        string = ' '.join(strings)
        SLACK_CHANNEL = os.getenv('SLACK_CHANNEL') or '#general'
        SLACK_USERNAME = os.getenv('SLACK_USERNAME') or 'cronboss'
        ICON_URL = os.getenv('SLACK_ICON_URL')
        slack_message = {
            'channel': SLACK_CHANNEL,
            'text': string,
            'username': SLACK_USERNAME,
        }
        if ICON_URL:
            slack_message['icon_url'] = ICON_URL

        try:
            req = requests.post(SLACK_WEBHOOK_URL, json=slack_message)
            if req.status_code in (200, 201, 202, 204):
                print('logs sent to slack channel {}'
                      .format(slack_message['channel']))
            else:
                print('received error code {} with response: {}'
                      .format(req.status_code, req.text))
        except (ConnectionError, requests.HTTPError) as e:
            print('Sending logs to slack failed: {}'
                  .format(e))
        except Exception as e:
            print('Something crazy happened sending logs to slack: {}'
                  .format(e))


def build_schedule():
    print('Starting cronboss. Current time: {}'
          .format(str(datetime.now())))
    interval = int(os.getenv('INTERVAL', '1'))
    unit = os.getenv('UNIT', 'day')
    time_of_day = os.getenv('TIME')

    evaluation_string = 'schedule.every(interval).' + unit
    if time_of_day:
        evaluation_string += '.at(time_of_day)'

    evaluation_string += '.do(run_command)'
    eval(evaluation_string)


def run_schedule():
    while True:
        sleep_time = schedule.next_run() - datetime.now()
        print('Next job to run at {}, which is {} from now'
              .format(str(schedule.next_run()), str(sleep_time)))

        # Sleep an extra second to make up for microseconds
        time.sleep(max(1, sleep_time.seconds + 1))
        schedule.run_pending()


if __name__ == "__main__":
    print(sys.argv)
    if not os.getenv('SELECTOR_LABEL'):
        print('ERROR: environment variable "SELECTOR_LABEL" is required.')
        exit(1)

    if 'now' == os.getenv('UNIT'):
        # Run now and exit instead of using a cron
        run_command()
    else:
        build_schedule()
        run_schedule()


