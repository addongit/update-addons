#!/usr/bin/python

import ConfigParser
import sys
import os
import shutil
from optparse import OptionParser

addons_info = {}

def initConfig(config):
  ''' Initialize the config object pointed to $config's path.'''
  c = ConfigParser.ConfigParser()
  c.optionxform = str
  c.cwd = sys.path[0]
  c.cfg_path = os.path.join(c.cwd, config)
  return c

def git_remove(addon):
  '''Remove $addon from the repository.'''
  os.system('git rm -r %s' % addon)
  return True
  
def git_add():
  ''' Run git add to record changes.'''
  os.system('git add .')
  return True
  
def git_commit(msg):
  ''' Commit changes recording $msg.'''
  os.system("git commit -a -s -m '%s'" % msg)
  return True
  
def git_push():
  ''' Push changes to the branches origin.'''
  os.system('git push')
  return True
  
def git_checkout(branch):
  ''' Checkout $branch.'''
  os.system('git checkout %s' % branch)
  return True
  
def sync_mirror(repo):
  ''' Syncs $repo against origin repo.
      In my case, $repo is a local mirror.'''
  cur_dir = os.getcwd()
  os.chdir(repo)
  os.system('git remote -v update')
  os.chdir(cur_dir)
  return True
  
def git_find_all_branches():
  ''' Find all branches
      Strip current branch identifier (*)
      Strip leading/trailing whitespace.'''
  cur_dir = os.getcwd()
  cmd = 'git branch -l'
  branches = []
  try:
    for branch in os.popen(cmd).readlines():
      branches.append(branch.replace('*','').strip())
  except:
    branches = []
  return branches

def get_addon_manifest(branch_list, do_common=False, do_diff=False):
  ''' Generates an addon manifest 
      across all branches. '''
 
  global addons_info
  addon_sets = {}
  branch_addons = {} 
  branch_count = len(branch_list)
  
  # if empty branch list, index everything
  branches = branch_list if branch_count > 0 else git_find_all_branches()

  for branch in branches:
    # Switch to the current branch
    git_checkout(branch)

    # Generate a list of addons
    branch_addons[branch] = sorted( os.listdir( addons_info['addons_directory'] ) )
    
    # TODO: move this functionality out of here
    # since we're storing addons by branch in a dict.
    # create a set with the addon_list and store
    addon_sets[branch] = set(branch_addons[branch])

  # Print Complete index of addons across all branches.
  if branch_count == 0:
    print format_section('Complete Addons list')
    for branch in branch_addons.keys():
      print '\n\t%s:\n' % branch
      for addon in branch_addons[branch]:
        print '\t\t%s' % addon
      print '\n'
    # Since we can only perform set logic when two
    # branches are present, we're done.
    return
  
  if branch_count != 2:
    print 'Exactly two branches are required for diff/common operations.'
    return

  if do_common:
    print format_section( 'Common Addons between branches: [%s] and [%s]' % ( branch_list[0], branch_list[1] ) )
    
    for common_addon in addon_sets[ branch_list[0] ].intersection( addon_sets[ branch_list[1] ] ):
      print '\t%s' % common_addon
    print '\n'

  if do_diff:
    print format_section('Unique Addons between branches: [%s] and [%s]' % ('jeni', 'rob'))
    
    print '\n\t%s:\n' % branch_list[0]
    for unique_addon in addon_sets[ branch_list[0] ].difference( addon_sets[ branch_list[1] ] ):
      print '\t\t%s' % unique_addon
    print '\n'
  
    print '\n\t%s:\n' % branch_list[1]
    for unique_addon in addon_sets[ branch_list[1] ].difference( addon_sets[ branch_list[0] ] ):
      print '\t\t%s' % unique_addon
    print '\n'


def format_section(header):
  DIV = '\n%s\n' % ( '=' * (len(header) * 2) )
  format_header = '\n\t%s\n' % (header) 
  return '%s%s%s' % (DIV, format_header, DIV) 


def main(opts, args):
  
  # Make sure config exists
  
  assert os.path.exists(opts.config)
  config = initConfig(opts.config)
  
  config.read(config.cfg_path)
  
  global addons_info

  addons_info = { 'branch':            opts.branch if len(opts.branch) > 0 else ['master'],
                  'addons_to_delete':  opts.delete,
                  'updates_directory': opts.updates_directory if opts.updates_directory is not None else config.get('local', 'AddonsUpdatesDirectory'),
                  'addons_directory':  opts.addons_directory if opts.addons_directory is not None else config.get('local', 'AddonsDirectory'),
                  'mirror':            config.get('local', 'RepoMirror'),
                  'exclusions':        [] if not config.get('local', 'exclusions') else config.get('local', 'exclusions').split(',')  
                }
  
  # Make sure required directories exist
  assert os.path.exists(addons_info['updates_directory'])
  assert os.path.exists(addons_info['addons_directory'])
  
  os.chdir(addons_info['addons_directory'])
  if opts.verbose: print 'Using %s' % os.getcwd()
  
  if opts.verbose: print 'Branches: (%s)' % ' | '.join(addons_info['branch'])
  
  # Determine if we have updated addons to process.
  #addon_updates = os.listdir(addons_info['updates_directory'])
  HAS_UPDATES = opts.update #True if len(addon_updates) > 0 else False
  
  # Determine if we need to delete specific addons.
  addons_delete = addons_info['addons_to_delete']
  HAS_DELETIONS = True if len(addons_info['addons_to_delete']) > 0 else False
  
  # Use what was passed in for branch name
  # If 'all', determine which branches are present and use them instead.
  addons_branches = addons_info['branch'] if addons_info['branch'] != ['all'] else git_find_all_branches()
  
  if opts.list_addons or opts.list_common or opts.list_diff:
    get_addon_manifest(opts.branch, do_common=opts.list_common, do_diff=opts.list_diff)
    sys.exit()

  # Process each branch.  
  for branch in addons_branches:
    git_checkout(branch)
    
    # branch specific addon updates directory.
    addon_depot_branch = os.path.join( addons_info['updates_directory'], branch )
    
    # Verify that directory exists
    assert os.path.exists(addon_depot_branch)
    
    print '(%s)\tUsing %s as base.' % (branch, addon_depot_branch)
   
    addon_updates = os.listdir(addon_depot_branch)

    # if the addons present in the updates folder
    # matches the entries in the exclusions we define exactly,
    # we can safely ignore the directory contents and declare an empty list
    if not set(addon_updates).difference( set( addons_info['exclusions'] ) ): addon_updates = []

    # Check for specific addons to delete and process them.
    if HAS_DELETIONS:
      for addon in addons_delete:
        if os.path.exists(os.path.join(addons_info['addons_directory'], addon)):
          if 'y' in raw_input('(%s)\tDelete << %s >> ?\n(Y or N): ' % (branch, addon)).lower():
            git_remove(addon)
            git_commit('Removed %s.' % addon)
        else:
          print '(%s)\t%s NOT found, skipping.' % (branch, addon)

    # If we have updated addons, process them.
    if HAS_UPDATES:
      if opts.verbose: print '(%s)\tUsing the following addons:\n%s' % (branch, '\n'.join(addon_depot_branch))
      
      # TODO: Add actual transaction logic supporting rollback functionality.
      
      # *** Done in the following manner to provide as close to a transactional process as possible.
      # For each addon in the updates folder, do the following:
      # Remove addon before updating.
      # Commit.
      # Copy the update into place.
      # Add files
      # Commit

      for addon in addon_updates:
        if addon in addons_info['exclusions']: continue

        print '(%s)\tProcessing %s' % (branch, addon)
        
        if os.path.exists(os.path.join(addons_info['addons_directory'], addon)):
          if opts.verbose: print '(%s)\tRemoving %s for update' % (branch, addon)
          git_remove(addon)
          git_commit('removed %s for update' % addon)
        
        updated_addon_src_path = os.path.join( addon_depot_branch, addon )
        updated_addon_dst_path = os.path.join(addons_info['addons_directory'], addon)
        
        if opts.verbose: print '(%s)\tCopying %s to %s' % (branch, updated_addon_src_path, updated_addon_dst_path)
        shutil.copytree(updated_addon_src_path, updated_addon_dst_path)
        
        git_add()
        git_commit('Updated %s' % addon)
        
    # Should we push commits to origin
    if opts.push: 
      if opts.verbose: print '(%s)\tPushing' % branch
      git_push()
  
  # Should we sync the mirror when finished.
  if opts.sync:
    print 'Syncing mirror'
    if opts.verbose: print 'Using mirror: %s' % addons_info['mirror']
    assert os.path.exists(addons_info['mirror'])
    sync_mirror(addons_info['mirror'])
    
  # Clean up if required.
  if opts.clean_up and HAS_UPDATES:
    print 'Removing (%d) addon folder(s) from %s\n' % (len(addon_updates), addon_depot_branch)
    for addon in addon_updates:
      if addon in addons_info['exclusions']: continue

      updated_addon_src_path = os.path.join(addon_depot_branch, addon)
      
      if opts.verbose: print 'Deleting %s' % updated_addon_src_path
      
      shutil.rmtree(updated_addon_src_path)
  
if __name__ == '__main__':

  def getOpts():
    '''
    Setup our cmdline variables.
    '''
    _parser = OptionParser(usage = "usage: %prog [options]")
    
    _parser.add_option( '--branch',
                        '-b',
                        action='append', 
                        type='string',
                        default=[], 
                        dest='branch', 
                        help="Branch. Defaults to 'master' if no branch supplied. Use 'all' for global updates *WARNING* BE CAREFUL.")
    
    _parser.add_option('--delete',
                        '-d',
                        action='append', 
                        default=[],
                        type='string',
                        dest='delete', 
                        help='Delete addon.')
                          
    _parser.add_option('--verbose',
                        '-v',
                        action='store_true', 
                        default=False, 
                        dest='verbose', 
                        help='Verbose.')
    
    _parser.add_option('--update',
                        '-u',
                        action='store_true', 
                        default=False, 
                        dest='update', 
                        help='Process addon updates.')
                                            
    _parser.add_option('--push',
                        '-p',
                        action='store_true', 
                        default=False, 
                        dest='push', 
                        help='Push branch to origin.')
                          
    _parser.add_option('--addons-updates-folder',
                       action='store', 
                       type='string',
                       default=None,
                       dest='updates_directory',
                       help='Path to the updated addons folder.')
                      
    _parser.add_option('--addons--folder',
                       action='store', 
                       type='string',
                       default=None,
                       dest='addons_directory',
                       help='Path to the addons repo.')
    
    _parser.add_option('--config',
                       action='store', 
                       type='string',
                       default='./update-addons.cfg',
                       dest='config',
                       help='Config file.')
                       
    _parser.add_option('--sync-repo',
                        '-s',
                        action='store_true', 
                        default=False, 
                        dest='sync', 
                        help='Sync configured mirror repo.')
                        
    _parser.add_option('--list-addons',
                        '-l',
                        action='store_true', 
                        default=False, 
                        dest='list_addons', 
                        help='List addons for the branch or branches specified. (**NOTE: If no branch is specified, \
                              a complete index across all branches will be generated.')
                        
    _parser.add_option('--diff-addons',
                        action='store_true', 
                        default=False, 
                        dest='list_diff', 
                        help='Diff addons between branches. (**NOTE: Must be used with two --branch args)')
                        
    _parser.add_option('--common-addons',
                        action='store_true', 
                        default=False, 
                        dest='list_common', 
                        help='List Common addons between branches. (**NOTE: Must be used with two --branch args)')
                        
    _parser.add_option('--clean-up',
                        '-c',
                        action='store_true', 
                        default=False, 
                        dest='clean_up', 
                        help='Clean up newly added addons in the transitory directory.')

    (_opts, _args) = _parser.parse_args()
    return _opts, _args

  opts, args = getOpts()

  try:
    main(opts, args)
  except KeyboardInterrupt, e:
    print >> sys.stderr, '\n\nExiting.'
  except Exception, e:
    print str('ERROR: %s' % e)
  sys.exit('Finished.\n')

  
