#!/usr/bin/python                                                                                                                                                                                            
import sys
import os
import optparse
from gtclib import golive
DEPLOYMENT_NAME='deploy'

if __name__ =='__main__':
    usage = "usage: python %prog [options] dbname\n"
    parser = optparse.OptionParser(version='0.1', usage=usage)

    deploy_group=golive.get_deploy_options_group(parser)
    parser.add_option_group(deploy_group)

    opt, args = parser.parse_args(sys.argv)
    user_id,host_id = golive.get_env(opt)

    dbname=args[1]
    server_path, config_file = golive.get_server_and_conf(opt, DEPLOYMENT_NAME)
    #server_path, config_file = '/home/jan/github.com/odoo7', '/home/jan/projects/server_pjbrefactoring.conf'                                                                                               
    sys.path.append(server_path)


    import openerp
    import openerp.tools.config
    openerp.tools.config.parse_config(['--config=%s' % config_file])
    import openerp.addons.galtyslib.openerplib as openerplib

    r=openerp.registry(dbname)
    openerp.api.Environment.reset()
    cr=r.cursor()
    uid=1
    env= openerp.api.Environment(cr, uid, {})
    pool=r

    file_ids=pool.get("deploy.file").search(cr, uid, [])
    delete_ids=[]
    for f in pool.get("deploy.file").browse(cr, uid, file_ids):
        i = pool.get(f.template_id.model).search(cr, uid, [('id','=',f.res_id)] )
        if len(i)==0:
            delete_ids.append( f.id)
    print delete_ids
    print pool.get("deploy.file").unlink(cr, uid, delete_ids)
    cr.commit()
    cr.close()
