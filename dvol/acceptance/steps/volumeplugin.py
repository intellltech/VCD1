from __future__ import unicode_literals, print_function

from time import sleep
from tempfile import mkdtemp

from docker import Client

from behave import given, when


@given("docker daemon is running")
def start_docker_deamon(context):
    """
    Use the system Docker daemon to run another Docker daemon for a test
    scenario.
    """
    port = 2375
    name = "dvol-dind-testing-xxx"
    docker_dind_image = "docker:1.10.0-rc1-dind"
    context.client = Client()
    print(context.client.version())
    context.dind_run_docker_plugins = mkdtemp()
    context.dind_var_run = mkdtemp()
    # docker run -d --privileged --name docker-1.10.0-rc1 docker:1.10.0-rc1-dind
    try:
        context.client.stop(name)
        context.client.remove_container(name)
    except Exception as e:
        print("remove_container failed", e)
    context.client.pull(docker_dind_image)
    context.dind_id = context.client.create_container(
        name=name,
        image=docker_dind_image,
        ports=[port],
        # Get some communication guts to share with the dvol plugin.  Normally
        # dvol hooks into the system docker which has easier-to-access state.
        # We don't want that, though.  We want to enable dvol on our dind
        # instance.
        volumes=["/run/docker/plugins", "/var/run/"],
        host_config=context.client.create_host_config(
            privileged=True,
            port_bindings={port: port},
            binds={
                context.dind_run_docker_plugins: {
                    "bind": "/run/docker/plugins",
                    "mode": "rw",
                },
                context.dind_var_run: {
                    "bind": "/var/run",
                    "mode": "rw",
                },
            },
        ),
    )
    context.client.start(context.dind_id)
    # XXX It takes an unknown amount of time to become ready.
    sleep(1)
    details = context.client.inspect_container(context.dind_id)
    ip = details["NetworkSettings"]["IPAddress"]
    context.dind_client = Client(
        base_url="http://{ip}:{port}/".format(ip=ip, port=port),
    )
    print(context.dind_client.version())

# XXX after_scenario for dind cleanup?


@given("dvol volume plugin is installed")
def install_dvol_volume_plugin(context):
    # XXX Test the local version, don't pull from Docker hub
    dvol_image = "clusterhq/dvol"
    context.var_lib_dvol = mkdtemp()
    # docker run -v /var/lib/dvol:/var/lib/dvol --restart=always -d \
    #     -v /run/docker/plugins:/run/docker/plugins \
    #     -v /var/run/docker.sock:/var/run/docker.sock \
    #     --name=dvol-docker-plugin clusterhq/dvol
    context.dvol_id = context.dind_client.create_container(
        volumes=[
            "/var/lib/dvol",
            "/run/docker/plugins",
            "/var/run/docker.sock",
        ],
        host_config=context.dind_client.create_host_config(
            # XXX should probably not let it auto-restart, it's probably a bug
            # if that happens in the tests
            restart_policy="always",
            binds={
                context.var_lib_dvol: {
                    "bind": "/var/lib/dvol",
                    "mode": "rw",
                },
                context.dind_run_docker_plugins: {
                    "bind": "/run/docker/plugins",
                    "mode": "rw",
                },
                context.dind_var_run: {
                    "bind": "/var/run",
                    "mode": "rw",
                },
            },
        ),
        name="dvol-docker-plugin",
        image=dvol_image,
    )
    context.dind_client.start(context.dvol_id)


@when("a container is created with a dvol volume named <name>")
def create_stateful_container(context):
        stateful_id = context.dind_client.create_container(
            name="random-test-name",
            # XXX use a good image
            image="busybox",
            volumes=["/data"],
            volume_driver="dvol",
        )
        context.find_client.start(stateful_id)
