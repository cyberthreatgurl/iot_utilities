""" This script discovers Hue lights on the local network and prints their details. """


from phue import Bridge, PhueRegistrationException, PhueRequestTimeout

try:
    b = Bridge('192.168.1.148')

    # This only needs to be run a single time
    b.connect()

    # Get the bridge state (This returns the full dictionary that you can explore)
    b.get_api()
except PhueRegistrationException:
    print("Press the button on the bridge and try again")
except PhueRequestTimeout:
    print("Could not connect to the bridge - check your network")