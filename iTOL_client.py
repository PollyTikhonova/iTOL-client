import re
import pandas as pd
import requests

class ITOL_session(object):
    def __init__(self, login, password):
        self.login = login
        self.pwd = password
        self.session = self.do_login()
        self.get_data()
    
    def do_login(self):
        LOGIN_URL = 'https://itol.embl.de/login.cgi'
        session = requests.Session()
        session.post(LOGIN_URL, data={'login':self.login, 'pwd':self.pwd})
        return session
        
    def delete(self, what, id_):
        if what == 'workspace':
            DELETE_URL = 'https://itol.embl.de/ajax/personal/workspace_remove.cgi'
            respond = self.session.post(DELETE_URL, data={'i':'hd-ws-%s'%id_})
        elif what == 'project':
            DELETE_URL = 'https://itol.embl.de/ajax/personal/project_remove.cgi'
            respond = self.session.post(DELETE_URL, data={'i':'project-%s'%id_})
        elif what == 'tree':
            DELETE_URL = 'https://itol.embl.de/ajax/personal/tree_remove.cgi'
            respond = self.session.post(DELETE_URL, data={'i':id_})
        if 'Please login.' in respond.text.rstrip():
            self.session = self.do_login()
            return self.delete( what, id_)
        self.data = self.get_data()
        return respond.text.rstrip()
        
    def get_data(self):
        respond = self.session.post("https://itol.embl.de/personal_page.cgi")
        msg = respond.text.rstrip()
        if 'Please login.' in msg:
            self.session = self.do_login()
            return self.get_data()
        between_script_tags = re.search('<script>(.*)</script>', msg)
        script_str = between_script_tags.string[between_script_tags.start():between_script_tags.end()]
        script_str = script_str.split("var ws = ")[1].replace(';$(document).ready(function() {initializeWorkspace(); });</script>', '')
        personal_page_list = eval(script_str)
        workspaces = pd.DataFrame(columns=['Name', 'ID', 'Description'])
        workspace_objects = pd.DataFrame(columns=['Name', 'ID','Object'])
        for workspace in personal_page_list:
            workspace_name = workspace['t']
            workspace_id = workspace['id']
            workspace_desc = workspace['d']
            workspace_projects = pd.DataFrame(columns=['Name', 'ID', 'SID', 'Description'])
            workspace_projects_objects = pd.DataFrame(columns=['Name', 'ID','Object'])
            for project in workspace['p']:
                project_name = project['t']
                project_id = project['id']
                project_sid = project['sid']
                project_desc = project['d']
                project_trees = pd.DataFrame(columns=['Name', 'ID', 'Description', 'Datasets',
                                                      'Inserted', 'Modified', 'Accessed'])
                project_trees_objects = pd.DataFrame(columns=['Name', 'ID', 'Object'])
                for tree in project['data']:
                    tree_name = tree['t']
                    tree_id = tree['id']
                    tree_desc = tree['d']
                    tree_inserted = tree['i']
                    tree_modified = tree['u']
                    tree_accessed = tree['a']
                    tree_datasets = tree.get('ds')
                    if tree_datasets is not None:
                        tree_datasets = ', '.join(['%s [%s]'%(dataset['l'], dataset['t'])
                                                  for dataset in tree_datasets])
                    project_trees.loc[len(project_trees)] = [tree_name, tree_id, tree_desc, tree_datasets,
                                                            tree_inserted, tree_modified, tree_accessed]
                    project_trees_objects.loc[len(project_trees_objects)] = [tree_name, tree_id,
                                                                             ITOL_tree(tree_name, tree_id, tree_desc, 
                                                                                       tree_datasets,
                                                                                      tree_inserted, tree_modified, 
                                                                                       tree_accessed)]
                workspace_projects_objects.loc[len(workspace_projects_objects)] = [project_name, project_id,
                                                                                   ITOL_project(project_name, project_id, 
                                                                                               project_sid, project_desc,
                                                                                               project_trees,
                                                                                               project_trees_objects)]
                workspace_projects.loc[len(workspace_projects)] = [project_name, project_id, project_sid, project_desc]
            workspace_objects.loc[len(workspace_objects)] = [workspace_name, workspace_id,
                                                             ITOL_workspace(workspace_name, workspace_id, workspace_desc,
                                                                                     workspace_projects,
                                                                                     workspace_projects_objects)]
            workspaces.loc[len(workspaces)] = [workspace_name, workspace_id, workspace_desc]
        self.data = ITOL_page(workspaces, workspace_objects)

class ITOL_data(object):    
    def __init__(self, table):
        self.table_id = table.copy()
        self.table_name = table.copy()
        self.table_id.index = self.table_id['ID'].values
        self.table_name.index = self.table_name['Name'].values
    
    def __getitem__(self, key):
        chosen = None
        if key in self.table_id.index:
            chosen = self.table_id.loc[key, 'Object']
        elif key in self.table_name.index:
            chosen = self.table_name.loc[key, 'Object']
        if chosen is None:
            return None
        elif 'ITOL' in str(type(chosen)): 
            return chosen
        else:
            return chosen.to_list()
            

class ITOL_page(ITOL_data):
    def __init__(self, table, workspace_objects):
        self.table = table
        super(ITOL_page, self).__init__(workspace_objects)
    
class ITOL_workspace(ITOL_data):
    def __init__(self, name, id_, desc, table, projects_objects):
        self.name = name
        self.id = id_
        self.desc = desc
        self.table = table
        super(ITOL_workspace, self).__init__(projects_objects)
        
class ITOL_project(ITOL_data):
    def __init__(self, name, id_, sid, desc, table, trees_objects):
        self.name = name
        self.id = id_
        self.sid = sid
        self.desc = desc
        self.table = table
        super(ITOL_project, self).__init__(trees_objects)
        
        
class ITOL_tree(ITOL_data):
    def __init__(self, name, id_, desc, datasets, inserted, modified, accessed):
        self.name = name
        self.id = id_
        self.desc = desc
        self.datasets = datasets
        self.inserted = inserted 
        self.modified = modified 
        self.accessed = accessed