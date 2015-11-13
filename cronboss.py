#!/usr/bin/python3
__author__ = 'nhumrich'

import schedule
import time
import os
import sys
# import subprocess
from datetime import datetime

from docker import Client

cmd_args = sys.argv[1:]  # Trim
docker = Client(base_url='unix://var/run/docker.sock')


def select_container():
    selector = os.getenv('SELECTOR_LABEL')
    key, value = selector.split('=')
    eligible_containers = docker.containers(filters={key: value})
    if len(eligible_containers) < 1:
        print('ERROR: No containers found with SELECTOR_LABEL "{}"'
              .format(selector))
    else:
        return eligible_containers[0].get('Id')


def runCommand():
    container_id = select_container()
    print('Running command. Current time: {}'.format(str(datetime.now())))
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


    print(response_string, 'Command finished at {}. Output:\n{}'
          .format(str(datetime.utcnow()), output.decode('utf-8')))


def build_schedule():
    print('Starting cronboss. Current time: {}'
          .format(str(datetime.now())))
    interval = int(os.getenv('INTERVAL', '1'))
    unit = os.getenv('UNIT', 'day')
    time_of_day = os.getenv('TIME')

    evaluation_string = 'schedule.every(interval).' + unit
    if time_of_day:
        evaluation_string += '.at(time_of_day)'

    evaluation_string += '.do(runCommand)'
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
    if not os.getenv('SELECTOR_LABEL'):
        print('ERROR: environment variable "SELECTOR_LABEL" is required.')
        exit(1)

    if 'now' == os.getenv('UNIT'):
        # Run now and exit instead of using a cron
        runCommand()
    else:
        build_schedule()
        run_schedule()


