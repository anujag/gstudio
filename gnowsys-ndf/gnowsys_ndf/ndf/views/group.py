''' -- imports from python libraries -- '''
# import os -- Keep such imports here
import json
import datetime

''' -- imports from installed packages -- '''
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response  # , render
from django.template import RequestContext
# from django.template.defaultfilters import slugify
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.views.generic import View

try:
    from bson import ObjectId
except ImportError:  # old pymongo
    from pymongo.objectid import ObjectId

''' -- imports from application folders/files -- '''
from gnowsys_ndf.settings import GAPPS, GSTUDIO_GROUP_AGENCY_TYPES, GSTUDIO_NROER_MENU, GSTUDIO_NROER_MENU_MAPPINGS
from gnowsys_ndf.ndf.models import NodeJSONEncoder
# from gnowsys_ndf.ndf.models import GSystemType, GSystem, Group, Triple
from gnowsys_ndf.ndf.models import node_collection, triple_collection
from gnowsys_ndf.ndf.views.ajax_views import set_drawer_widget
from gnowsys_ndf.ndf.templatetags.ndf_tags import get_all_user_groups, get_sg_member_of  # get_existing_groups
from gnowsys_ndf.ndf.views.methods import *
from gnowsys_ndf.ndf.org2any import org2html
# ######################################################################################################################################

group_gst = node_collection.one({'_type': 'GSystemType', 'name': u'Group'})
gst_group = group_gst
app = gst_group

moderating_group_gst = node_collection.one({'_type': 'GSystemType', 'name': u'ModeratingGroup'})
programevent_group_gst = node_collection.one({'_type': 'GSystemType', 'name': u'ProgramEventGroup'})
courseevent_group_gst = node_collection.one({'_type': 'GSystemType', 'name': u'CourseEventGroup'})

file_gst = node_collection.one({'_type': 'GSystemType', 'name': 'File'})
page_gst = node_collection.one({'_type': 'GSystemType', 'name': 'Page'})
task_gst = node_collection.one({'_type': 'GSystemType', 'name': 'Task'})

# ######################################################################################################################################
#      V I E W S   D E F I N E D   F O R   G A P P -- ' G R O U P '
# ######################################################################################################################################

class CreateGroup(object):
    """
    Creates group.
    Instantiate group with request as argument
    """
    def __init__(self, request):
        super(CreateGroup, self).__init__()
        self.request = request
        self.moderated_groups_member_of = ['ProgramEventGroup',\
         'CourseEventGroup', 'PartnerGroup', 'ModeratingGroup']


    def is_group_exists(self, arg_group_name):
        '''
        Checks if group with the given name exists.
        Returns Bool.
            - True: If group exists.
            - False: If group doesn't exists.
        '''
        
        # explicitely using "find_one" query
        group = node_collection.find_one({'_type': 'Group', 'name': unicode(arg_group_name)})

        if group:
            return True

        else:
            return False


    def get_group_fields(self, group_name, **kwargs):
        '''
        function to fill the empty group object with values supplied.
        - group name is must and it's first argument.
        - group information may be sent either from "request" or from "kwargs".

        # If arg is kwargs, provide following dict as kwargs arg to this function.
        group_fields = {
          'altnames': '', 'group_type': '', 'edit_policy': '',
          'agency_type': '', 'moderation_level': '',
          ...., ...
        }

        # call in following way
        class_instance_var.get_group_fields(group_name, **group_fields)
        (NOTE: use ** before dict variables, in above case it's group_fields so it's: **group_fields)
        '''

        # getting the data into variables
        name = group_name

        # to check if existing group is getting edited
        node_id = kwargs.get('node_id', None)

        if kwargs.get('altnames', ''):
            altnames = kwargs.get('altnames', name) 
        else:
            altnames = self.request.POST.get('altnames', name).strip()

        if kwargs.get('group_type', ''):
            group_type = kwargs.get('group_type', '') 
        else:
            group_type = self.request.POST.get('group_type', '')

        if kwargs.get('access_policy', ''):
            access_policy = kwargs.get('access_policy', group_type) 
        else:
            access_policy = self.request.POST.get('access_policy', group_type)

        if kwargs.get('edit_policy', ''):
            edit_policy = kwargs.get('edit_policy', '') 
        else:
            edit_policy = self.request.POST.get('edit_policy', '')

        if kwargs.get('subscription_policy', ''):
            subscription_policy = kwargs.get('subscription_policy', 'OPEN') 
        else:
            subscription_policy = self.request.POST.get('subscription_policy', "OPEN")

        if kwargs.get('visibility_policy', ''):
            visibility_policy = kwargs.get('visibility_policy', 'ANNOUNCED') 
        else:
            visibility_policy = self.request.POST.get('visibility_policy', 'ANNOUNCED')

        if kwargs.get('disclosure_policy', ''):
            disclosure_policy = kwargs.get('disclosure_policy', 'DISCLOSED_TO_MEM') 
        else:
            disclosure_policy = self.request.POST.get('disclosure_policy', 'DISCLOSED_TO_MEM')

        if kwargs.get('encryption_policy', ''):
            encryption_policy = kwargs.get('encryption_policy', 'NOT_ENCRYPTED') 
        else:
            encryption_policy = self.request.POST.get('encryption_policy', 'NOT_ENCRYPTED')

        if kwargs.get('agency_type', ''):
            agency_type = kwargs.get('agency_type', 'Other') 
        else:
            agency_type = self.request.POST.get('agency_type', 'Other')

        if kwargs.get('content_org', ''):
            content_org = kwargs.get('content_org', '')
        else:
            content_org = self.request.POST.get('content_org', '')

        # whenever we are passing int: 0, condition gets false
        # therefor casting to str
        if str(kwargs.get('moderation_level', '')):
            moderation_level = kwargs.get('moderation_level', '-1') 
        else:
            moderation_level = self.request.POST.get('moderation_level', '-1')

        if node_id:
            # Existing group: if node_id exists means group already exists.
            # So fetch that group and use same object to override the fields.
            group_obj = node_collection.one({'_id': ObjectId(node_id)})
        else:
            # New group: instantiate empty group object
            group_obj = node_collection.collection.Group()

        # filling the values with variables in group object:
        group_obj.name = unicode(name)
        group_obj.altnames = unicode(altnames)

        # while doing append operation make sure to-be-append is not in the list
        if gst_group._id not in group_obj.member_of:
            group_obj.member_of.append(gst_group._id)

        if gst_group._id not in group_obj.type_of:
            group_obj.type_of.append(gst_group._id)
      
        # user related fields:
        user_id = int(self.request.user.id)
        group_obj.created_by = user_id
        group_obj.modified_by = user_id
        if user_id not in group_obj.author_set:
            group_obj.author_set.append(user_id)
        if user_id not in group_obj.contributors:
            group_obj.contributors.append(user_id)
        if user_id not in group_obj.group_admin:
            group_obj.group_admin.append(user_id)

        # group specific fields:
        group_obj.group_type = group_type
        group_obj.access_policy = access_policy
        group_obj.edit_policy = edit_policy
        group_obj.subscription_policy = subscription_policy
        group_obj.visibility_policy = visibility_policy
        group_obj.disclosure_policy = disclosure_policy
        group_obj.encryption_policy = encryption_policy
        group_obj.agency_type = agency_type

        #  org-content
        if group_obj.content_org != content_org:
            group_obj.content_org = content_org

            # Required to link temporary files with the current user who is:
            usrname = self.request.user.username
            filename = slugify(name) + "-" + slugify(usrname) + "-" + ObjectId().__str__()
            group_obj.content = org2html(content_org, file_prefix=filename)
            is_changed = True

        # decision for adding moderation_level
        if group_obj.edit_policy == "EDITABLE_MODERATED":
            group_obj.moderation_level = int(moderation_level)
        else:
            group_obj.moderation_level = -1  # non-moderated group.

        # group's should not have draft stage. So publish them:
        group_obj.status = u"PUBLISHED"

        # returning basic fields filled group object 
        return group_obj

    # --- END --- get_group_fields() ------


    def create_group(self, group_name, **kwargs):
        '''
        Creates group with given args.
        - Takes group name as compulsory argument.
        - Returns tuple containing: (True/False, sub_group_object/error)
        '''

        node_id = kwargs.get('node_id', None)
        # print "node_id : ", node_id

        # checking if group exists with same name
        if not self.is_group_exists(group_name) or node_id:

            # print "group_name : ", group_name
            group_obj = self.get_group_fields(group_name, **kwargs)

            try:
                group_obj.save()
            except Exception, e:
                return False, e

            # group created successfully
            return True, group_obj

        else:
            return False, 'Group with same name exists.'

    # --- END --- create_group() ---


    def get_group_edit_policy(self, group_id):
        '''
        Returns "edit_policy" of the group.
        - Takes group_id as compulsory and only argument.
        - Returns: either "edit_policy" or boolian "False". 
        '''

        group_obj = node_collection.one({'_id': ObjectId(group_id)})

        if group_obj:
            return group_obj.edit_policy
            
        else:
          return False
    # --- END --- get_group_edit_policy() ------


    def get_group_type(self, group_id):
        '''
        Returns "group_type" of the group.
        - Takes group_id as compulsory and only argument.
        - Returns: either "group_type" or boolian "False". 
        '''

        group_obj = node_collection.one({'_id': ObjectId(group_id)})

        if group_obj:
            return group_obj.group_type

        else:
            return False
    # --- END --- get_group_type() ------


    def get_all_subgroups_obj_list(self, group_id):
        '''
        Returns mongokit (find) cursor of sub-group documents (only immediate first level) /
        which are in the post node of argument group_id else returns False.
        - Takes group_id as compulsory and only argument.
        '''

        group_obj = node_collection.one({'_id': ObjectId(group_id)})

        # check if group has post_node. Means it has sub-group/s
        if group_obj and group_obj.post_node:
            return node_collection.find({'_id': {'$in': group_obj.post_node} })

        else:
          return False
    # --- END --- get_all_subgroups_obj_list() ------


    def get_all_subgroups_member_of_list(self, group_id):
        '''
        Returns list of names of "member_of" of sub-groups.
        - Takes group_id as compulsory and only argument.
        '''

        sg_member_of_list = []
        # get all underlying groups
        all_sg = self.get_all_subgroups_obj_list(group_id)

        if all_sg:
            # getting parent's sub group's member_of in a list
            for each_sg in all_sg:
                sg_member_of_list += each_sg.member_of_names_list

        return sg_member_of_list
    # --- END --- get_all_subgroups_member_of_list() ------

# --- END of class CreateGroup ---
# --------------------------------


class CreateSubGroup(CreateGroup):
    """
        Create sub-group of any type
        (e.g: Moderated, Normal, programe_event, course_event)
        Instantiate group with request as argument
    """
    def __init__(self, request):
        super(CreateSubGroup, self).__init__(request)
        self.request = request

    
    def get_subgroup_fields(self, parent_group_id, sub_group_name, sg_member_of, **kwargs):
        '''
        Get empty group object filled with values supplied in arguments.
        "parent_group_id" and "sub_group_id" and "sg_member_of" are compulsory args.
        '''

        # get basic fields filled group object
        group_obj = self.get_group_fields(sub_group_name, **kwargs)

        # if sg_member_of in ['ProgramEventGroup', 'CourseEventGroup', 'PartnerGroup', 'ModeratingGroup']:
        if sg_member_of in self.moderated_groups_member_of:
            # overriding member_of field of subgroup
            member_of_group = node_collection.one({'_type': u'GSystemType', 'name': unicode(sg_member_of)})
            group_obj.member_of = [ObjectId(member_of_group._id)]

            # for subgroup's of this types, group_type must be PRIVATE and EDITABLE_MODERATED
            group_obj.group_type = 'PRIVATE'
            group_obj.access_policy = u'PRIVATE'
            group_obj.edit_policy = 'EDITABLE_MODERATED'

        else:  # for normal sub-groups
            if not group_obj.group_type:
                # if group_type is not specified take it from parent:
                group_obj.group_type = self.get_group_type(parent_group_id)

            # if not group_obj.edit_policy:
            #     group_obj.edit_policy = self.get_group_edit_policy(parent_group_id)

        # check if group object's prior_node has _id of parent group, otherwise add one.
        if ObjectId(parent_group_id) not in group_obj.prior_node:
            group_obj.prior_node.append(ObjectId(parent_group_id))

        return group_obj


    def create_subgroup(self, parent_group_id, sub_group_name, sg_member_of, **kwargs):
        '''
        Creates sub-group with given args.
        Returns tuple containing True/False, sub_group_object/error.
        '''

        try:
            parent_group_id = ObjectId(parent_group_id)

        except:
            parent_group_name, parent_group_id = get_group_name_id(group_id)

        # checking feasible conditions to add this sub-group
        if not self.check_subgroup_feasibility(parent_group_id, sg_member_of):
            return False, "It's not feasible to make sub-group with given values"

        if not self.is_group_exists(sub_group_name):

            # getting sub-group object filled with basic fields of (group + subgroup) levels
            group_obj = self.get_subgroup_fields(parent_group_id, sub_group_name, sg_member_of, **kwargs)

            try:
                group_obj.save()
            except Exception, e:
                # if any errors return tuple with False and error
                return False, e

            # after sub-group get created/saved successfully:
            self.add_subgroup_to_parents_postnode(parent_group_id, group_obj._id, sg_member_of)

            return True, group_obj
        
        else:
            return False, 'Group with same name exists.'


    def check_subgroup_feasibility(self, parent_group_id, sg_member_of):
        '''
        method to check feasibility of adding sub group to parent group 
        according to their following properties:
        - parent group's edit_policy
        - child group's member_of
        Returns True if it is OK to create sub-group with suplied fields.
        Otherwise returns False.
        '''
        if sg_member_of == 'Group':
            # i.e: group is normal-sub-group.
            return True

        # elif sg_member_of in ['ProgramEventGroup', 'CourseEventGroup', 'PartnerGroup', 'ModeratingGroup']:
        elif sg_member_of in self.moderated_groups_member_of:
            if self.get_group_edit_policy(parent_group_id) == 'EDITABLE_MODERATED':
                
                # if current sub-groups member_of is in parent's any one of the sub-group,
                # i.e: sub-group with current property exists in/for parent group.
                # And no sibling with these property can exists together (like normal sub-groups).

                if sg_member_of in self.get_all_subgroups_member_of_list(parent_group_id):
                    return False
                else:
                    return True

            else:
                return False


    def add_subgroup_to_parents_postnode(self, parent_group_id, sub_group_id, sg_member_of):
        '''
        Adding sub-group's _id in post_node of parent_group.
        '''

        # fetching parent group obj
        parent_group_object = node_collection.one({'_id': ObjectId(parent_group_id)})

        # adding sub group's id in post node of parent node
        if ObjectId(sub_group_id) not in parent_group_object.post_node:
            parent_group_object.post_node.append(ObjectId(sub_group_id))

            # adding normal sub-group to collection_set of parent group:
            if sg_member_of == 'Group':
                parent_group_object.collection_set.append(ObjectId(sub_group_id))

            parent_group_object.save()
            return True

        # sub-groups "_id" already exists in parent_group.
        return False


    def get_particular_member_of_subgroup(self, group_id, member_of):
        '''
        Returns sub-group-object having supplied particular member_of.
        Else return False
        '''
        member_of = node_collection.one({'_type': 'GSystemType', 'name': unicode(member_of)})

        group_obj = node_collection.one({
                                        '_type': 'Group',
                                        'prior_node': {'$in': [ObjectId(group_id)]},
                                        'member_of': member_of._id
                                    })

        if group_obj:
            return group_obj

        else:
            return False

# --- END of class CreateSubGroup ---
# --------------------------------


class CreateModeratedGroup(CreateSubGroup):
    """
        Creates moderated sub-groups.
        Instantiate with request.
    """
    def __init__(self, request):
        super(CreateSubGroup, self).__init__(request)
        self.request = request
        self.edit_policy = 'EDITABLE_MODERATED'
        # maintaining dict of group types and their corresponding sub-groups altnames.
        # referenced while creating new moderated sub-groups.
        self.altnames = {
            'ModeratingGroup': [u'Clearing House', u'Curation House'],
            'ProgramEventGroup': [u'Clearing House', u'Curation House'],
            'CourseEventGroup': [u'Clearing House', u'Curation House']
        }


    def create_edit_moderated_group(self, group_name, moderation_level=1, sg_member_of="ModeratingGroup", **kwargs):
        '''
        Creates/Edits top level group as well as underlying sub-mod groups.
        - Takes group_name as compulsory argument and optional kwargs.
        - Returns tuple: (True/False, top_group_object/error)
        '''

        # retrieves node_id. means it's edit operation of existing group.
        node_id = kwargs.get('node_id', None)

        # checking if group exists with same name
        if not self.is_group_exists(group_name) or node_id:

            # values will be taken from POST form fields
            group_obj = self.get_group_fields(group_name, node_id=node_id)

            try:
                group_obj.save()
            except Exception, e:
                # if any errors return tuple with False and error
                # print e
                return False, e

            if node_id:
                # i.e: Editing already existed group object.
                # method modifies the underlying mod-sub-group structure and doesn't return anything.
                self.check_reset_mod_group_hierarchy(sg_member_of=sg_member_of, top_group_obj=group_obj)

            else:
                # i.e: New group is created and following code will create
                # sub-mod-groups as per specified in the form.
                parent_group_id = group_obj._id

                for each_sg_iter in range(0, int(moderation_level)):

                    result = self.add_moderation_level(parent_group_id, sg_member_of=sg_member_of)

                    # result is tuple of (bool, newly-created-sub-group-obj)
                    if result[0]:
                        # overwritting parent's group_id with currently/newly-created group object
                        parent_group_id = result[1]._id

                    else:
                        # if result is False, means sub-group is not created.
                        # In this case, there is no point to go ahead and create subsequent sub-group.
                        break

            return True, group_obj
        
        else:
            return False, 'Group with same name exists.'


    def add_moderation_level(self, parent_group_id, sg_member_of, increment_mod_level=False):
        '''
        Adds the moderation sub group to parent group.
        - compulsory argument:
            - "_id/name" of parent
            - sub_group's "member_of": <str>.
        - increment_mod_level: If you want to add next moderation subgroup, despite of 
                    moderation_level is 0.
                    In this case, if value is True, 
                    moderation_level of all top hierarchy groups will be updated by 1.
        '''
        # getting group object
        parent_group_object = get_group_name_id(parent_group_id, get_obj=True)

        # pg: parent group
        pg_name = parent_group_object.name
        pg_moderation_level = parent_group_object.moderation_level
        # print pg_moderation_level, "===", pg_name

        # possible/next mod group name: 
        # sg: sub group
        sg_name = pg_name + unicode('_mod')

        # no need to check following here, because it's being checked at sub-group creation time.
        # but keep this following code for future perspective.
        # 
        # if self.is_group_exists(sg_name):
        #     # checking for group with name exists
        #     return False, 'Group with name: ' + sg_name + ' exists.'

        # elif not self.check_subgroup_feasibility(sg_member_of):
        #     # checking if any of the sub-group has same member_of field.
        #     return False, 'Sub-Group with type of group' + sg_member_of + ' exists.'

        if (pg_moderation_level == 0) and not increment_mod_level:
            # if parent_group's moderation_level is reached to leaf; means to 0. Then return False

            return False, 'Parent group moderation level is: ' + pg_moderation_level \
             + '. So, further moderation group cannot be created!'

        elif (pg_moderation_level > 0) or increment_mod_level:
            # valid condition to create a sub group

            if (pg_moderation_level == 0) and increment_mod_level:
                # needs to increase moderation_level of all group hierarchy
                self.increment_hierarchy_mod_level(parent_group_id, sg_member_of)
                pg_moderation_level += 1

            try:
                result = self.get_top_group_of_hierarchy(parent_group_object._id)
                altnames_dict_index = -1
                if result:
                    top_group_obj = result[1]
                    top_group_moderation_level = top_group_obj.moderation_level
                    pg_name = top_group_obj.name
                    altnames_dict_index = top_group_moderation_level - pg_moderation_level
                sg_altnames = self.altnames[sg_member_of][altnames_dict_index] \
                                + u" of " + pg_name
                # print "=== in try", sg_altnames
            except Exception, e:
                # print e
                sg_altnames = sg_name
                # print "=== in Exception", sg_altnames

            # create new sub-group and append it to parent group:
            sub_group_result_tuple = self.create_subgroup(parent_group_id, sg_name, \
              sg_member_of, moderation_level=(pg_moderation_level-1), \
               altnames=sg_altnames)

            # print "\n=== sub_group_result_tuple", sub_group_result_tuple
            return sub_group_result_tuple


    def increment_hierarchy_mod_level(self, group_id, sg_member_of):
        '''
        Raises moderation_level by one of all the groups (right from top) in the hierarchy.
        Takes group_id as compulsory argument.
        Returns boolian True/False, depending on Success/Failure.
        '''

        try:
            group_id = ObjectId(group_id)
        except:
            group_name, group_id = get_group_name_id(group_id)

        # firstly getting all the sub-group-object list
        result = self.get_all_group_hierarchy(group_id, sg_member_of=sg_member_of)

        if result[0]:
            # get group's object's list into variables
            group_list = result[1]
            # flag
            is_updated = False

            for each_group in group_list:

                # change flag to True
                is_updated = True

                # adding +1 to existing moderation_level
                updated_moderation_level = each_group.moderation_level + 1

                node_collection.collection.update({'_id': each_group._id},
                            {'$set': {'moderation_level': updated_moderation_level } },
                            upsert=False, multi=False )

            if is_updated:
                return True

            else:
                return False

        # something went wrong to get group list
        else:
            return False


    def get_all_group_hierarchy(self, group_id, sg_member_of, top_group_obj=None, with_deleted=False):
        '''
        Provide _id of any of the group in the hierarchy and get list of all groups.
        Order will be from top to bottom.
        Arguments it takes:
            - "group_id": Takes _id of any of the group among hierarchy
            - "top_group_obj":  Takes object of top group (optional).
                                To be used in certain conditions.
            - "with_deleted":   Takes boolean value.
                                If it's True - returns all the groups irrespective of:
                                post_node and status field whether it's deleted or not.
                                To be used cautiously in certain conditions.
        e.g: [top_gr_obj, sub_gr_obj, sub_sub_gr_obj, ..., ...]
        NOTE: this function will return hierarchy of 
        only groups with edit_policy: 'EDITABLE_MODERATED'
        '''
        # It will be good to go through proper flow.
        # Despite of either argument of top_group_obj is provided or not.
        # That's why using following step:
        result = self.get_top_group_of_hierarchy(group_id)

        if result[0]:
            # getting object of top group
            top_group = result[1]

        elif top_group_obj:
            # if top group is in args and result if negative.
            top_group = top_group_obj

        else:
            # fail to get top group
            return result

        # starting list with top-group's object:
        all_sub_group_list = [top_group]

        # taking top_group's object in group_obj. which will be used to start while loop
        group_obj = top_group

        # loop till overwritten group_obj exists and
        # if group_obj.post_node exists or with_deleted=True
        while group_obj and (group_obj.post_node or with_deleted):

            # getting previous group objects name before it get's overwritten
            temp_group_obj_name = group_obj.name
            group_obj = self.get_particular_member_of_subgroup(group_obj._id, sg_member_of)

            # if in the case group_obj doesn't exists and with_deleted=True
            if with_deleted and not group_obj:

                try:
                    temp_group_name = unicode(group_obj_name + '_mod')
                except:
                    temp_group_name = unicode(temp_group_obj_name + '_mod')

                # firing named query here. with the rule of group names are unique and cannot be edited.
                group_obj = node_collection.one({'_type': u'Group',
                    'name': temp_group_name})

                # required to break the while loop along with with_deleted=True
                if not group_obj:
                    return True, all_sub_group_list

            # group object found with regular conditions
            if group_obj:
                group_obj_name = group_obj.name
                all_sub_group_list.append(group_obj)
            # group object not found with regular conditions and arg: with_deleted=False (default val)
            else:
                # return partially-completed/incompleted (at least with top-group-obj) group hierarchy list.
                return False, all_sub_group_list

        # while loop completed. now return computed list
        return True, all_sub_group_list


    def get_top_group_of_hierarchy(self, group_id):
        '''
        For getting top group object of hierarchy.
        Arguments:
        - group_id: _id of any of the group in the hierarchy.
        Returns top-group-object.
        '''
        curr_group_obj = node_collection.one({'_id': ObjectId(group_id)})

        # loop till there is no end of prior_node or till reaching at top group.
        while curr_group_obj and curr_group_obj.prior_node:

            # fetching object having curr_group_obj in it's prior_node:
            curr_group_obj = node_collection.one({'_id': curr_group_obj.prior_node[0]})

            # hierarchy does exists for 'EDITABLE_MODERATED' groups.
            # if edit_policy of fetched group object is not 'EDITABLE_MODERATED' return false.
            if curr_group_obj.edit_policy != 'EDITABLE_MODERATED':
                return False, "One of the group: " + str(curr_group_obj._id) \
                 + " is not with edit_policy: EDITABLE_MODERATED."
            
        # send overwritten/first curr_group_obj's "_id"
        return True, curr_group_obj


    def check_reset_mod_group_hierarchy(self, top_group_obj, sg_member_of):
        '''
        This is the method to reset/adjust all the group objects in the hierarchy,
        right from top group to last group.
        Method works-on/reset's/updates following fields of group object \
        according to top group object's fields:
            - moderation_level
            - post_node
            - status
            - altnames
            - member_of
        NOTE: "prior_node" is not updated or not taken into consideration.
              can be used in future/in-some-cases.
        Argument:
            - top_group_obj: Top group's object
        '''

        # instantiate variable group_moderation_level.
        # used for setting moderation_level of all groups
        group_moderation_level = 0

        # last sub-groups _id
        last_sg_id = top_group_obj._id

        # getting all the group hierarchy irrespective of
        # it's fields like post_node, moderation_level, status
        result = self.get_all_group_hierarchy(top_group_obj._id, \
            sg_member_of=sg_member_of, top_group_obj=top_group_obj, with_deleted=True)

        if result[0]:

            # getting all the group objects hierarchy in the list:
            all_sub_group_obj_list = result[1]
            # Zero index of all_sub_group_obj_list is top-group.

            # print [g.name for g in all_sub_group_obj_list]

            top_group_moderation_level = top_group_obj.moderation_level
            top_group_name = top_group_obj.name

            # overwritting group_moderation_level
            group_moderation_level = top_group_moderation_level

            # checking moderation_level hierarchy lists of:
            # - list created from iterating over all_sub_group_obj_list and 
            # - list created from range starts from top_group_obj's moderation_level till 0.
            # if these both are same then there is no point in going ahead and do processing.
            # bacause there is no changes in the underlying heirarchy.
            # So return from here if both lists are equal.
            # ml: moderation_level
            if [ml.moderation_level for ml in all_sub_group_obj_list] == \
            [m for m in range(top_group_moderation_level, -1, -1)]:
                # print "=== return"
                return

            # looping through each group object of/in \
            # all_sub_group_obj_list with current iteration index:
            for index, each_sg in enumerate(all_sub_group_obj_list):
                # print "\n=== group_moderation_level : ", group_moderation_level
                # print each_sg.moderation_level, "=== each_sg name : ", each_sg.name

                # getting immediate parent group of current iterated group w.r.t. all_sub_group_obj_list
                # pg: parent group
                pg_obj = all_sub_group_obj_list[index - 1] if (index > 0) else top_group_obj
                pg_id = pg_obj._id
                pg_name = pg_obj.name

                # even we need to update altnames field \
                 # w.r.t. altnames dict (defined at class level variable)
                try:
                    sg_altnames = self.altnames[sg_member_of][index-1] \
                                    + u" of " + top_group_name
                except Exception, e:
                    # if not found in altnames dict (defined at class level variable)
                    sg_altnames = each_sg.name

                # do not update altnames field of top group w.r.t altnames dict and 
                # keep Group gst's id in member_of of top-group's object:
                if each_sg._id == top_group_obj._id:
                    sg_altnames = each_sg.altnames
                    member_of_id = group_gst._id
                else:
                    if sg_member_of == "ModeratingGroup":
                        member_of_id = moderating_group_gst._id
                    elif sg_member_of == "ProgramEventGroup":
                        member_of_id = programevent_group_gst._id
                    elif sg_member_of == "CourseEventGroup":
                        member_of_id = courseevent_group_gst._id

                # print "=== altnames: ", sg_altnames

                if group_moderation_level > 0:
                    # print "=== level > 0", each_sg.name

                    node_collection.collection.update({'_id': each_sg._id},
                        {'$set': {
                            'altnames': sg_altnames,
                            'member_of': [member_of_id],
                            'moderation_level': group_moderation_level,
                            'status': u'PUBLISHED'
                            } 
                        },
                        upsert=False, multi=False )
                        
                    # except top-group, add current group's _id in top group's post_node
                    if pg_id != each_sg._id:
                        self.add_subgroup_to_parents_postnode(pg_id, each_sg._id, sg_member_of)

                    # one group/element of all_sub_group_obj_list is processed now \
                    # decrement group_moderation_level by 1:
                    group_moderation_level -= 1

                    # update last_sg variables:
                    last_sg_id = each_sg._id
                    last_sg_moderation_level = each_sg.moderation_level

                elif group_moderation_level == 0:
                    # only difference in above level>0 and this level==0 is:
                    #   last/leaf group-node (w.r.t. top_group_object.moderation_level) \
                    #   of hierarchy should not have post_node.

                    # print "=== level == 0", each_sg.name
                    node_collection.collection.update({'_id': each_sg._id},
                        {'$set': {
                            'altnames': sg_altnames,
                            'member_of': [member_of_id],
                            'moderation_level': group_moderation_level,
                            'status': u'PUBLISHED',
                            'post_node': []
                            }
                        },
                        upsert=False, multi=False )
                    # except top-group, add current group's _id in top group's post_node
                    if pg_id != each_sg._id:
                        self.add_subgroup_to_parents_postnode(pg_id, each_sg._id, sg_member_of)

                    # one group/element of all_sub_group_obj_list is processed now \
                    # decrement group_moderation_level by 1:
                    group_moderation_level -= 1

                    # update last_sg variables:
                    last_sg_id = each_sg._id
                    last_sg_moderation_level = each_sg.moderation_level

                elif group_moderation_level < 0:
                    # Now these/this are/is already created underlying moderated group's in the hierarchy.
                    # We do need to update following fields of this group object:
                    #     - moderation_level: -1
                    #     - status: u"DELETED"
                    #     - member_of: [<_id of Group gst>]
                    #     - post_node: []

                    # While doing above process, resources in these/this group need to be freed.
                    # So, fetching all the resources in this group and publishing them to top-group

                    # print "=== level < 0", each_sg.name

                    # getting all the resources (of type: File, Page, Task) under this group:
                    group_res_cur = node_collection.find({
                        'member_of': {'$in': [file_gst._id, page_gst._id, task_gst._id]},
                        'group_set': {'$in': [each_sg._id]} })

                    # iterating over each resource under this group:
                    for each_group_res in group_res_cur:

                        group_set = each_group_res.group_set

                        # removing current sub-groups _id from group_set:
                        if each_sg._id in group_set:
                            group_set.pop(group_set.index(each_sg._id))

                        # adding top-group's _id in group_set:
                        if top_group_obj._id not in group_set:
                            group_set.append(top_group_obj._id)

                        each_group_res.group_set = group_set
                        each_group_res.status = u'PUBLISHED'
                        each_group_res.save()

                    # updating current sub-group with above stated changes:
                    node_collection.collection.update({
                        '_id': each_sg._id},
                        {'$set': {
                            'member_of': [group_gst._id],
                            'status': u'DELETED',
                            'moderation_level': -1,
                            'post_node': []
                            }
                        }, upsert=False, multi=False )

                    # updating last_sg variables
                    last_sg_id = each_sg._id
                    last_sg_moderation_level = each_sg.moderation_level

        # print "out of for === group_moderation_level", group_moderation_level

        # despite of above looping and iterations, group_moderation_level is > 0 \
        # i.e: new moderated sub-group/s need to be created. (moderation level of parent group has raised).
        if group_moderation_level >= 0:

            # range(0, 0) will results: [] and range(0, 1) will results: [0]
            # hence, group_moderation_level is need to be increased by 1
            for each_sg_iter in range(0, group_moderation_level+1):

                # print each_sg_iter, " === each_sg_iter", last_sg_id
                result = self.add_moderation_level(last_sg_id, sg_member_of=sg_member_of)
                # result is tuple of (bool, newly-created-sub-group-obj)

                if result[0]:
                    last_sg_id = result[1]._id
                    # print " === new group created: ", result[0].name

                else:
                    # if result is False, means sub-group is not created.
                    # In this case, there is no point to go ahead and create subsequent sub-group.
                    break

# --- END of class CreateModeratedGroup ---
# -----------------------------------------



class CreateEventGroup(CreateModeratedGroup):
    """
        Creates moderated event sub-groups.
        Instantiate with request.
    """

    def __init__(self, request):
        super(CreateEventGroup, self).__init__(request)
        self.request = request

    def set_event_and_enrollment_dates(self, request, group_id):
        '''
        Sets Start-Date, End-Date, Start-Enroll-Date, End-Enroll-Date
        - Takes required dates from request object.
        - Returns tuple: (True/False, top_group_object/error)
        '''

        # retrieves node_id. means it's edit operation of existing group.
        group_obj = node_collection.one({'_id': ObjectId(group_id)})

        # if "ProgramEventGroup" not in group_obj.member_of_names_list:
        #     node_collection.collection.update({'_id': group_obj._id},
        #         {'$push': {'member_of': ObjectId(programevent_group_gst._id)}}, upsert=False, multi=False)
        #     group_obj.reload()
        try:
            start_date_val = self.request.POST.get('event_start_date','')
            if start_date_val:
                start_date_val = datetime.strptime(start_date_val, "%d/%m/%Y")
            end_date_val = self.request.POST.get('event_end_date','')
            if end_date_val:
                end_date_val = datetime.strptime(end_date_val, "%d/%m/%Y")

            start_enroll_val = self.request.POST.get('event_start_enroll_date','')
            if start_enroll_val:
                start_enroll_val = datetime.strptime(start_enroll_val, "%d/%m/%Y")

            end_enroll_val = self.request.POST.get('event_end_enroll_date','')
            if end_enroll_val:
                end_enroll_val = datetime.strptime(end_enroll_val, "%d/%m/%Y")

            start_date_AT = node_collection.one({'_type': "AttributeType", 'name': "start_time"})
            end_date_AT = node_collection.one({'_type': "AttributeType", 'name': "end_time"})

            start_enroll_AT = node_collection.one({'_type': "AttributeType", 'name': "start_enroll"})
            end_enroll_AT = node_collection.one({'_type': "AttributeType", 'name': "end_enroll"})

            create_gattribute(group_obj._id, start_date_AT, start_date_val)
            create_gattribute(group_obj._id, end_date_AT, end_date_val)
            create_gattribute(group_obj._id, start_enroll_AT, start_enroll_val)
            create_gattribute(group_obj._id, end_enroll_AT, end_enroll_val)

            return True, group_obj

        except Exception as e:
            return False, 'Cannot Set Dates to EventGroup.' + str(e)


# --- END of class CreateEventGroup ---
# -----------------------------------------

class CreateProgramEventGroup(CreateEventGroup):
    """
        Creates ProgramEvent sub-groups.
        Instantiate with request.
    """

    def __init__(self, request):
        super(CreateProgramEventGroup, self).__init__(request)
        self.request = request


# --- END of class CreateProgramEventGroup ---
# -----------------------------------------

class CreateCourseEventGroup(CreateEventGroup):
    """
        Creates CourseEvent sub-groups.
        Instantiate with request.
    """

    def __init__(self, request):
        super(CreateCourseEventGroup, self).__init__(request)
        self.request = request

    def initialize_course_event_structure(self, request, group_id):
        course_node_id = request.POST.get('course_node_id', '')
        if course_node_id:
            course_node = node_collection.one({'_id': ObjectId(course_node_id)})
            rt_group_has_course_event = node_collection.one({'_type': "RelationType", 'name': "group_has_course_event"})
            group_obj = node_collection.one({'_id': ObjectId(group_id)})
            create_grelation(group_obj._id, rt_group_has_course_event, course_node._id)
            self.ce_set_up(request, course_node, group_obj)
            if "CourseEventGroup" not in group_obj.member_of_names_list:
                node_collection.collection.update({'_id': group_obj._id},
                    {'$push': {'member_of': ObjectId(courseevent_group_gst._id)}}, upsert=False, multi=False)
                group_obj.reload()

    def ce_set_up(self, request, node, group_obj):
        """
            Recursive function to fetch from Course'collection_set
            and build new GSystem for CourseEventGroup
        """
        try:
            section_event_gst = node_collection.one({'_type': "GSystemType", 'name': "CourseSectionEvent"})
            subsection_event_gst = node_collection.one({'_type': "GSystemType", 'name': "CourseSubSectionEvent"})
            forum_gst = node_collection.one({'_type': "GSystemType", 'name': "Forum"})
            twist_gst = node_collection.one({'_type': "GSystemType", 'name': "Twist"})
            page_gst = node_collection.one({'_type': "GSystemType", 'name': "Page"})
            sitename = Site.objects.all()[0].name.__str__()
            user_id = request.user.id
            if node.collection_set:
                for each in node.collection_set:
                    each_node = node_collection.one({'_id': ObjectId(each)})
                    if "CourseSection" in each_node.member_of_names_list:
                        name_arg = each_node.name
                        new_cse = self.create_corresponding_gsystem(name_arg,section_event_gst,user_id, group_obj)
                        if each_node.collection_set:
                            for each_ss in each_node.collection_set:
                                each_ss_node = node_collection.one({'_id': ObjectId(each_ss)})
                                if "CourseSubSection" in each_ss_node.member_of_names_list:
                                    name_arg = each_ss_node.name
                                    new_csse = self.create_corresponding_gsystem(name_arg,subsection_event_gst,user_id, new_cse)
                                    if each_ss_node.collection_set:
                                        for each_cu in each_ss_node.collection_set:
                                            each_cu_node = node_collection.one({'_id': ObjectId(each_cu)})
                                            if "CourseUnit" in each_cu_node.member_of_names_list:
                                                name_arg = each_cu_node.name
                                                new_cu = self.create_corresponding_gsystem(name_arg,forum_gst,user_id, new_csse)
                                                new_cu.group_set.append(group_obj._id)
                                                new_cu.save()
                                                if each_cu_node.collection_set:
                                                    for each_res in each_cu_node.collection_set:
                                                        each_res_node = node_collection.one({'_id': ObjectId(each_res)})
                                                        name_arg = each_res_node.name
                                                        new_res = self.create_corresponding_gsystem(name_arg,twist_gst,user_id, new_cu)
                                                        if "Page" in each_res_node.member_of_names_list:
                                                            new_res.content = each_res_node.content
                                                            new_res.content_org = each_res_node.content_org
                                                            new_res.save()
                                                        elif "File" in each_res_node.member_of_names_list:
                                                            if "mime_type" in each_res_node:
                                                                if "image" in each_res_node.mime_type:
                                                                    content_org = u"[["+"http://"+sitename+"/"+group_obj.name+"/file/readDoc/"+str(each_res_node._id)+"/"+each_res_node.name+"]]"
                                                                elif "video" in each_res_node.mime_type:
                                                                    content_org = u'#+BEGIN_HTML \r\n\r\n<video width="600" height="400" controls>\r\n  <source src="http://'+ sitename + '/' + group_obj.name+'/video/fullvideo/'+str(each_res_node._id)+ \
                                                                    '" type="video/webm">\r\n \r\n  Your browser does not support HTML5 video.\r\n</video>\r\n\r\n#+END_HTML\r\n'
                                                            new_res.content_org = unicode(content_org)
                                                            new_res.content = org2html(content_org, file_prefix=ObjectId().__str__())
                                                            new_res.save()
            return True
        except Exception as e:

            print e, "CourseEventGroup structure setup Error"

    def create_corresponding_gsystem(self,gs_name,gs_member_of,user_id,gs_under_coll_set_of_obj):

        try:
            new_gsystem = node_collection.collection.GSystem()
            new_gsystem.name = unicode(gs_name)
            new_gsystem.member_of.append(gs_member_of._id)
            new_gsystem.modified_by = int(user_id)
            new_gsystem.created_by = int(user_id)
            new_gsystem.contributors.append(int(user_id))
            new_gsystem.save()
            gs_under_coll_set_of_obj.collection_set.append(new_gsystem._id)
            gs_under_coll_set_of_obj.save()
            new_gsystem.prior_node.append(gs_under_coll_set_of_obj._id)
            new_gsystem.save()
            return new_gsystem
        except:
            return False


# --- END of class CreateCourseEventGroup ---
# -----------------------------------------


class GroupCreateEditHandler(View):
    """
    Class to handle create/edit group requests.
    This class should handle all the types ofgroup create/edit requests.
    Currently it supports the functionality for following types of groups:
        - Normal Groups
        - Moderating Groups
        - Pending:
            -- Sub Groups
            -- CourseEvent Group
            -- ProgramEvent Group
    """
    @method_decorator(login_required)
    @method_decorator(get_execution_time)
    def get(self, request, group_id, action):
        """
        Catering GET request of group's create/edit.
        Render's to create_group template.
        """
        try:
            group_id = ObjectId(group_id)
        except:
            group_name, group_id = get_group_name_id(group_id)

        group_obj = None
        nodes_list = []

        if action == "edit":  # to edit existing group

            group_obj = get_group_name_id(group_id, get_obj=True)

            # as group edit will not have provision to change name field.
            # there is no need to send nodes_list while group edit.

        elif action == "create":  # to create new group

            available_nodes = node_collection.find({'_type': u'Group'}, {'name': 1, '_id': 0})
            # making list of group names (to check uniqueness of the group):
            nodes_list = [str(g_obj.name.strip().lower()) for g_obj in available_nodes]
            # print nodes_list
        # why following logic exists? Do we need so?
        # if group_obj.status == u"DRAFT":
        #     group_obj, ver = get_page(request, group_obj)
        #     group_obj.get_neighbourhood(group_obj.member_of)

        title = action + ' Group'

        # In the case of need, we can simply replace:
        # "ndf/create_group.html" with "ndf/edit_group.html"
        return render_to_response("ndf/create_group.html",
                                    {
                                        'node': group_obj, 'title': title,
                                        'nodes_list': nodes_list,
                                        'groupid': group_id, 'group_id': group_id
                                        # 'appId':app._id, # 'is_auth_node':is_auth_node
                                      }, context_instance=RequestContext(request))
    # --- END of get() ---

    @method_decorator(login_required)
    @method_decorator(get_execution_time)
    def post(self, request, group_id, action):
        '''
        To handle post request of group form.
        To save edited or newly-created group's data.
        '''

        # getting group's object:
        group_obj = get_group_name_id(group_id, get_obj=True)

        # getting field values from form:
        group_name = request.POST.get('name', '').strip()  # hidden-form-field
        node_id = request.POST.get('node_id', '').strip()  # hidden-form-field
        edit_policy = request.POST.get('edit_policy', '')
        # check if group's editing policy is already 'EDITABLE_MODERATED' or
        # it was not and now it's changed to 'EDITABLE_MODERATED' or vice-versa.
        if (edit_policy == "EDITABLE_MODERATED") or (group_obj.edit_policy == "EDITABLE_MODERATED"):

            moderation_level = request.POST.get('moderation_level', '')
            # print "~~~~~~~ ", moderation_level

            # instantiate moderated group
            mod_group = CreateModeratedGroup(request)

            # calling method to create new group
            result = mod_group.create_edit_moderated_group(group_name, moderation_level, "ModeratingGroup", node_id=node_id)

        else:

            # instantiate regular group
            group = CreateGroup(request)

            # calling method to create new group
            result = group.create_group(group_name, node_id=node_id)

        # print result[0], "\n=== result : ", result[1].name, "\n\n"
        if result[0]:
            # operation success: redirect to group-detail page
            group_obj = result[1]
            group_name = group_obj.name
            url_name = 'groupchange'

        else:
            # operation fail: redirect to group-listing
            group_name = 'home'
            url_name = 'group'

        return HttpResponseRedirect( reverse( url_name, kwargs={'group_id': group_name} ) )

# ===END of class EditGroup() ===
# -----------------------------------------

class EventGroupCreateEditHandler(View):
    """
    Class to handle create/edit group requests.
    Currently it supports the functionality for following types of groups:
        - CourseEvent Group
        - ProgramEvent Group
    """
    @method_decorator(login_required)
    @method_decorator(get_execution_time)
    def get(self, request, group_id, action, sg_type):
        """
        Catering GET request of group's create/edit.
        Render's to create_group template.
        """
        try:
            group_id = ObjectId(group_id)
        except:
            group_name, group_id = get_group_name_id(group_id)
        course_node_id = request.GET.get('cnode_id', '')
        group_obj = None
        nodes_list = []
        spl_group_type = sg_type
        # spl_group_type = request.GET.get('sg_type','')
        # print "\n\n spl_group_type", spl_group_type

        if action == "edit":  # to edit existing group

            group_obj = get_group_name_id(group_id, get_obj=True)
            # as group edit will not have provision to change name field.
            # there is no need to send nodes_list while group edit.

        elif action == "create":  # to create new group

            available_nodes = node_collection.find({'_type': u'Group'}, {'name': 1, '_id': 0})

            # making list of group names (to check uniqueness of the group):
            nodes_list = [str(g_obj.name.strip().lower()) for g_obj in available_nodes]

        title = action + ' ' + spl_group_type

        # In the case of need, we can simply replace:
        # "ndf/create_group.html" with "ndf/edit_group.html"
        return render_to_response("ndf/create_event_group.html",
                                    {
                                        'node': group_obj, 'title': title,
                                        'nodes_list': nodes_list,
                                        'spl_group_type': spl_group_type,
                                        'course_node_id': course_node_id,
                                        'groupid': group_id, 'group_id': group_id
                                        # 'appId':app._id, # 'is_auth_node':is_auth_node
                                      }, context_instance=RequestContext(request))
    # --- END of get() ---

    @method_decorator(login_required)
    @method_decorator(get_execution_time)
    def post(self, request, group_id, action, sg_type):
        '''
        To handle post request of group form.
        To save edited or newly-created group's data.
        '''
        group_obj = get_group_name_id(group_id, get_obj=True)

        # getting field values from form:
        group_name = request.POST.get('name', '').strip()  # hidden-form-field
        node_id = request.POST.get('node_id', '').strip()  # hidden-form-field
        edit_policy = request.POST.get('edit_policy', '')
        course_node_id = request.POST.get('course_node_id', '')

        # check if group's editing policy is already 'EDITABLE_MODERATED' or
        # it was not and now it's changed to 'EDITABLE_MODERATED' or vice-versa.
        if (edit_policy == "EDITABLE_MODERATED") or (group_obj.edit_policy == "EDITABLE_MODERATED"):

            moderation_level = request.POST.get('moderation_level', '')
            # instantiate moderated group
            if sg_type == "ProgramEventGroup":
                mod_group = CreateProgramEventGroup(request)
            elif sg_type == "CourseEventGroup":
                mod_group = CreateCourseEventGroup(request)
                moderation_level = -1
            parent_group_obj = group_obj
            # calling method to create new group
            result = mod_group.create_edit_moderated_group(group_name, moderation_level, sg_type, node_id=node_id,)
        if result[0]:
            # operation success: create ATs
            group_obj = result[1]
            parent_group_obj.post_node.append(group_obj._id)
            group_obj.prior_node.append(parent_group_obj._id)
            group_obj.save()
            parent_group_obj.save()
            date_result = mod_group.set_event_and_enrollment_dates(request, group_obj._id)
            if date_result[0]:
                # Successfully had set dates to EventGroup
                if sg_type == "CourseEventGroup":
                    mod_group.initialize_course_event_structure(request, group_obj._id)
                group_name = group_obj.name
                url_name = 'groupchange'
            else:
                # operation fail: redirect to group-listing
                group_name = 'home'
                url_name = 'group'
        else:
            # operation fail: redirect to group-listing
            group_name = 'home'
            url_name = 'group'

        return HttpResponseRedirect(reverse(url_name, kwargs={'group_id': group_name}))

# ===END of class EventGroupCreateEditHandler() ===
# -----------------------------------------


@get_execution_time
def group(request, group_id, app_id=None, agency_type=None):
  """Renders a list of all 'Group-type-GSystems' available within the database.
  """

  try:
      group_id = ObjectId(group_id)
  except:
      group_name, group_id = get_group_name_id(group_id)

  query_dict = {}
  if (app_id == "agency_type") and (agency_type in GSTUDIO_GROUP_AGENCY_TYPES):
    query_dict["agency_type"] = agency_type
  # print "=========", app_id, agency_type

  group_nodes = []
  group_count = 0
  auth = node_collection.one({'_type': u"Author", 'name': unicode(request.user.username)})

  if request.method == "POST":
    # Page search view
    title = gst_group.name
    
    search_field = request.POST['search_field']

    if auth:
      # Logged-In View
      cur_groups_user = node_collection.find({'_type': "Group", 
                                       '_id': {'$nin': [ObjectId(group_id), auth._id]},
                                       '$and': [query_dict],
                                       '$or': [
                                          {'$and': [
                                            {'name': {'$regex': search_field, '$options': 'i'}},
                                            {'$or': [
                                              {'created_by': request.user.id}, 
                                              {'group_admin': request.user.id},
                                              {'author_set': request.user.id},
                                              {'group_type': 'PUBLIC'} 
                                              ]
                                            }                                  
                                          ]
                                          },
                                          {'$and': [
                                            {'tags': {'$regex':search_field, '$options': 'i'}},
                                            {'$or': [
                                              {'created_by': request.user.id}, 
                                              {'group_admin': request.user.id},
                                              {'author_set': request.user.id},
                                              {'group_type': 'PUBLIC'} 
                                              ]
                                            }                                  
                                          ]
                                          }, 
                                        ],
                                        'name': {'$nin': ["home"]},
                                   }).sort('last_update', -1)

      if cur_groups_user.count():
        #loop replaced by a list comprehension
        group_nodes=[group for group in cur_groups_user]

      group_count = cur_groups_user.count()
        
    else:
      # Without Log-In View
      cur_public = node_collection.find({'_type': "Group", 
                                       '_id': {'$nin': [ObjectId(group_id)]},
                                       '$and': [query_dict],
                                       '$or': [
                                          {'name': {'$regex': search_field, '$options': 'i'}}, 
                                          {'tags': {'$regex':search_field, '$options': 'i'}}
                                        ],
                                        'name': {'$nin': ["home"]},
                                        'group_type': "PUBLIC"
                                   }).sort('last_update', -1)
  
      if cur_public.count():
        #loop replaced by a list comprehension
        group_nodes=[group for group in cur_public]
      group_count = cur_public.count()

    return render_to_response("ndf/group.html",
                              {'title': title,
                               'appId':app._id, 'app_gst': group_gst,
                               'searching': True, 'query': search_field,
                               'group_nodes': group_nodes, 'group_nodes_count': group_count,
                               'groupid':group_id, 'group_id':group_id
                              }, 
                              context_instance=RequestContext(request)
    )

  else: # for GET request

    if auth:
      # Logged-In View
      cur_groups_user = node_collection.find({'_type': "Group", 
                                              '$and': [query_dict],
                                              '_id': {'$nin': [ObjectId(group_id), auth._id]},
                                              'name': {'$nin': ["home"]},
                                              '$or': [
                                                      {'created_by': request.user.id},
                                                      {'author_set': request.user.id},
                                                      {'group_admin': request.user.id},
                                                      {'group_type': 'PUBLIC'}
                                                    ]
                                            }).sort('last_update', -1)
      # if cur_groups_user.count():
      #   for group in cur_groups_user:
      #     group_nodes.append(group)

      if cur_groups_user.count():
        group_nodes = cur_groups_user
        group_count = cur_groups_user.count()
        
    else:
      # Without Log-In View
      cur_public = node_collection.find({'_type': "Group", 
                                         '_id': {'$nin': [ObjectId(group_id)]},
                                         '$and': [query_dict],
                                         'name': {'$nin': ["home"]},
                                         'group_type': "PUBLIC"
                                     }).sort('last_update', -1)
  
      # if cur_public.count():
      #   for group in cur_public:
      #     group_nodes.append(group)
  
      if cur_public.count():
        group_nodes = cur_public
        group_count = cur_public.count()
    
    return render_to_response("ndf/group.html", 
                              {'group_nodes': group_nodes,
                               'appId':app._id, 'app_gst': group_gst,
                               'group_nodes_count': group_count,
                               'groupid': group_id, 'group_id': group_id
                              }, context_instance=RequestContext(request))


# @login_required
# @get_execution_time
# def create_group(request, group_id):

#   try:
#       group_id = ObjectId(group_id)
#   except:
#       group_name, group_id = get_group_name_id(group_id)

#   if request.method == "POST":

#     cname = request.POST.get('name', "").strip()
#     edit_policy = request.POST.get('edit_policy', "")
#     group_type = request.POST.get('group_type', "")
#     moderation_level = request.POST.get('moderation_level', '1')

#     if request.POST.get('edit_policy', "") == "EDITABLE_MODERATED":

#         # instantiate moderated group
#         mod_group = CreateModeratedGroup(request)

#         # calling method to create new group
#         result = mod_group.create_edit_moderated_group(cname, moderation_level)
        
#     else:

#         # instantiate moderated group
#         group = CreateGroup(request)

#         # calling method to create new group
#         result = group.create_group(cname)
        
#     if result[0]:
#         colg = result[1]

#     # auth = node_collection.one({'_type': 'Author', 'name': unicode(request.user.username) }) 

#     # has_shelf_RT = node_collection.one({'_type': 'RelationType', 'name': u'has_shelf' })

#     shelves = []
#     shelf_list = {}
    
#     # if auth:
#     #   shelf = triple_collection.find({'_type': 'GRelation', 'subject': ObjectId(auth._id), 'relation_type.$id': has_shelf_RT._id })

#     #   if shelf:
#     #     for each in shelf:
#     #       shelf_name = node_collection.one({'_id': ObjectId(each.right_subject)})           
#     #       shelves.append(shelf_name)

#     #       shelf_list[shelf_name.name] = []         
#     #       for ID in shelf_name.collection_set:
#     #         shelf_item = node_collection.one({'_id': ObjectId(ID) })
#     #         shelf_list[shelf_name.name].append(shelf_item.name)
                  
#     #   else:
#     #     shelves = []

#     return render_to_response("ndf/groupdashboard.html", 
#                                 {'groupobj': colg, 'appId': app._id, 'node': colg,
#                                   'user': request.user,
#                                   'groupid': colg._id, 'group_id': colg._id,
#                                   'shelf_list': shelf_list,'shelves': shelves
#                                 },context_instance=RequestContext(request))


#   # for rendering empty form page:
#   available_nodes = node_collection.find({'_type': u'Group'})
#   nodes_list = []
#   for each in available_nodes:
#       nodes_list.append(str((each.name).strip().lower()))
#   return render_to_response("ndf/create_group.html", {'groupid': group_id, 'appId': app._id, 'group_id': group_id, 'nodes_list': nodes_list},RequestContext(request))


@login_required
@get_execution_time
def populate_list_of_members():
	members = User.objects.all()
	memList = []
	for mem in members:
		memList.append(mem.username)	
	return memList


@login_required
@get_execution_time
def populate_list_of_group_members(group_id):
    try :
      try:
        author_list = node_collection.one({"_type":"Group", "_id":ObjectId(group_id)}, {"author_set":1, "_id":0})
      except:
        author_list = node_collection.find_one({"_type":"Group", "name":group_id}, {"author_set":1, "_id":0})
      
      memList = []

      for author in author_list.author_set:
          name_author = User.objects.get(pk=author)
          memList.append(name_author)
      return memList
    except:
        return []


@get_execution_time
def group_dashboard(request, group_id=None):
  # # print "reahcing"
  # if ins_objectid.is_valid(group_id) is False :
  #   group_ins = node_collection.find_one({'_type': "Group","name": group_id})
  #   auth = node_collection.one({'_type': 'Author', 'name': unicode(request.user.username) })
  #   if group_ins:
	 #    group_id = str(group_ins._id)
  #   else :
	 #    auth = node_collection.one({'_type': 'Author', 'name': unicode(request.user.username) })
	 #    if auth :
	 #    	group_id = str(auth._id)	
  # else :
  # 	pass

  try:
    group_obj = "" 
    shelf_list = {}
    shelves = []
    alternate_template = ""
    profile_pic_image = None
    list_of_unit_events = []
    blog_pages = None

    group_obj = get_group_name_id(group_id, get_obj=True)

    if not group_obj:
      group_obj=node_collection.one({'$and':[{'_type':u'Group'},{'name':u'home'}]})
      group_id=group_obj['_id']
    else:
      # group_obj=node_collection.one({'_id':ObjectId(group_id)})
      group_id = group_obj._id

      # getting the profile pic File object
      for each in group_obj.relation_set:
          if "has_profile_pic" in each:
              profile_pic_image = node_collection.one(
                  {'_type': "File", '_id': each["has_profile_pic"][0]}
              )
              break

    auth = node_collection.one({'_type': 'Author', 'name': unicode(request.user.username) }) 

    if auth:

      has_shelf_RT = node_collection.one({'_type': 'RelationType', 'name': u'has_shelf' })

      shelf = triple_collection.find({'_type': 'GRelation', 'subject': ObjectId(auth._id), 'relation_type.$id': has_shelf_RT._id })        
      shelf_list = {}

      if shelf:
        #a temp. variable which stores the lookup for append method
        shelves_append_temp=shelves.append
        for each in shelf:
          shelf_name = node_collection.one({'_id': ObjectId(each.right_subject)})           
          shelves_append_temp(shelf_name)

          shelf_list[shelf_name.name] = []
          #a temp. variable which stores the lookup for append method
          shelf_lst_shelfname_append=shelf_list[shelf_name.name].append
          for ID in shelf_name.collection_set:
            shelf_item = node_collection.one({'_id': ObjectId(ID) })
            shelf_lst_shelfname_append(shelf_item.name)
              
      else:
          shelves = []

  except Exception as e:
    group_obj=node_collection.one({'$and':[{'_type':u'Group'},{'name':u'home'}]})
    group_id=group_obj['_id']
    pass


  # Call to get_neighbourhood() is required for setting-up property_order_list
  group_obj.get_neighbourhood(group_obj.member_of)
  list_of_sg_member_of = get_sg_member_of(group_obj._id)
  # print "\n\n list_of_sg_member_of", list_of_sg_member_of
  if "CourseEventGroup" in group_obj.member_of_names_list:
			forum_gst = node_collection.one({'_type': "GSystemType", 'name': "Forum"})
			twist_gst = node_collection.one({'_type': "GSystemType", 'name': "Twist"})
			page_gst = node_collection.one({'_type': "GSystemType", 'name': "Page"})
			blogpage_gst = node_collection.one({'_type': "GSystemType", 'name': "Blog page"})
			blog_pages = node_collection.find({'member_of':page_gst._id, 'created_by': int(request.user.id),
									'type_of': blogpage_gst._id})
			alternate_template = "ndf/course_event_group.html"
			existing_forums = node_collection.find({
                                          'member_of': forum_gst._id,
                                          'group_set': ObjectId(group_obj._id), 
                                          }).sort('created_at', -1)
			for each in existing_forums:

					temp_forum = {}
					temp_forum['name'] = each.name
					temp_forum['created_at'] = each.created_at
					temp_forum['tags'] = each.tags
					temp_forum['member_of_names_list'] = each.member_of_names_list
					temp_forum['user_details_dict'] = each.user_details_dict
					temp_forum['html_content'] = each.html_content
					temp_forum['contributors'] = each.contributors
					temp_forum['id'] = each._id
					temp_forum['threads'] = node_collection.find({
                                                      '$and':[
                                                      				{'member_of': twist_gst._id},
                                                              {'_type': 'GSystem'},
                                                              {'prior_node': ObjectId(each._id)}
                                                              ], 
                                                      'status': {'$nin': ['HIDDEN']} 
                                                      }).count()
          
					list_of_unit_events.append(temp_forum)

  allow_to_join = True
  if 'end_enroll' in group_obj:
      last_enrollment_date = group_obj.end_enroll
      if last_enrollment_date:
        curr_date_time = datetime.now()
        if curr_date_time > last_enrollment_date:
            allow_to_join = False
  property_order_list = []
  if "group_of" in group_obj:
    if group_obj['group_of']:
      college = node_collection.one({'_type': "GSystemType", 'name': "College"}, {'_id': 1})

      if college:
        if college._id in group_obj['group_of'][0]['member_of']:
          alternate_template = "ndf/college_group_details.html"

      property_order_list = get_property_order_with_value(group_obj['group_of'][0])

  annotations = json.dumps(group_obj.annotations)
  
  default_template = "ndf/groupdashboard.html"
  return render_to_response([alternate_template,default_template] ,{'node': group_obj, 'groupid':group_id, 
                                                       'group_id':group_id, 'user':request.user, 
                                                       'shelf_list': shelf_list,
                                                       'list_of_unit_events': list_of_unit_events,
                                                       'blog_pages':blog_pages,
                                                       'allow_to_join': allow_to_join,
                                                       'appId':app._id, 'app_gst': group_gst,
                                                       'annotations' : annotations, 'shelves': shelves,
                                                       'prof_pic_obj': profile_pic_image
                                                      },context_instance=RequestContext(request)
                          )


# @login_required
# @get_execution_time
# def edit_group(request, group_id):
  
#   # page_node = node_collection.one({"_id": ObjectId(group_id)})
#   # title = gst_group.name
#   # if request.method == "POST":
#   #   is_node_changed=get_node_common_fields(request, page_node, group_id, gst_group)
    
#   #   if page_node.access_policy == "PUBLIC":
#   #     page_node.group_type = "PUBLIC"

#   #   if page_node.access_policy == "PRIVATE":
#   #     page_node.group_type = "PRIVATE"
#     # page_node.save(is_changed=is_node_changed)
#     # page_node.save()
#   #   group_id=page_node._id
#   #   page_node.get_neighbourhood(page_node.member_of)
#   #   return HttpResponseRedirect(reverse('groupchange', kwargs={'group_id':group_id}))

#   # else:
#   #   if page_node.status == u"DRAFT":
#   #     page_node, ver = get_page(request, page_node)
#   #     page_node.get_neighbourhood(page_node.member_of) 

#   # available_nodes = node_collection.find({'_type': u'Group', 'member_of': ObjectId(gst_group._id) })
#   # nodes_list = []
#   # for each in available_nodes:
#   #     nodes_list.append(str((each.name).strip().lower()))

#   # return render_to_response("ndf/edit_group.html",
#   #                                   { 'node': page_node,'title':title,
#   #                                     'appId':app._id,
#   #                                     'groupid':group_id,
#   #                                     'nodes_list': nodes_list,
#   #                                     'group_id':group_id,
#   #                                     'is_auth_node':is_auth_node
#   #                                     },
#   #                                   context_instance=RequestContext(request)
#   #                                   )
    
#     group_obj = get_group_name_id(group_id, get_obj=True)

#     if request.method == "POST":
#         is_node_changed = get_node_common_fields(request, group_obj, group_id, gst_group)
#         # print "=== ", is_node_changed

#         if group_obj.access_policy == "PUBLIC":
#             group_obj.group_type = "PUBLIC"

#         elif group_obj.access_policy == "PRIVATE":
#             group_obj.group_type = "PRIVATE"

#         group_obj.save(is_changed=is_node_changed)

#         group_obj.get_neighbourhood(group_obj.member_of)

#         return HttpResponseRedirect(reverse('groupchange', kwargs={'group_id':group_obj._id}))

#     elif request.method == "GET":
#         if group_obj.status == u"DRAFT":
#             group_obj, ver = get_page(request, group_obj)
#             group_obj.get_neighbourhood(group_obj.member_of) 

#         available_nodes = node_collection.find({'_type': u'Group', '_id': {'$nin': [group_obj._id]}}, {'name': 1, '_id': 0})
#         nodes_list = [str(g_obj.name.strip().lower()) for g_obj in available_nodes]
#         # print nodes_list

#         return render_to_response("ndf/create_group.html",
#                                         {   
#                                         'node': group_obj,
#                                         'title': 'Group',
#                                         # 'appId':app._id,
#                                         'groupid':group_id,
#                                         'group_id':group_id,
#                                         'nodes_list': nodes_list,
#                                         # 'is_auth_node':is_auth_node
#                                       },
#                                     context_instance=RequestContext(request)
#                                     )

        
@login_required
@get_execution_time
def app_selection(request, group_id):
    if ObjectId.is_valid(group_id) is False:
        group_ins = node_collection.find_one({
            '_type': "Group", "name": group_id
        })
        auth = node_collection.one({
            '_type': 'Author', 'name': unicode(request.user.username)
        })
        if group_ins:
            group_id = str(group_ins._id)
        else:
            auth = collection.Node.one({
                '_type': 'Author', 'name': unicode(request.user.username)
            })
            if auth:
                group_id = str(auth._id)
    else:
        pass

    try:
        grp = node_collection.one({
            "_id": ObjectId(group_id)
        }, {
            "name": 1, "attribute_set.apps_list": 1
        })
        if request.method == "POST":
            apps_to_set = request.POST['apps_to_set']
            apps_to_set = json.loads(apps_to_set)

            apps_to_set = [
                ObjectId(app_id) for app_id in apps_to_set if app_id
            ]

            apps_list = []
            apps_list_append = apps_list.append
            for each in apps_to_set:
                apps_list_append(
                    node_collection.find_one({
                        "_id": each
                    })
                )

            at_apps_list = node_collection.one({
                '_type': 'AttributeType', 'name': 'apps_list'
            })
            ga_node = create_gattribute(grp._id, at_apps_list, apps_list)
            return HttpResponse("Apps list updated successfully.")

        else:
            list_apps = []

            for attr in grp.attribute_set:
                if attr and "apps_list" in attr:
                    list_apps = attr["apps_list"]
                    break

            st = get_gapps(already_selected_gapps=list_apps)

            data_list = set_drawer_widget(st, list_apps)
            return HttpResponse(json.dumps(data_list))

    except Exception as e:
        print "Error in app_selection " + str(e)


@get_execution_time
def switch_group(request,group_id,node_id):
  ins_objectid = ObjectId()
  if ins_objectid.is_valid(group_id) is False:
    group_ins = node_collection.find_one({'_type': "Group","name": group_id}) 
    auth = node_collection.one({'_type': 'Author', 'name': unicode(request.user.username) }) 
    if group_ins:
      group_id = str(group_ins._id)
    else:
      auth = node_collection.one({'_type': 'Author', 'name': unicode(request.user.username) })
      if auth:
      	group_id = str(auth._id)
  else :
  	pass

  try:
    node = node_collection.one({"_id": ObjectId(node_id)})
    existing_grps = node.group_set
    if request.method == "POST":
      new_grps_list = request.POST.getlist("new_groups_list[]", "")
      resource_exists = False
      resource_exists_in_grps = []
      response_dict = {'success': False, 'message': ""}
      #a temp. variable which stores the lookup for append method
      resource_exists_in_grps_append_temp=resource_exists_in_grps.append
      new_grps_list_distinct = [ObjectId(item) for item in new_grps_list if ObjectId(item) not in existing_grps]
      if new_grps_list_distinct:
        for each_new_grp in new_grps_list_distinct:
          if each_new_grp:
            grp = node_collection.find({'name': node.name, "group_set": ObjectId(each_new_grp), "member_of":ObjectId(node.member_of[0])})
            if grp.count() > 0:
              resource_exists = True
              resource_exists_in_grps_append_temp(unicode(each_new_grp))

        response_dict["resource_exists_in_grps"] = resource_exists_in_grps

      if not resource_exists:
        new_grps_list_all = [ObjectId(item) for item in new_grps_list]
        node_collection.collection.update({'_id': node._id}, {'$set': {'group_set': new_grps_list_all}}, upsert=False, multi=False)
        node.reload()
        response_dict["success"] = True
        response_dict["message"] = "Published to selected groups"
      else:
        response_dict["success"] = False
        response_dict["message"] = node.member_of_names_list[0] + " with name " + node.name + \
                " already exists. Hence Cannot Publish to selected groups."
        response_dict["message"] = node.member_of_names_list[0] + " with name " + node.name + \
                " already exists in selected group(s). " + \
                "Hence cannot be cross published now." + \
                " For publishing, you can rename this " + node.member_of_names_list[0] + " and try again."
      # print response_dict
      return HttpResponse(json.dumps(response_dict))

    else:
      coll_obj_list = []
      data_list = []
      user_id = request.user.id
      all_user_groups = []
    # for each in get_all_user_groups():
    #   all_user_groups.append(each.name)
    #loop replaced by a list comprehension
      all_user_groups=[each.name for each in get_all_user_groups()]
      st = node_collection.find({'$and': [{'_type': 'Group'}, {'author_set': {'$in':[user_id]}},{'name':{'$nin':all_user_groups}}]})
    # for each in node.group_set:
    #   coll_obj_list.append(node_collection.one({'_id': each}))
    #loop replaced by a list comprehension
      coll_obj_list=[node_collection.one({'_id': each}) for each in node.group_set ]
      data_list = set_drawer_widget(st, coll_obj_list)
      return HttpResponse(json.dumps(data_list))
   
  except Exception as e:
    print "Exception in switch_group"+str(e)
    return HttpResponse("Failure")


@login_required
@get_execution_time
def publish_group(request,group_id,node):

    group_obj = get_group_name_id(group_id, get_obj=True)
    profile_pic_image = None

    if group_obj:
      group_id = group_obj._id

      # getting the profile pic File object
      for each in group_obj.relation_set:

          if "has_profile_pic" in each:
              profile_pic_image = node_collection.one( {'_type': "File", '_id': each["has_profile_pic"][0]} )
              break

    node=node_collection.one({'_id':ObjectId(node)})
     
    page_node,v=get_page(request,node)
    
    node.content = page_node.content
    node.content_org=page_node.content_org
    node.status=unicode("PUBLISHED")
    node.modified_by = int(request.user.id)
    node.save() 
   
    return render_to_response("ndf/groupdashboard.html",
                                   { 'group_id':group_id, 'groupid':group_id,
                                   'node':node, 'appId':app._id,                                   
                                   'prof_pic_obj': profile_pic_image
                                 },
                                  context_instance=RequestContext(request)
                              )


@login_required
@get_execution_time
def create_sub_group(request,group_id):
  try:
      ins_objectid  = ObjectId()
      grpname=""
      if ins_objectid.is_valid(group_id) is False :
          group_ins = node_collection.find_one({'_type': "Group","name": group_id}) 
          auth = node_collection.one({'_type': 'Author', 'name': unicode(request.user.username) })
          if group_ins:
              grpname=group_ins.name 
              group_id = str(group_ins._id)
          else :
              auth = node_collection.one({'_type': 'Author', 'name': unicode(request.user.username) })
              if auth :
                  group_id = str(auth._id)
                  grpname=auth.name	
      else :
          group_ins = node_collection.find_one({'_type': "Group","_id": ObjectId(group_id)})
          if group_ins:
              grpname=group_ins.name
              pass
          else:
              group_ins = node_collection.find_one({'_type': "Author","_id": ObjectId(group_id)})
              if group_ins:
                  grpname=group_ins.name
                  pass

      if request.method == "POST":
          colg = node_collection.collection.Group()
          Mod_colg=node_collection.collection.Group()
          cname=request.POST.get('name', "")
          colg.altnames=cname
          colg.name = unicode(cname)
          colg.member_of.append(gst_group._id)
          usrid = int(request.user.id)
          colg.created_by = usrid
          if usrid not in colg.author_set:
              colg.author_set.append(usrid)
          colg.modified_by = usrid
          if usrid not in colg.contributors:
              colg.contributors.append(usrid)
          colg.group_type = request.POST.get('group_type', "")
          colg.edit_policy = request.POST.get('edit_policy', "")
          colg.subscription_policy = request.POST.get('subscription', "OPEN")
          colg.visibility_policy = request.POST.get('existance', "ANNOUNCED")
          colg.disclosure_policy = request.POST.get('member', "DISCLOSED_TO_MEM")
          colg.encryption_policy = request.POST.get('encryption', "NOT_ENCRYPTED")
          colg.agency_type=request.POST.get('agency_type',"")
          if group_id:
              colg.prior_node.append(group_ins._id)
          colg.save()
          #save subgroup_id in the collection_set of parent group 
          group_ins.collection_set.append(colg._id)
          #group_ins.post_node.append(colg._id)
          group_ins.save()
    
          if colg.edit_policy == "EDITABLE_MODERATED":
              Mod_colg.altnames = cname + "Mod" 
              Mod_colg.name = cname + "Mod"     
              Mod_colg.group_type = "PRIVATE"
              Mod_colg.created_by = usrid
              if usrid not in Mod_colg.author_set:
                  Mod_colg.author_set.append(usrid)
              Mod_colg.modified_by = usrid
              if usrid not in Mod_colg.contributors:
                  Mod_colg.contributors.append(usrid)
              Mod_colg.prior_node.append(colg._id)
              Mod_colg.save() 

              colg.post_node.append(Mod_colg._id)
              colg.save()
          auth = node_collection.one({'_type': 'Author', 'name': unicode(request.user.username) }) 
          has_shelf_RT = node_collection.one({'_type': 'RelationType', 'name': u'has_shelf' })
          shelves = []
          shelf_list = {}
    
          if auth:
              shelf = triple_collection.find({'_type': 'GRelation', 'subject': ObjectId(auth._id), 'relation_type.$id': has_shelf_RT._id })        

              if shelf:
                  for each in shelf:
                      shelf_name = node_collection.one({'_id': ObjectId(each.right_subject)})
                      shelves.append(shelf_name)
                      shelf_list[shelf_name.name] = []
                      for ID in shelf_name.collection_set:
                          shelf_item = node_collection.one({'_id': ObjectId(ID) })
                          shelf_list[shelf_name.name].append(shelf_item.name)
                  
              else:
                  shelves = []

          return render_to_response("ndf/groupdashboard.html",{'groupobj':colg,'appId':app._id,'node':colg,'user':request.user,
                                                         'groupid':colg._id,'group_id':colg._id,
                                                         'shelf_list': shelf_list,'shelves': shelves
                                                        },context_instance=RequestContext(request))
      available_nodes = node_collection.find({'_type': u'Group', 'member_of': ObjectId(gst_group._id) })
      nodes_list = []
      for each in available_nodes:
          nodes_list.append(str((each.name).strip().lower()))

      return render_to_response("ndf/create_sub_group.html", {'groupid':group_id,'maingroup':grpname,'group_id':group_id,'nodes_list': nodes_list},RequestContext(request))
  except Exception as e:
      print "Exception in create subgroup "+str(e)
