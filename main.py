from __future__ import print_function
import pickle
import os.path
import json
import urllib
from timeit import default_timer as timer
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.group']

'''
TODOs

'''


def main():

    # return all members of group in shape of list of json objects 'members resource' (not paginated)
    # https://developers.google.com/admin-sdk/directory/v1/reference/members#resource
    def get_members_json_list(group_key, role=None):
        try:
            request = service.members().list(groupKey=group_key)  # maxResults default is 200 (200 is max)
            result = request.execute()
            members = []
            while request is not None:
                for item in result.get('members', []):
                    if role is not None:
                        if item['role'] == role:
                            members.append(item)
                    else:
                        members.append(item)
                request = service.members().list_next(request, result)
                if request is not None:
                    result = request.execute()
            return members
        except Exception as e:
            print('! Unable to get members of group {} Exception: {}'.format(group_key, e))
            return []

    # helper function, print all members (email and role) of group to console
    def print_members(group_key):
        print('\nMembers of {0}:'.format(group_key))
        members = get_members_json_list(group_key)
        for member in members:
            print('\t{0}\t{1}'.format(member['email'], member['role']))
        print('\n')

    def get_members_emails(group_key, role=None):
        # print('Getting members\' {} emails of role {}'.format(group_key, role))
        return [member['email'] for member in get_members_json_list(group_key, role=role)]

    # delete MEMBER with email 'member_key' from group
    def delete_member(group_key, member_key):
        # print('> Deleting member {} from group {}'.format(member_key, group_key))
        try:
            service.members().delete(groupKey=group_key, memberKey=member_key).execute()
        except Exception as e:
            print('! Deleting of member {} from group {} failed. Exception: {}'.format(member_key, group_key, e))

    # delete multiple members from group
    def delete_multiple_members(group_key, member_keys):
        for member_key in member_keys:
            delete_member(group_key, member_key)

    # delete members from group
    def delete_group_members(group_key, role=None):
        print('> Deleting group members {} {}'.format(group_key, role))
        delete_multiple_members(group_key, get_members_emails(group_key, role=role))

    # add member with email 'member_key' as a ROLE to group
    def add_member(group_key, member_key, role='MEMBER'):
        # print('> Adding member {} to group {}'.format(member_key, group_key))
        body = {'email': member_key, 'role': role}
        try:
            service.members().insert(groupKey=group_key, body=body).execute()
        except Exception as e:
            print('! Inserting of member {} to group {} as {} failed. Exception: {}'
                  .format(member_key, group_key, role, e))
            if role == 'OWNER':
                try:
                    print('> Updating member {} in group {} to role {}'.format(member_key, group_key, role))
                    service.members().update(groupKey=group_key, memberKey=member_key, body=body).execute()
                except Exception as e:
                    print('! Updating of member {} in group {} to role {} failed. Exception: {}'
                          .format(member_key, group_key, role, e))

    # add multiple members to group
    def add_members(group_key, member_keys, role='MEMBER'):
        print('> Adding multiple members to group {} as {} {}'.format(group_key, role, member_keys))
        for member_key in member_keys:
            add_member(group_key, member_key, role=role)

    def add_owners(group_key, member_keys):
        add_members(group_key, member_keys, role='OWNER')

    # add '@110zbor.sk' to string (group)
    def at(txt):
        return txt + '@110zbor.sk'

    def parse_groups(struct):
        try:

            # delete members of all higher groups

            for group in struct['druziny']:
                delete_group_members(at(group), role='MEMBER')
                delete_group_members(at(group + '.r'), role='OWNER')
                delete_group_members(at(group + '.d'), role='OWNER')

            for group in struct['oddiely_a_zbor_r_d']:
                delete_group_members(at(group), role='MEMBER')
                delete_group_members(at(group + '.r'))  # both MEMBERs and OWNERs
                delete_group_members(at(group + '.d'))  # both MEMBERs and OWNERs

            for group in struct['higher_groups']:
                delete_group_members(at(group), role='MEMBERS')

            # add members to higher groups r d

            for group in struct['druziny']:
                # add r&d to patrol@
                add_members(at(group), get_members_emails(at(group + '.r')) + get_members_emails(at(group + '.d')))
                # add patrol@ owners to r&d
                emails_to_add = get_members_emails(at(group), role='OWNER')
                add_members(at(group + '.r'), emails_to_add, role='OWNER')
                add_members(at(group + '.d'), emails_to_add, role='OWNER')

            for parent_group, subgroups in struct['oddiely'].items(): # for key, value in...
                # add r&d to higher group / vytovrí oddiel.r@ a oddiel.d@ z družín .r a .d
                for subgroup in subgroups:
                    add_members(at(parent_group + '.r'), get_members_emails(at(subgroup + '.r')))
                    add_members(at(parent_group + '.d'), get_members_emails(at(subgroup + '.d')))
                # add r&d to group@ / vytvorí oddiel@ z oddiel.r@ a oddiel.d@
                add_members(at(parent_group), get_members_emails(at(parent_group + '.r')) + get_members_emails(at(parent_group + '.d')))
                # add group@ owners to r&d / pridá vedúcich z oddiel@ do oddiel.d@ a oddiel.r@
                emails_to_add = get_members_emails(at(parent_group), role='OWNER')
                add_members(at(parent_group + '.r'), emails_to_add, role='OWNER')
                add_members(at(parent_group + '.d'), emails_to_add, role='OWNER')

            parent_group = 'zbor'
            for subgroup in struct['zbor']:
                # add r&d to higher group / vytovrí zbor.r@ a zbor.d@ z oddielov .r a .d
                add_members(at(parent_group + '.r'), get_members_emails(at(subgroup + '.r')))
                add_members(at(parent_group + '.d'), get_members_emails(at(subgroup + '.d')))
            # add r&d to group@ / vytvorí zbor@ z zbor.r@ a zbor.d@
            add_members(at(parent_group), get_members_emails(at(parent_group + '.r')) + get_members_emails(at(parent_group + '.d')))
            # add group@ owners to r&d / pridá vedúcich zo zbor@ do zbor.d@ a zbor.r@
            emails_to_add = get_members_emails(at(parent_group), role='OWNER')
            add_members(at(parent_group + '.r'), emails_to_add, role='OWNER')
            add_members(at(parent_group + '.d'), emails_to_add, role='OWNER')

            for parent_group, subgroups in struct['special'].items():
                for subgroup in subgroups:
                    emails_to_add = get_members_emails(at(subgroup))
                    add_members(at(parent_group), emails_to_add)

        except Exception as e:
            print('! Error while parsing group structure.\n Exception:', e)

    ##########################################################################################

    timer_start = timer()
    creds = authorize()
    service = build('admin', 'directory_v1', credentials=creds)

    # read the structure from file
    with open('structure.json') as f:
        struct = json.load(f)
    print(json.dumps(struct, indent=2, sort_keys=True))

    # parse the structure and update members
    parse_groups(struct)

    timer_end = timer()
    print('Elapsed time:', timer_end - timer_start)  # Time in seconds


# function from google quickstart.py example
def authorize():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is created automatically
    # when the authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


if __name__ == '__main__':
    main()
