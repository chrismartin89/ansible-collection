#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2022, XLAB Steampunk <steampunk@xlab.si>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
module: tag

author:
  - Domen Dobnikar (@domen_dobnikar)
short_description: Manages tags on a machines.
description: Add or remove tags from machines.
version_added: 1.0.0
extends_documentation_fragment:
  - canonical.maas.cluster_instance
seealso: []
options:
  name:
    description:
      - The new tag name.
      - Because the name will be used in urls, it should be short.
    type: str
    required: True
  machines:
    description:
      - List of MAAS machines.
      - Use FQDN.
    type: list
    elements: str
    required: True
  state:
    description: Prefered tag state.
    choices: [ present, absent, set ]
    type: str
    required: True
"""

EXAMPLES = r"""
- name: Create new tag 'one' and place it on VMs
  canonical.maas.tag:
    cluster_instance:
      host: host-ip
      token_key: token-key
      token_secret: token-secret
      customer_key: customer-key
    state: present
    name: one
    machines:
      - instance-test.maas
      - new-machine-test-tag.maas
  register: tag_list
- ansible.builtin.debug:
    var: tag_list

- name: Delete new tag 'one' and place it on VMs
  canonical.maas.tag:
    cluster_instance:
      host: host-ip
      token_key: token-key
      token_secret: token-secret
      customer_key: customer-key
    state: absent
    name: one
    machines:
      - instance-test.maas
      - new-machine-test-tag.maas
  register: tag_list
- ansible.builtin.debug:
    var: tag_list
"""

RETURN = r"""
records:
  description:
    - Machine tags.
  returned: success
  type: list
  sample:
    - machine: this_machine.maas
      tags:
        - one
        - two
        - three
    - machine: that_machine.maas
      tags:
        - one
        - four
        - five
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils import arguments, errors
from ..module_utils.utils import is_changed
from ..module_utils.cluster_instance import get_oauth1_client
from ..module_utils.state import TagState
from ..module_utils.tag import Tag
from ..module_utils.machine import Machine


def get_after(client, after):
    updated_machine_list = Machine.get_id_from_fqdn(client, *after)
    after = []
    for machine in updated_machine_list:
        after.append(dict(machine=machine.fqdn, tags=machine.tags))
    return after


def ensure_present(module, client):
    before = []
    after = []
    machine_list = Machine.get_id_from_fqdn(client, *module.params["machines"])
    existing_tag = Tag.get_tag_by_name(client, module)
    if not existing_tag:
        Tag.send_create_request(client, module)
    for machine in machine_list:
        if module.params["name"] not in machine.tags:
            before.append(dict(machine=machine.fqdn, tags=machine.tags))
            Tag.send_tag_request(client, machine.id, module.params["name"])
            after.append(machine.fqdn)
    if after:  # Get updated machines
        after = get_after(client, after)
    return is_changed(before, after), after, dict(before=before, after=after)


def ensure_absent(module, client):
    before = []
    after = []
    machine_list = Machine.get_id_from_fqdn(client, *module.params["machines"])
    existing_tag = Tag.get_tag_by_name(client, module)
    if existing_tag:
        for machine in machine_list:
            if existing_tag["name"] in machine.tags:
                before.append(dict(machine=machine.fqdn, tags=machine.tags))
                Tag.sent_untag_request(client, machine.id, module.params["name"])
                after.append(machine.fqdn)
    if after:  # Get updated machines
        after = get_after(client, after)
    return is_changed(before, after), after, dict(before=before, after=after)


def run(module, client):
    if module.params["state"] == TagState.present:
        changed, records, diff = ensure_present(module, client)
    else:
        changed, records, diff = ensure_absent(module, client)
    return changed, records, diff


def main():
    module = AnsibleModule(
        supports_check_mode=False,
        argument_spec=dict(
            arguments.get_spec("cluster_instance"),
            name=dict(
                type="str",
                required=True,
            ),
            machines=dict(
                type="list",
                required=True,
                elements="str",
            ),
            state=dict(
                type="str",
                choices=["present", "absent", "set"],
                required=True,
            ),
        ),
    )

    try:
        client = get_oauth1_client(module.params)
        changed, records, diff = run(module, client)
        module.exit_json(changed=changed, records=records, diff=diff)
    except errors.MaasError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
