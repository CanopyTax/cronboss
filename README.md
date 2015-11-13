# cronboss

This container runs a command on another container, as a schedule.
The equivalent function could be added by putting a crontab on the desired container,
but that gets tricky when you have multiple containers running the same code in a production like environment.

This container will automatically select one (and only one) container based on labels, and run the command once.
This is equivalently a "leader-selection" device for running crons.

## How do I use it

The container needs access to the docker socket as well as some environment variables. The command you would like to run is passed in as the container command.

The environment variables needed are:

    SELECTOR_LABEL : A key=value pair string representing the docker label, i.e. "service=foobar"
    INTERVAL: How many units (Optional, default=1)
    UNIT: Unit of time (Optional, default=day)
    TIME: Specific time of each day to run (Optional, used instead of INTERVAL and UNIT)
    
For example, if you want to run your job every 4 hours, you would set `INTERVAL=4` and `UNIT= hours`.
If you would like to run your job every day at 6:00pm (server time) you would set `TIME=18:00`.


Example:

    # Launch two containers with the same labels
    docker run -it --label service==foobar debian sleep 20000;
    docker run -it --label service==foobar debian sleep 20000;
    
    # Now run your command in the container!
    docker run -it -v /var/run/docker.sock:/var/run/docker.sock -e SELECTOR_LABEL=service=foobar -e INTERVAL=15 -e UNIT=seconds canopytax/cronboss echo Hello World
    

## Run Now!

You can also just use this container to do a one-time command. You do this by setting `UNIT=now`.