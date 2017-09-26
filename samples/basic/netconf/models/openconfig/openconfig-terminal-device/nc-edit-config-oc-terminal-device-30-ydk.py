#!/usr/bin/env python
#
# Copyright 2016 Cisco Systems, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Edit configuration for 20x10GE --> 1x200G model openconfig-terminal-device.

usage: nc-edit-config-oc-terminal-device-30-ydk.py [-h] [-v] device

positional arguments:
  device         NETCONF device (ssh://user:password@host:port)

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  print debugging messages
"""

from argparse import ArgumentParser
from urlparse import urlparse

from ydk.services import NetconfService, Datastore
from ydk.providers import NetconfServiceProvider
from ydk.models.openconfig import openconfig_interfaces \
    as oc_interfaces
from ydk.models.openconfig import openconfig_terminal_device \
    as oc_terminal_device
from ydk.models.openconfig import openconfig_platform \
    as oc_platform
from ydk.models.ietf import iana_if_type
from ydk.models.openconfig import openconfig_transport_types \
    as oc_tr_types
from ydk.types import Decimal64
import logging


def config_interfaces(interfaces):
    
    """
    Add config data for each line interface to be active
    within the configured slice
    """   

    ## Trunk port configuration
    interface = interfaces.Interface()
    interface.name = 'Optics0/0/0/6'
    if_config = interface.Config()
    if_config.name = 'Optics0/0/0/6'
    if_config.type = iana_if_type.OpticalchannelIdentity()
    ## "True" means port is in "no shut" mode
    ## "False" means port is in "shut" mode
    if_config.enabled = True
    interface.config = if_config
    interfaces.interface.append(interface)


def config_terminal_device(terminal_device):

    """
    Add config data for correlation between client
    ports, logical channels and optical channels.
    "20x10G client -> 1x200G line" slice mode.
    In that mode in each client port is
    mapped to the single (second) line port.
    """
    ## Define logical mapping between logical ethernet channels
    ## and logical OTN channels

    ## Creation of the logical number (index) for the client ports (4x10GE)
    ## of slice0
    for j in [[0, '0/0-Optics0/0/0/0'], [10, '0/0-Optics0/0/0/1'],
          [20, '0/0-Optics0/0/0/2'], [30, '0/0-Optics0/0/0/3'],
          [40, '0/0-Optics0/0/0/4']]:
        NUM = 100
        for i in range(1,5):       
            channel = terminal_device.logical_channels.Channel()
            ## indexing can be any, except 0. 
            channel.index = NUM + j[0]
            ## defining the Ethernet logical channel (speed, status, Eth mode)
            channel_config = channel.Config()
            channel_config.rate_class = oc_tr_types.Trib_Rate_10GIdentity()
            channel_config.trib_protocol = oc_tr_types.Prot_10Ge_LanIdentity()
            channel_config.logical_channel_type = oc_tr_types.Prot_EthernetIdentity()
            channel.config = channel_config
            ## mapping of the client physical port into the 
            ## assigned logical number (index)
            channel_ingress = channel.Ingress()
            channel_ingress_tr = channel_ingress.Config()
            channel_ingress_tr.transceiver = j[1]
            channel_ingress_tr.physical_channel.append(i)
            channel_ingress.config = channel_ingress_tr
            channel.ingress = channel_ingress
            ## mapping the ethernet logical channel into the OTN logical channel
            channel_assignment = channel.logical_channel_assignments.Assignment()
            ## mapping the logical channel and the client port
            channel_assignment.index = 1
            channel_assignment_config = channel_assignment.Config()
            ## Defining the allocation of client speed into the line port
            channel_assignment_config.allocation = Decimal64('10')
            channel_assignment_config.assignment_type = channel_assignment.\
                                                        config.AssignmentTypeEnum.\
                                                        LOGICAL_CHANNEL
            ## defining the number of a line to be used for that client port
            ## line is also indexed and will be defined later
            channel_assignment_config.logical_channel = 200
            channel_assignment.config = channel_assignment_config
            channel.logical_channel_assignments.assignment.append(channel_assignment)
            
            terminal_device.logical_channels.channel.append(channel)
            NUM = NUM + 1

    ## Creation of the logical number(index) for the line port of slice0
    channel = terminal_device.logical_channels.Channel()
    channel.index = 200
    ## OTN logical channel definition (OTN type, Enabled)
    channel_config = channel.Config()
    channel_config.admin_state = oc_tr_types.AdminStateTypeEnum.ENABLED
    channel_config.logical_channel_type = oc_tr_types.Prot_OtnIdentity()
    channel.config = channel_config
    ## defining the speed of that port
    channel_assignment = channel.logical_channel_assignments.Assignment()
    channel_assignment.index = 1
    channel_assignment_config = channel_assignment.Config()
    channel_assignment_config.allocation = Decimal64('200')
    channel_assignment_config.assignment_type = channel_assignment.config.\
                                                AssignmentTypeEnum.\
                                                OPTICAL_CHANNEL
    ## and mapping into the optical channel
    channel_assignment_config.optical_channel = '0/0-OpticalChannel0/0/0/6'
    channel_assignment.config = channel_assignment_config
    channel.logical_channel_assignments.assignment.append(channel_assignment)

    terminal_device.logical_channels.channel.append(channel)

    
def config_components(components):
    
    """
    Add config data for optical channels (lines) and map into real ports
    This is where you define output power and the wavelength
    """

    component = components.Component()
    component.name = '0/0-OpticalChannel0/0/0/6'
    optical_channel_config = component.optical_channel.Config()
    optical_channel_config.line_port = '0/0-Optics0/0/0/6'
    ## mode1 == FEC7%, mode 2 == FEC20%
    optical_channel_config.operational_mode = 2
    ## output power is expressed in increments of 0.01 dBm
    optical_channel_config.target_output_power = Decimal64('0')
    ## frequency of the optical channel, expressed in MHz
    optical_channel_config.frequency = 191300000
    component.optical_channel.config = optical_channel_config
    components.component.append(component) 


if __name__ == "__main__":
    """Execute main program."""
    parser = ArgumentParser()
    parser.add_argument("-v", "--verbose", help="print debugging messages",
                        action="store_true")
    parser.add_argument("device",
                        help="NETCONF device (ssh://user:password@host:port)")
    args = parser.parse_args()
    device = urlparse(args.device)

    # log debug messages if verbose argument specified
    if args.verbose:
        logger = logging.getLogger("ydk")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(("%(asctime)s - %(name)s - "
                                      "%(levelname)s - %(message)s"))
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # create NETCONF provider
    provider = NetconfServiceProvider(address=device.hostname,
                                      port=device.port,
                                      username=device.username,
                                      password=device.password,
                                      protocol=device.scheme)
    # create NETCONF service
    netconf = NetconfService()

    # create OC-interfaces object (optical channels)
    interfaces = oc_interfaces.Interfaces()
    config_interfaces(interfaces)
    
    # create OC-Terminal_device object (mapping between logical ports)
    terminal_device = oc_terminal_device.TerminalDevice()
    config_terminal_device(terminal_device)
    
    # create OC-platform object (description for optical channels)
    components = oc_platform.Components()
    config_components(components)  

    # edit configuration on NETCONF device
    # netconf.lock(provider, Datastore.candidate)
    netconf.edit_config(provider, Datastore.candidate, interfaces)
    netconf.edit_config(provider, Datastore.candidate, terminal_device)
    netconf.edit_config(provider, Datastore.candidate, components)    
    netconf.commit(provider)
    # netconf.unlock(provider, Datastore.candidate)

    exit()
# End of script

##### helpfull commands to check the status on the NCS1002:

### 'sh hw-module slice 0' to find the provisioning progress
### 'sh terminal-device layout' to check accepted configuration \
###    layout with a clear picture of logical channels and their mappings
### 'sh terminal-device logical-channel <all|number>' to check details \
###    either for all logical channels or for a specific one
### 'sh terminal-device operational-modes' to check supported operational modes
